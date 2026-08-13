"""GraphQL clients for the two downstream services (Users and Products).

Where the REST edition used JSON REST calls and the gRPC edition used typed
stubs, here each dependency call is a **GraphQL document POSTed over HTTP**. Each
client owns an ``httpx.AsyncClient`` (base_url set to the service) and:

* attaches a per-request timeout,
* retries only transport-level failures with exponential backoff,
* forwards the ``x-request-id`` header for tracing,
* inspects the GraphQL ``errors`` array to map failures onto domain exceptions.

The ``httpx.AsyncClient`` is injected so tests can point it at in-process fake
GraphQL apps via an ASGI transport.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from .circuit_breaker import CircuitBreaker
from .config import get_settings
from .observability import outbound_headers

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
    """A downstream service was unreachable or returned a transport error."""


class ProductUnavailable(Exception):
    """A product is missing or does not have enough stock."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


async def _post_graphql(client: httpx.AsyncClient, query: str, variables: dict, breaker: CircuitBreaker) -> dict:
    """POST a GraphQL document, retrying transport errors, returning the JSON body.

    Guarded by a circuit breaker: if the breaker is OPEN we fail fast without a
    network call. A clean HTTP 200 (even one whose body carries GraphQL
    ``errors`` — a *business* failure) means the dependency is healthy and records
    a success; only transport/HTTP-status failures that exhaust the retry budget
    record a breaker failure.
    """
    if not breaker.allow():
        raise DownstreamError(f"circuit open for {breaker.name}")

    settings = get_settings()
    last_exc: Exception | None = None
    for attempt in range(1, settings.http_max_retries + 1):
        try:
            resp = await client.post(
                "/graphql",
                json={"query": query, "variables": variables},
                headers=outbound_headers(),
                timeout=settings.http_timeout_seconds,
            )
            resp.raise_for_status()
            breaker.record_success()
            return resp.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < settings.http_max_retries:
                delay = 0.1 * (2 ** (attempt - 1))
                log.warning("retry %d for downstream in %.2fs (%s)", attempt, delay, exc)
                await asyncio.sleep(delay)
    breaker.record_failure()
    raise DownstreamError(str(last_exc))


def _first_error_message(body: dict) -> str | None:
    errors = body.get("errors")
    if errors:
        return errors[0].get("message", "downstream error")
    return None


class UsersGraphQLClient:
    """Validates the buyer via the Users service's GraphQL API."""

    _QUERY = "query ($id: ID!) { user(id: $id) { id } }"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def user_exists(self, user_id: str) -> bool:
        body = await _post_graphql(self._client, self._QUERY, {"id": user_id}, _breaker("users"))
        if _first_error_message(body):
            # The Users service reports an unknown id as a "user not found" error.
            return False
        return body.get("data", {}).get("user") is not None


class ProductsGraphQLClient:
    """Prices and reserves stock via the Products service's GraphQL API."""

    _GET = "query ($id: ID!) { product(id: $id) { id name priceCents stock } }"
    _RESERVE = "mutation ($id: ID!, $qty: Int!) { reserveStock(id: $id, quantity: $qty) { id stock } }"
    _RELEASE = "mutation ($id: ID!, $qty: Int!) { releaseStock(id: $id, quantity: $qty) { id stock } }"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_product(self, product_id: str) -> dict:
        body = await _post_graphql(self._client, self._GET, {"id": product_id}, _breaker("products"))
        if _first_error_message(body):
            raise ProductUnavailable(f"product {product_id} not found")
        return body["data"]["product"]

    async def reserve(self, product_id: str, quantity: int) -> dict:
        body = await _post_graphql(
            self._client, self._RESERVE, {"id": product_id, "qty": quantity}, _breaker("products")
        )
        msg = _first_error_message(body)
        if msg:
            raise ProductUnavailable(msg)
        return body["data"]["reserveStock"]

    async def release(self, product_id: str, quantity: int) -> None:
        """Compensating action for :meth:`reserve` — return ``quantity`` units to
        stock after a checkout fails partway through.

        Releasing only ever *increases* stock, so it is safe to retry and safe to
        call even if the product has since been deleted. Business-level GraphQL
        errors (e.g. "product not found") are tolerated — there is simply nothing
        to release; only transport failures propagate (and the saga logs them).
        """
        await _post_graphql(
            self._client, self._RELEASE, {"id": product_id, "qty": quantity}, _breaker("products")
        )
