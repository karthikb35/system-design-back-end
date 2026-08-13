"""Test fixtures for the Orders GraphQL service.

Orders is a GraphQL *client* of Users and Products, so we build two tiny FAKE
Strawberry apps (in-memory data) and wire the REAL Orders clients to them via an
in-process ASGI transport. The real Orders client code, orchestration, and
GraphQL serialization are all exercised.
"""
from __future__ import annotations

import httpx
import pytest_asyncio
import strawberry
from app.clients import ProductsGraphQLClient, UsersGraphQLClient
from app.database import Base, engine, init_models
from app.main import create_app
from fastapi import FastAPI
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter

# --- Fake Users GraphQL app --------------------------------------------------
_USERS = {"user-1"}


@strawberry.type
class _FUser:
    id: strawberry.ID


@strawberry.type
class _UsersQuery:
    @strawberry.field
    async def user(self, id: strawberry.ID) -> _FUser:
        if str(id) not in _USERS:
            raise GraphQLError("user not found")
        return _FUser(id=id)


def _users_app() -> FastAPI:
    app = FastAPI()
    app.include_router(GraphQLRouter(strawberry.Schema(query=_UsersQuery)), prefix="/graphql")
    return app


# --- Fake Products GraphQL app ----------------------------------------------
_PRODUCTS = {
    "prod-1": {"name": "Keyboard", "priceCents": 4999, "stock": 10},
    "prod-2": {"name": "Mouse", "priceCents": 2500, "stock": 1},
}


@strawberry.type
class _FProduct:
    id: strawberry.ID
    name: str
    price_cents: int
    stock: int


@strawberry.type
class _ProductsQuery:
    @strawberry.field
    async def product(self, id: strawberry.ID) -> _FProduct:
        p = _PRODUCTS.get(str(id))
        if p is None:
            raise GraphQLError("product not found")
        return _FProduct(id=id, name=p["name"], price_cents=p["priceCents"], stock=p["stock"])


@strawberry.type
class _ProductsMutation:
    @strawberry.mutation
    async def reserve_stock(self, id: strawberry.ID, quantity: int) -> _FProduct:
        p = _PRODUCTS.get(str(id))
        if p is None:
            raise GraphQLError("product not found")
        if p["stock"] < quantity:
            raise GraphQLError(f"only {p['stock']} in stock")
        p["stock"] -= quantity
        return _FProduct(id=id, name=p["name"], price_cents=p["priceCents"], stock=p["stock"])

    @strawberry.mutation
    async def release_stock(self, id: strawberry.ID, quantity: int) -> _FProduct:
        # Compensation: add the units back (tolerates unknown ids like the real one).
        p = _PRODUCTS.get(str(id))
        if p is None:
            raise GraphQLError("product not found")
        p["stock"] += quantity
        return _FProduct(id=id, name=p["name"], price_cents=p["priceCents"], stock=p["stock"])


def _products_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        GraphQLRouter(strawberry.Schema(query=_ProductsQuery, mutation=_ProductsMutation)),
        prefix="/graphql",
    )
    return app


def _reset_fakes() -> None:
    _PRODUCTS["prod-1"]["stock"] = 10
    _PRODUCTS["prod-2"]["stock"] = 1


@pytest_asyncio.fixture
def products_state() -> dict:
    # The same in-memory catalog the fake Products app mutates, so a test can
    # assert the Orders saga released a reservation after a partial failure.
    return _PRODUCTS


@pytest_asyncio.fixture
async def client():
    _reset_fakes()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_models()

    users_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=_users_app()), base_url="http://users")
    products_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=_products_app()), base_url="http://products")
    users_client = UsersGraphQLClient(users_http)
    products_client = ProductsGraphQLClient(products_http)

    app = create_app(users_client=users_client, products_client=products_client)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    await users_http.aclose()
    await products_http.aclose()


async def gql(client: httpx.AsyncClient, query: str, variables: dict | None = None) -> dict:
    resp = await client.post("/graphql", json={"query": query, "variables": variables or {}})
    assert resp.status_code == 200, resp.text
    return resp.json()
