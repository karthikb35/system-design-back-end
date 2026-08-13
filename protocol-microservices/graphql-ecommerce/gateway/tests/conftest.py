"""Gateway test fixtures.

The Gateway composes three backend GraphQL services, so the harness builds three
FAKE Strawberry apps (Users, Products, Orders) with in-memory data and wires the
REAL Gateway ``BackendClients`` to them via in-process ASGI transports. The real
gateway schema — including the ``Order.buyer`` and ``OrderItem.product`` field
resolvers that fan out — is exercised end to end.
"""
from __future__ import annotations

import httpx
import pytest_asyncio
import strawberry
from fastapi import FastAPI
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter

from app.clients import BackendClients
from app.main import create_app

# --- In-memory backend data --------------------------------------------------
USERS = {"user-1": {"email": "buyer@example.com", "fullName": "Buyer One", "isActive": True}}
PRODUCTS = {
    "prod-1": {"sku": "KB1", "name": "Keyboard", "description": "", "priceCents": 4999, "stock": 10},
    "prod-2": {"sku": "MS1", "name": "Mouse", "description": "", "priceCents": 2999, "stock": 5},
}
ORDERS: dict[str, dict] = {}


# --- Fake Users --------------------------------------------------------------
@strawberry.type
class _User:
    id: strawberry.ID
    email: str
    full_name: str
    is_active: bool


@strawberry.type
class _UQuery:
    @strawberry.field
    async def user(self, id: strawberry.ID) -> _User:
        u = USERS.get(str(id))
        if u is None:
            raise GraphQLError("user not found")
        return _User(id=id, email=u["email"], full_name=u["fullName"], is_active=u["isActive"])


@strawberry.type
class _UMutation:
    @strawberry.mutation
    async def create_user(self, email: str, password: str, full_name: str = "") -> _User:
        uid = f"user-{len(USERS) + 1}"
        USERS[uid] = {"email": email, "fullName": full_name, "isActive": True}
        return _User(id=strawberry.ID(uid), email=email, full_name=full_name, is_active=True)


# --- Fake Products -----------------------------------------------------------
@strawberry.type
class _Product:
    id: strawberry.ID
    sku: str
    name: str
    description: str
    price_cents: int
    stock: int


@strawberry.type
class _PQuery:
    @strawberry.field
    async def product(self, id: strawberry.ID) -> _Product:
        p = PRODUCTS.get(str(id))
        if p is None:
            raise GraphQLError("product not found")
        return _Product(id=id, sku=p["sku"], name=p["name"], description=p["description"],
                        price_cents=p["priceCents"], stock=p["stock"])


# --- Fake Orders -------------------------------------------------------------
@strawberry.type
class _OItem:
    product_id: strawberry.ID
    quantity: int
    unit_price_cents: int


@strawberry.type
class _Order:
    id: strawberry.ID
    user_id: strawberry.ID
    status: str
    total_cents: int
    items: list[_OItem]


@strawberry.input(name="OrderItemInput")
class _OItemInput:
    product_id: strawberry.ID
    quantity: int


def _order_obj(d: dict) -> _Order:
    return _Order(
        id=strawberry.ID(d["id"]), user_id=strawberry.ID(d["userId"]), status=d["status"],
        total_cents=d["totalCents"],
        items=[_OItem(product_id=strawberry.ID(i["productId"]), quantity=i["quantity"], unit_price_cents=i["unitPriceCents"]) for i in d["items"]],
    )


@strawberry.type
class _OQuery:
    @strawberry.field
    async def order(self, id: strawberry.ID) -> _Order:
        d = ORDERS.get(str(id))
        if d is None:
            raise GraphQLError("order not found")
        return _order_obj(d)

    @strawberry.field
    async def orders(self, user_id: strawberry.ID, limit: int = 50, offset: int = 0) -> list[_Order]:
        rows = [d for d in ORDERS.values() if d["userId"] == str(user_id)]
        return [_order_obj(d) for d in rows[offset : offset + limit]]


@strawberry.type
class _OMutation:
    @strawberry.mutation
    async def place_order(self, user_id: strawberry.ID, items: list[_OItemInput]) -> _Order:
        oid = f"order-{len(ORDERS) + 1}"
        item_dicts = [
            {"productId": str(i.product_id), "quantity": i.quantity, "unitPriceCents": PRODUCTS[str(i.product_id)]["priceCents"]}
            for i in items
        ]
        total = sum(i["unitPriceCents"] * i["quantity"] for i in item_dicts)
        d = {"id": oid, "userId": str(user_id), "status": "confirmed", "totalCents": total, "items": item_dicts}
        ORDERS[oid] = d
        return _order_obj(d)


def _mount(query, mutation=None) -> FastAPI:
    app = FastAPI()
    app.include_router(GraphQLRouter(strawberry.Schema(query=query, mutation=mutation)), prefix="/graphql")
    return app


def _build_backends() -> tuple[httpx.AsyncClient, httpx.AsyncClient, httpx.AsyncClient]:
    """Three fake backend GraphQL apps wired over in-process ASGI transports."""
    uh = httpx.AsyncClient(transport=httpx.ASGITransport(app=_mount(_UQuery, _UMutation)), base_url="http://users")
    ph = httpx.AsyncClient(transport=httpx.ASGITransport(app=_mount(_PQuery)), base_url="http://products")
    oh = httpx.AsyncClient(transport=httpx.ASGITransport(app=_mount(_OQuery, _OMutation)), base_url="http://orders")
    return uh, ph, oh


class CountingClients(BackendClients):
    """A ``BackendClients`` that records every single-id user/product fetch.

    The DataLoader's batch functions call ``get_user`` / ``get_product`` exactly
    once per *distinct* id per request, so these counters let a test prove the
    N+1 collapse: many ``.load(id)`` calls with duplicate ids turn into far fewer
    backend calls (ideally one per distinct id).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_calls: list[str] = []
        self.product_calls: list[str] = []

    async def get_user(self, user_id: str):
        self.user_calls.append(user_id)
        return await super().get_user(user_id)

    async def get_product(self, product_id: str):
        self.product_calls.append(product_id)
        return await super().get_product(product_id)


@pytest_asyncio.fixture
async def client():
    ORDERS.clear()

    uh, ph, oh = _build_backends()

    app = create_app(clients=BackendClients(uh, ph, oh))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    await uh.aclose()
    await ph.aclose()
    await oh.aclose()


@pytest_asyncio.fixture
async def counting_client():
    """Like ``client`` but yields ``(ac, counting)`` so a test can inspect how
    many backend calls the DataLoaders actually made."""
    ORDERS.clear()

    uh, ph, oh = _build_backends()

    counting = CountingClients(uh, ph, oh)
    app = create_app(clients=counting)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, counting

    await uh.aclose()
    await ph.aclose()
    await oh.aclose()


async def gql(client: httpx.AsyncClient, query: str, variables: dict | None = None) -> dict:
    resp = await client.post("/graphql", json={"query": query, "variables": variables or {}})
    assert resp.status_code == 200, resp.text
    return resp.json()
