"""gRPC clients used by the Gateway.

The Gateway holds one long-lived ``grpc.aio`` channel per backend service and a
typed stub on top of it. Each method translates an HTTP-shaped dict into a
protobuf request, calls the service, and converts the reply back into a plain
dict for JSON serialization. gRPC status codes are mapped to ``HTTPException``s.

Channels are created on FastAPI startup and closed on shutdown (see main.py).
"""
from __future__ import annotations

import grpc
from fastapi import HTTPException

from .config import get_settings
from .observability import outbound_metadata
from .pb import (
    orders_pb2,
    orders_pb2_grpc,
    products_pb2,
    products_pb2_grpc,
    users_pb2,
    users_pb2_grpc,
)

# gRPC status -> HTTP status. This is the inverse of what each servicer does.
_STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.ALREADY_EXISTS: 409,
    grpc.StatusCode.INVALID_ARGUMENT: 422,
    grpc.StatusCode.FAILED_PRECONDITION: 409,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.UNAVAILABLE: 502,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
}


def _to_http(exc: grpc.aio.AioRpcError) -> HTTPException:
    status = _STATUS_MAP.get(exc.code(), 500)
    return HTTPException(status_code=status, detail=exc.details() or exc.code().name)


def _user(reply) -> dict:
    return {
        "id": reply.id,
        "email": reply.email,
        "full_name": reply.full_name,
        "is_active": reply.is_active,
    }


def _product(reply) -> dict:
    return {
        "id": reply.id,
        "sku": reply.sku,
        "name": reply.name,
        "description": reply.description,
        "price_cents": reply.price_cents,
        "stock": reply.stock,
    }


def _order(reply) -> dict:
    return {
        "id": reply.id,
        "user_id": reply.user_id,
        "status": reply.status,
        "total_cents": reply.total_cents,
        "items": [
            {
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price_cents": i.unit_price_cents,
            }
            for i in reply.items
        ],
    }


class BackendClients:
    """Owns the channels + stubs for all three backend services."""

    def __init__(self) -> None:
        s = get_settings()
        self._timeout = s.grpc_timeout_seconds
        self._users_ch = grpc.aio.insecure_channel(s.users_service_addr)
        self._products_ch = grpc.aio.insecure_channel(s.products_service_addr)
        self._orders_ch = grpc.aio.insecure_channel(s.orders_service_addr)
        self.users = users_pb2_grpc.UserServiceStub(self._users_ch)
        self.products = products_pb2_grpc.ProductServiceStub(self._products_ch)
        self.orders = orders_pb2_grpc.OrderServiceStub(self._orders_ch)
        self.health = None  # health handled per-channel in health router

    async def close(self) -> None:
        await self._users_ch.close()
        await self._products_ch.close()
        await self._orders_ch.close()

    # --- Users ---------------------------------------------------------------
    async def create_user(self, body: dict) -> dict:
        req = users_pb2.CreateUserRequest(
            email=body["email"], full_name=body.get("full_name", ""), password=body["password"]
        )
        try:
            return _user(await self.users.CreateUser(req, metadata=outbound_metadata(), timeout=self._timeout))
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def get_user(self, user_id: str) -> dict:
        try:
            reply = await self.users.GetUser(
                users_pb2.GetUserRequest(id=user_id), metadata=outbound_metadata(), timeout=self._timeout
            )
            return _user(reply)
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def list_users(self, limit: int, offset: int) -> list[dict]:
        try:
            reply = await self.users.ListUsers(
                users_pb2.ListUsersRequest(limit=limit, offset=offset),
                metadata=outbound_metadata(), timeout=self._timeout,
            )
            return [_user(u) for u in reply.users]
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def login(self, body: dict) -> dict:
        try:
            reply = await self.users.Login(
                users_pb2.LoginRequest(email=body["email"], password=body["password"]),
                metadata=outbound_metadata(), timeout=self._timeout,
            )
            return {"access_token": reply.access_token, "token_type": reply.token_type}
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    # --- Products ------------------------------------------------------------
    async def create_product(self, body: dict) -> dict:
        req = products_pb2.CreateProductRequest(
            sku=body["sku"], name=body["name"], description=body.get("description", ""),
            price_cents=body["price_cents"], stock=body.get("stock", 0),
        )
        try:
            return _product(await self.products.CreateProduct(req, metadata=outbound_metadata(), timeout=self._timeout))
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def get_product(self, product_id: str) -> dict:
        try:
            reply = await self.products.GetProduct(
                products_pb2.GetProductRequest(id=product_id),
                metadata=outbound_metadata(), timeout=self._timeout,
            )
            return _product(reply)
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def list_products(self, limit: int, offset: int) -> list[dict]:
        try:
            reply = await self.products.ListProducts(
                products_pb2.ListProductsRequest(limit=limit, offset=offset),
                metadata=outbound_metadata(), timeout=self._timeout,
            )
            return [_product(p) for p in reply.products]
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    # --- Orders --------------------------------------------------------------
    async def place_order(self, body: dict) -> dict:
        req = orders_pb2.PlaceOrderRequest(
            user_id=body["user_id"],
            items=[
                orders_pb2.OrderItemInput(product_id=i["product_id"], quantity=i["quantity"])
                for i in body["items"]
            ],
        )
        try:
            return _order(await self.orders.PlaceOrder(req, metadata=outbound_metadata(), timeout=self._timeout))
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def get_order(self, order_id: str) -> dict:
        try:
            reply = await self.orders.GetOrder(
                orders_pb2.GetOrderRequest(id=order_id),
                metadata=outbound_metadata(), timeout=self._timeout,
            )
            return _order(reply)
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)

    async def list_orders(self, user_id: str, limit: int, offset: int) -> list[dict]:
        try:
            reply = await self.orders.ListOrders(
                orders_pb2.ListOrdersRequest(user_id=user_id, limit=limit, offset=offset),
                metadata=outbound_metadata(), timeout=self._timeout,
            )
            return [_order(o) for o in reply.orders]
        except grpc.aio.AioRpcError as exc:
            raise _to_http(exc)
