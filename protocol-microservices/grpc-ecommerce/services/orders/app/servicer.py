"""gRPC servicer — the adapter between protobuf and the orchestration service.

Domain error -> gRPC status mapping:
  ValidationError   -> INVALID_ARGUMENT
  UserNotFound      -> FAILED_PRECONDITION (buyer must exist first)
  ProductUnavailable-> FAILED_PRECONDITION (missing / oversold)
  DownstreamError   -> UNAVAILABLE (a dependency failed)
  OrderNotFound     -> NOT_FOUND
"""
from __future__ import annotations

import grpc

from .clients import DownstreamError, ProductsGrpcClient, UsersGrpcClient
from .database import SessionLocal
from .pb import orders_pb2, orders_pb2_grpc
from .repository import OrderRepository
from .service import (
    OrderNotFound,
    OrderService,
    ProductUnavailable,
    UserNotFound,
    ValidationError,
)


def _to_reply(order) -> orders_pb2.OrderReply:
    return orders_pb2.OrderReply(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_cents=order.total_cents,
        items=[
            orders_pb2.OrderItemReply(
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in order.items
        ],
    )


class OrderServicer(orders_pb2_grpc.OrderServiceServicer):
    def __init__(self, users_client: UsersGrpcClient, products_client: ProductsGrpcClient) -> None:
        self._users = users_client
        self._products = products_client

    async def PlaceOrder(self, request, context) -> orders_pb2.OrderReply:
        items = [(i.product_id, i.quantity) for i in request.items]
        async with SessionLocal() as session:
            svc = OrderService(OrderRepository(session), self._users, self._products)
            try:
                order = await svc.place_order(request.user_id, items)
            except ValidationError as exc:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            except UserNotFound:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "buyer does not exist")
            except ProductUnavailable as exc:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, exc.detail)
            except DownstreamError:
                await context.abort(grpc.StatusCode.UNAVAILABLE, "a downstream service is unavailable")
            return _to_reply(order)

    async def GetOrder(self, request, context) -> orders_pb2.OrderReply:
        async with SessionLocal() as session:
            svc = OrderService(OrderRepository(session), self._users, self._products)
            try:
                order = await svc.get(request.id)
            except OrderNotFound:
                await context.abort(grpc.StatusCode.NOT_FOUND, "order not found")
            return _to_reply(order)

    async def ListOrders(self, request, context) -> orders_pb2.ListOrdersReply:
        async with SessionLocal() as session:
            svc = OrderService(OrderRepository(session), self._users, self._products)
            limit = request.limit or 50
            orders = await svc.list_for_user(request.user_id, limit=limit, offset=request.offset)
            return orders_pb2.ListOrdersReply(orders=[_to_reply(o) for o in orders])
