"""Test fixtures for the Orders service.

The Orders service normally calls the Users and Products services over HTTP. In
tests we replace those clients with in-memory fakes via
`app.dependency_overrides`, so the full checkout flow runs with no network and no
other services running.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from app.database import init_models
from app.dependencies import get_products_client, get_users_client
from app.main import app
from httpx import ASGITransport, AsyncClient


class FakeUsersClient:
    def __init__(self, known: set[str]) -> None:
        self._known = known

    async def user_exists(self, user_id: str) -> bool:
        return user_id in self._known


class FakeProductsClient:
    """In-memory catalog: {product_id: {"price_cents", "stock"}}."""

    def __init__(self, catalog: dict[str, dict]) -> None:
        self._catalog = catalog

    async def get_product(self, product_id: str) -> dict:
        from app.clients import ProductUnavailable

        if product_id not in self._catalog:
            raise ProductUnavailable(f"product {product_id} not found")
        p = self._catalog[product_id]
        return {"id": product_id, "price_cents": p["price_cents"], "stock": p["stock"]}

    async def reserve(self, product_id: str, quantity: int) -> dict:
        from app.clients import ProductUnavailable

        if product_id not in self._catalog:
            raise ProductUnavailable(f"product {product_id} not found")
        p = self._catalog[product_id]
        if p["stock"] < quantity:
            raise ProductUnavailable(f"insufficient stock for {product_id}")
        p["stock"] -= quantity
        return {"id": product_id, "price_cents": p["price_cents"], "stock": p["stock"]}

    async def release(self, product_id: str, quantity: int) -> None:
        # Compensation: add the units back. Tolerates unknown ids like the real
        # client (a deleted product simply has nothing to release).
        p = self._catalog.get(product_id)
        if p is not None:
            p["stock"] += quantity


@pytest.fixture
def known_users() -> set[str]:
    return {"user-1"}


@pytest.fixture
def catalog() -> dict[str, dict]:
    return {
        "prod-1": {"price_cents": 1000, "stock": 5},
        "prod-2": {"price_cents": 2500, "stock": 2},
    }


@pytest_asyncio.fixture
async def client(known_users, catalog) -> AsyncClient:
    await init_models()
    app.dependency_overrides[get_users_client] = lambda: FakeUsersClient(known_users)
    app.dependency_overrides[get_products_client] = lambda: FakeProductsClient(catalog)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
