"""Gateway test fixtures.

The Gateway is a pure HTTP -> gRPC translator, so the test harness stands up
three FAKE in-process gRPC servers (Users, Products, Orders) on ephemeral ports,
points the Gateway's settings at them, then drives the Gateway over HTTP via an
ASGI transport. The REAL gateway routing, translation, and status mapping run.
"""
from __future__ import annotations

import grpc
import httpx
import pytest_asyncio
from app.config import get_settings
from app.pb import (
    orders_pb2,
    orders_pb2_grpc,
    products_pb2,
    products_pb2_grpc,
    users_pb2,
    users_pb2_grpc,
)
from grpc_health.v1 import health, health_pb2, health_pb2_grpc


class _Users(users_pb2_grpc.UserServiceServicer):
    def __init__(self):
        self.by_id = {"user-1": ("buyer@example.com", "Buyer One")}

    async def CreateUser(self, request, context):
        uid = f"user-{len(self.by_id) + 1}"
        self.by_id[uid] = (request.email, request.full_name)
        return users_pb2.UserReply(id=uid, email=request.email, full_name=request.full_name, is_active=True)

    async def GetUser(self, request, context):
        u = self.by_id.get(request.id)
        if u is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "user not found")
        return users_pb2.UserReply(id=request.id, email=u[0], full_name=u[1], is_active=True)

    async def ListUsers(self, request, context):
        return users_pb2.ListUsersReply(
            users=[users_pb2.UserReply(id=k, email=v[0], full_name=v[1], is_active=True) for k, v in self.by_id.items()]
        )

    async def Login(self, request, context):
        return users_pb2.TokenReply(access_token="tok", token_type="bearer")


class _Products(products_pb2_grpc.ProductServiceServicer):
    def __init__(self):
        self.by_id = {"prod-1": ["SKU1", "Keyboard", "", 4999, 10]}

    async def CreateProduct(self, request, context):
        pid = f"prod-{len(self.by_id) + 1}"
        self.by_id[pid] = [request.sku, request.name, request.description, request.price_cents, request.stock]
        p = self.by_id[pid]
        return products_pb2.ProductReply(id=pid, sku=p[0], name=p[1], description=p[2], price_cents=p[3], stock=p[4])

    async def GetProduct(self, request, context):
        p = self.by_id.get(request.id)
        if p is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
        return products_pb2.ProductReply(id=request.id, sku=p[0], name=p[1], description=p[2], price_cents=p[3], stock=p[4])

    async def ListProducts(self, request, context):
        return products_pb2.ListProductsReply(
            products=[
                products_pb2.ProductReply(id=k, sku=v[0], name=v[1], description=v[2], price_cents=v[3], stock=v[4])
                for k, v in self.by_id.items()
            ]
        )

    async def ReserveStock(self, request, context):
        p = self.by_id[request.id]
        p[4] -= request.quantity
        return products_pb2.ProductReply(id=request.id, sku=p[0], name=p[1], description=p[2], price_cents=p[3], stock=p[4])


class _Orders(orders_pb2_grpc.OrderServiceServicer):
    def __init__(self):
        self.by_id = {}

    async def PlaceOrder(self, request, context):
        oid = f"order-{len(self.by_id) + 1}"
        items = [
            orders_pb2.OrderItemReply(product_id=i.product_id, quantity=i.quantity, unit_price_cents=4999)
            for i in request.items
        ]
        total = sum(i.unit_price_cents * i.quantity for i in items)
        reply = orders_pb2.OrderReply(id=oid, user_id=request.user_id, status="confirmed", total_cents=total, items=items)
        self.by_id[oid] = reply
        return reply

    async def GetOrder(self, request, context):
        o = self.by_id.get(request.id)
        if o is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "order not found")
        return o

    async def ListOrders(self, request, context):
        return orders_pb2.ListOrdersReply(
            orders=[o for o in self.by_id.values() if o.user_id == request.user_id]
        )


async def _start(add_fn, servicer):
    server = grpc.aio.server()
    add_fn(servicer, server)
    health_servicer = health.aio.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    await health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    return server, port


@pytest_asyncio.fixture
async def client():
    us, up = await _start(users_pb2_grpc.add_UserServiceServicer_to_server, _Users())
    ps, pp = await _start(products_pb2_grpc.add_ProductServiceServicer_to_server, _Products())
    os_, op = await _start(orders_pb2_grpc.add_OrderServiceServicer_to_server, _Orders())

    # Point the (cached) settings at the fake servers, then build the app.
    get_settings.cache_clear()
    settings = get_settings()
    settings.users_service_addr = f"127.0.0.1:{up}"
    settings.products_service_addr = f"127.0.0.1:{pp}"
    settings.orders_service_addr = f"127.0.0.1:{op}"

    from app.main import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    await us.stop(grace=0.5)
    await ps.stop(grace=0.5)
    await os_.stop(grace=0.5)
    get_settings.cache_clear()
