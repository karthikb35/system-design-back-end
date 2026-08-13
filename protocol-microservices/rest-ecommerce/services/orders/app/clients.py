"""HTTP clients for the two downstream services (Users and Products).

This is where the Orders service crosses the network. Two production concerns
are handled here so the service layer stays clean:

1. **Timeouts** — never wait forever for a slow dependency.
2. **Retries with backoff** — transient failures (a brief network blip, a pod
   restarting) are retried a few times before giving up.

The correlation id (X-Request-ID) is forwarded so a single request can be traced
across every service it touches.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from .circuit_breaker import CircuitBreaker
from .config import get_settings
from .observability import REQUEST_ID_HEADER, request_id_ctx

log = logging.getLogger("orders.clients")

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


class UserNotFound(Exception):
    """The buyer's user id does not exist in the Users service."""


class ProductUnavailable(Exception):
    """A product is missing or does not have enough stock."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _headers() -> dict[str, str]:
    # Propagate the correlation id to downstream services for tracing.
    return {REQUEST_ID_HEADER: request_id_ctx.get()}


async def _request_with_retry(method: str, url: str, breaker: CircuitBreaker, **kwargs) -> httpx.Response:
    """Send an HTTP request, retrying on network errors / 5xx with backoff.

    Guarded by a circuit breaker: if the breaker is OPEN we fail fast without
    touching the network. A 4xx (caller's fault) or 2xx/3xx counts as a healthy
    dependency and closes/keeps-closed the breaker; only a fully-exhausted call
    (network errors or 5xx on every attempt) records a breaker failure.
    """
    if not breaker.allow():
        raise DownstreamError(f"circuit open for {breaker.name}")

    settings = get_settings()
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    last_exc: Exception | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, settings.http_max_retries + 1):
            try:
                resp = await client.request(method, url, headers=_headers(), **kwargs)
            except httpx.HTTPError as exc:  # connect/read/timeout errors
                last_exc = exc
            else:
                # Retry only on server errors; 4xx are the caller's fault.
                if resp.status_code < 500:
                    breaker.record_success()
                    return resp
                last_exc = DownstreamError(f"{url} -> {resp.status_code}")

            if attempt < settings.http_max_retries:
                # Exponential backoff: 0.1s, 0.2s, 0.4s, ...
                delay = 0.1 * (2 ** (attempt - 1))
                log.warning("retry %d/%d for %s in %.2fs", attempt, settings.http_max_retries, url, delay)
                await asyncio.sleep(delay)

    breaker.record_failure()
    raise DownstreamError(str(last_exc))


class UsersClient:
    """Talks to the Users service to validate the buyer."""

    async def user_exists(self, user_id: str) -> bool:
        settings = get_settings()
        url = f"{settings.users_service_url}/users/{user_id}"
        resp = await _request_with_retry("GET", url, _breaker("users"))
        if resp.status_code == 404:
            return False
        if resp.status_code == 200:
            return True
        raise DownstreamError(f"users service returned {resp.status_code}")


class ProductsClient:
    """Talks to the Products service to price and reserve stock."""

    async def get_product(self, product_id: str) -> dict:
        settings = get_settings()
        url = f"{settings.products_service_url}/products/{product_id}"
        resp = await _request_with_retry("GET", url, _breaker("products"))
        if resp.status_code == 404:
            raise ProductUnavailable(f"product {product_id} not found")
        if resp.status_code != 200:
            raise DownstreamError(f"products service returned {resp.status_code}")
        return resp.json()

    async def reserve(self, product_id: str, quantity: int) -> dict:
        settings = get_settings()
        url = f"{settings.products_service_url}/products/{product_id}/reserve"
        resp = await _request_with_retry("POST", url, _breaker("products"), json={"quantity": quantity})
        if resp.status_code == 409:
            raise ProductUnavailable(f"insufficient stock for {product_id}")
        if resp.status_code == 404:
            raise ProductUnavailable(f"product {product_id} not found")
        if resp.status_code != 200:
            raise DownstreamError(f"products service returned {resp.status_code}")
        return resp.json()

    async def release(self, product_id: str, quantity: int) -> None:
        """Compensating action for :meth:`reserve` — return ``quantity`` units to
        stock after a checkout fails partway through.

        Releasing only ever *increases* stock, so it is safe to retry and safe to
        call even if the product has since been deleted (404 is tolerated). This
        is what makes release a valid compensation for reserve in the saga.
        """
        settings = get_settings()
        url = f"{settings.products_service_url}/products/{product_id}/release"
        resp = await _request_with_retry("POST", url, _breaker("products"), json={"quantity": quantity})
        if resp.status_code not in (200, 404):
            raise DownstreamError(f"products service returned {resp.status_code}")
