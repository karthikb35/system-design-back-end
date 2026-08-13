"""gRPC clients for the two downstream services (Users and Products).

This is the gRPC analogue of the REST edition's httpx clients. Two production
concerns are handled here:

1. **Deadlines** — every call carries a timeout so a slow dependency can't hang
   the order.
2. **Retries with backoff** — only *transient* gRPC codes (``UNAVAILABLE``,
   ``DEADLINE_EXCEEDED``) are retried; business errors like ``NOT_FOUND`` are not.

The correlation id is forwarded as ``x-request-id`` metadata so one id traces the
request across every service.
"""
from __future__ import annotations

import asyncio
import logging

import grpc

from .circuit_breaker import CircuitBreaker
from .config import get_settings
from .observability import REQUEST_ID_KEY, request_id_ctx
from .pb import (
    products_pb2,
    products_pb2_grpc,
    users_pb2,
    users_pb2_grpc,
)

log = logging.getLogger("orders.clients")

_RETRYABLE = {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}

# One breaker per downstream dependency, shared across all requests in this
# worker (created lazily so settings are read once at first use).
_BREAKERS: dict[str, CircuitBreaker] = {}


def _breaker(name: str) -> CircuitBreaker:
    cb = _BREAKERS.get(name)
    if cb is None:
        s = get_settings()
        cb = CircuitBreaker(
            name,
            failure_threshold=s.cb_failure_threshold,
            recovery_time=s.cb_recovery_seconds,
        )
        _BREAKERS[name] = cb
    return cb


class DownstreamError(Exception):
    """A downstream service was unreachable or returned a server error."""


class ProductUnavailable(Exception):
    """A product is missing or does not have enough stock."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _md() -> list[tuple[str, str]]:
    return [(REQUEST_ID_KEY, request_id_ctx.get())]


async def _call_with_retry(make_call, breaker: CircuitBreaker):
    """Invoke ``make_call()`` (returns an awaitable), retrying transient codes.

    Guarded by a circuit breaker: if the breaker is OPEN we fail fast. A
    non-retryable status (NOT_FOUND, FAILED_PRECONDITION, ...) means the
    dependency *answered* — it is healthy, so we record a success and re-raise the
    business error. Only exhausting the retry budget on transient codes records a
    breaker failure.
    """
    if not breaker.allow():
        raise DownstreamError(f"circuit open for {breaker.name}")

    settings = get_settings()
    last: grpc.aio.AioRpcError | None = None
    for attempt in range(1, settings.grpc_max_retries + 1):
        try:
            result = await make_call()
        except grpc.aio.AioRpcError as exc:
            if exc.code() not in _RETRYABLE:
                breaker.record_success()  # dependency answered (business error)
                raise  # business error — do not retry
            last = exc
            if attempt < settings.grpc_max_retries:
                delay = 0.1 * (2 ** (attempt - 1))
                log.warning("retry %d for downstream in %.2fs (%s)", attempt, delay, exc.code())
                await asyncio.sleep(delay)
        else:
            breaker.record_success()
            return result
    breaker.record_failure()
    raise DownstreamError(str(last))


class UsersGrpcClient:
    """Validates the buyer via the Users service."""

    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = users_pb2_grpc.UserServiceStub(channel)

    async def user_exists(self, user_id: str) -> bool:
        timeout = get_settings().grpc_timeout_seconds
        try:
            await _call_with_retry(
                lambda: self._stub.GetUser(
                    users_pb2.GetUserRequest(id=user_id), metadata=_md(), timeout=timeout
                ),
                _breaker("users"),
            )
            return True
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.NOT_FOUND:
                return False
            raise DownstreamError(str(exc))


class ProductsGrpcClient:
    """Prices and reserves stock via the Products service."""

    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = products_pb2_grpc.ProductServiceStub(channel)

    async def get_product(self, product_id: str) -> dict:
        timeout = get_settings().grpc_timeout_seconds
        try:
            reply = await _call_with_retry(
                lambda: self._stub.GetProduct(
                    products_pb2.GetProductRequest(id=product_id), metadata=_md(), timeout=timeout
                ),
                _breaker("products"),
            )
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.NOT_FOUND:
                raise ProductUnavailable(f"product {product_id} not found")
            raise DownstreamError(str(exc))
        return {"id": reply.id, "name": reply.name, "price_cents": reply.price_cents, "stock": reply.stock}

    async def reserve(self, product_id: str, quantity: int) -> dict:
        timeout = get_settings().grpc_timeout_seconds
        try:
            reply = await _call_with_retry(
                lambda: self._stub.ReserveStock(
                    products_pb2.ReserveStockRequest(id=product_id, quantity=quantity),
                    metadata=_md(),
                    timeout=timeout,
                ),
                _breaker("products"),
            )
        except grpc.aio.AioRpcError as exc:
            code = exc.code()
            if code == grpc.StatusCode.FAILED_PRECONDITION:
                raise ProductUnavailable(f"insufficient stock for {product_id}")
            if code == grpc.StatusCode.NOT_FOUND:
                raise ProductUnavailable(f"product {product_id} not found")
            raise DownstreamError(str(exc))
        return {"id": reply.id, "name": reply.name, "price_cents": reply.price_cents, "stock": reply.stock}

    async def release(self, product_id: str, quantity: int) -> None:
        """Compensating action for :meth:`reserve` — return ``quantity`` units to
        stock after a checkout fails partway through.

        Releasing only ever *increases* stock, so it is safe to retry and safe to
        call even if the product has since been deleted (NOT_FOUND is tolerated).
        This is what makes release a valid compensation for reserve in the saga.
        """
        timeout = get_settings().grpc_timeout_seconds
        try:
            await _call_with_retry(
                lambda: self._stub.ReleaseStock(
                    products_pb2.ReleaseStockRequest(id=product_id, quantity=quantity),
                    metadata=_md(),
                    timeout=timeout,
                ),
                _breaker("products"),
            )
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.NOT_FOUND:
                return  # nothing to release — tolerate
            raise DownstreamError(str(exc))
