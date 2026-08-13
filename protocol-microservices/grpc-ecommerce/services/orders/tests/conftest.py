"""Test fixtures for the Orders service.

The Orders service is a gRPC *client* of Users and Products, so to test it in
isolation we stand up two lightweight FAKE gRPC servers (in-memory dicts) that
implement the generated ``UserServiceServicer`` / ``ProductServiceServicer``
interfaces. The REAL Orders client code, orchestration, and serialization are
exercised end to end against them.
"""
from __future__ import annotations

import grpc
import pytest_asyncio
from app.clients import ProductsGrpcClient, UsersGrpcClient
from app.database import Base, engine
from app.pb import (
    orders_pb2_grpc,
    products_pb2,
    products_pb2_grpc,
    users_pb2,
    users_pb2_grpc,
)
from app.server import build_server


# --- Fake downstream servers -------------------------------------------------
class _FakeUserService(users_pb2_grpc.UserServiceServicer):
    def __init__(self) -> None:
        self.users = {"user-1": "buyer@example.com"}

    async def GetUser(self, request, context):
        email = self.users.get(request.id)
        if email is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "user not found")
        return users_pb2.UserReply(id=request.id, email=email, full_name="Buyer", is_active=True)


class _FakeProductService(products_pb2_grpc.ProductServiceServicer):
    def __init__(self) -> None:
        # id -> (name, price_cents, stock)
        self.products = {
            "prod-1": ["Keyboard", 4999, 10],
            "prod-2": ["Mouse", 2500, 1],
        }

    async def GetProduct(self, request, context):
        p = self.products.get(request.id)
        if p is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
        return products_pb2.ProductReply(
            id=request.id, sku=request.id, name=p[0], description="",
            price_cents=p[1], stock=p[2],
        )

    async def ReserveStock(self, request, context):
        p = self.products.get(request.id)
        if p is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
        if p[2] < request.quantity:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "insufficient stock")
        p[2] -= request.quantity
        return products_pb2.ProductReply(
            id=request.id, sku=request.id, name=p[0], description="",
            price_cents=p[1], stock=p[2],
        )

    async def ReleaseStock(self, request, context):
        # Compensation: add the units back. Tolerates unknown ids.
        p = self.products.get(request.id)
        if p is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
        p[2] += request.quantity
        return products_pb2.ProductReply(
            id=request.id, sku=request.id, name=p[0], description="",
            price_cents=p[1], stock=p[2],
        )


async def _start_fake(add_fn, servicer):
    server = grpc.aio.server()
    add_fn(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    return server, port


@pytest_asyncio.fixture
async def _reset_schema():
    # In-memory sqlite + StaticPool persists across tests in one process, so
    # rebuild the schema for isolation.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
def fake_users() -> _FakeUserService:
    return _FakeUserService()


@pytest_asyncio.fixture
def fake_products() -> _FakeProductService:
    # Exposed as a fixture so tests can inspect the catalog's stock (e.g. to
    # assert the Orders saga released a reservation after a partial failure).
    return _FakeProductService()


@pytest_asyncio.fixture
async def stub(_reset_schema, fake_users, fake_products):
    users_srv, users_port = await _start_fake(
        users_pb2_grpc.add_UserServiceServicer_to_server, fake_users
    )
    products_srv, products_port = await _start_fake(
        products_pb2_grpc.add_ProductServiceServicer_to_server, fake_products
    )

    users_channel = grpc.aio.insecure_channel(f"127.0.0.1:{users_port}")
    products_channel = grpc.aio.insecure_channel(f"127.0.0.1:{products_port}")
    users_client = UsersGrpcClient(users_channel)
    products_client = ProductsGrpcClient(products_channel)

    orders_srv, orders_port = await build_server("127.0.0.1:0", users_client, products_client)
    await orders_srv.start()

    orders_channel = grpc.aio.insecure_channel(f"127.0.0.1:{orders_port}")
    client = orders_pb2_grpc.OrderServiceStub(orders_channel)
    try:
        yield client
    finally:
        await orders_channel.close()
        await users_channel.close()
        await products_channel.close()
        await orders_srv.stop(grace=0.5)
        await users_srv.stop(grace=0.5)
        await products_srv.stop(grace=0.5)
        # Close the sqlite connection in-loop (see users/tests/conftest note).
        await engine.dispose()
