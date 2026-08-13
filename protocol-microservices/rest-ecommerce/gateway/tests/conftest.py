"""Gateway test fixtures.

The gateway has no database; it only makes outbound HTTP calls. We intercept
those by monkeypatching `httpx.AsyncClient` to use an `httpx.MockTransport` that
serves an in-memory fleet of the three downstream services, routed by port
(users=8001, products=8002, orders=8003).
"""
from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

# In-memory downstream data.
USERS = {"user-1": {"id": "user-1", "full_name": "Ada Lovelace"}}
PRODUCTS = {
    "prod-1": {"id": "prod-1", "name": "Widget", "price_cents": 1000, "stock": 5},
}
ORDERS = {
    "order-1": {
        "id": "order-1",
        "user_id": "user-1",
        "status": "confirmed",
        "total_cents": 2000,
        "items": [{"product_id": "prod-1", "quantity": 2, "unit_price_cents": 1000}],
    }
}


def _json(payload, status_code=200) -> httpx.Response:
    return httpx.Response(status_code, content=json.dumps(payload).encode(), headers={"content-type": "application/json"})


def _handler(request: httpx.Request) -> httpx.Response:
    port = request.url.port
    path = request.url.path

    if path == "/health/ready":
        return _json({"status": "ready"})

    if port == 8001:  # users
        if path.startswith("/users/"):
            uid = path.split("/users/")[1]
            return _json(USERS[uid]) if uid in USERS else _json({"detail": "not found"}, 404)
    if port == 8002:  # products
        if path.startswith("/products/"):
            pid = path.split("/products/")[1]
            return _json(PRODUCTS[pid]) if pid in PRODUCTS else _json({"detail": "not found"}, 404)
    if port == 8003:  # orders
        if path.startswith("/orders/"):
            oid = path.split("/orders/")[1]
            return _json(ORDERS[oid]) if oid in ORDERS else _json({"detail": "not found"}, 404)

    return _json({"detail": "unhandled"}, 500)


@pytest.fixture(autouse=True)
def mock_httpx(monkeypatch):
    """Force every AsyncClient created by the app to use the mock transport."""
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        # Respect an explicitly-provided transport (the ASGI client below);
        # otherwise route outbound calls through the mock fleet.
        kwargs.setdefault("transport", httpx.MockTransport(_handler))
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    # The client that talks to the GATEWAY itself uses the real ASGI transport,
    # created before the monkeypatch would interfere (ASGITransport is explicit).
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
