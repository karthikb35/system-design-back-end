"""GraphQL schema — the transport adapter for the Orders service.

Resolvers read the injected downstream clients out of the GraphQL ``context``
(wired in main.py from ``app.state``), open a DB session, call the orchestration
service, and translate domain exceptions into ``GraphQLError``s.
"""
from __future__ import annotations

import strawberry
from graphql import GraphQLError
from strawberry.types import Info

from .clients import DownstreamError
from .database import SessionLocal
from .models import Order as OrderModel
from .repository import OrderRepository
from .service import (
    OrderNotFound,
    OrderService,
    ProductUnavailable,
    UserNotFound,
    ValidationError,
)


@strawberry.type(description="One line of an order, with a price snapshot.")
class OrderItem:
    product_id: strawberry.ID
    quantity: int
    unit_price_cents: int


@strawberry.type(description="A confirmed order.")
class Order:
    id: strawberry.ID
    user_id: strawberry.ID
    status: str
    total_cents: int
    items: list[OrderItem]

    @classmethod
    def from_model(cls, m: OrderModel) -> "Order":
        return cls(
            id=strawberry.ID(m.id),
            user_id=strawberry.ID(m.user_id),
            status=m.status,
            total_cents=m.total_cents,
            items=[
                OrderItem(
                    product_id=strawberry.ID(i.product_id),
                    quantity=i.quantity,
                    unit_price_cents=i.unit_price_cents,
                )
                for i in m.items
            ],
        )


@strawberry.input(description="One requested line item.")
class OrderItemInput:
    product_id: strawberry.ID
    quantity: int


def _service(session, info: Info) -> OrderService:
    return OrderService(
        OrderRepository(session),
        info.context["users_client"],
        info.context["products_client"],
    )


@strawberry.type
class Query:
    @strawberry.field(description="Fetch a single order by id.")
    async def order(self, id: strawberry.ID, info: Info) -> Order:
        async with SessionLocal() as session:
            try:
                return Order.from_model(await _service(session, info).get(str(id)))
            except OrderNotFound:
                raise GraphQLError("order not found")

    @strawberry.field(description="List a user's orders (paginated).")
    async def orders(self, user_id: strawberry.ID, info: Info, limit: int = 50, offset: int = 0) -> list[Order]:
        async with SessionLocal() as session:
            rows = await _service(session, info).list_for_user(str(user_id), limit=limit, offset=offset)
            return [Order.from_model(o) for o in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Place an order: validate buyer, reserve stock, persist.")
    async def place_order(self, user_id: strawberry.ID, items: list[OrderItemInput], info: Info) -> Order:
        pairs = [(str(i.product_id), i.quantity) for i in items]
        async with SessionLocal() as session:
            try:
                order = await _service(session, info).place_order(str(user_id), pairs)
            except ValidationError as exc:
                raise GraphQLError(str(exc))
            except UserNotFound:
                raise GraphQLError("buyer does not exist")
            except ProductUnavailable as exc:
                raise GraphQLError(exc.detail)
            except DownstreamError:
                raise GraphQLError("a downstream service is unavailable")
            return Order.from_model(order)


schema = strawberry.Schema(query=Query, mutation=Mutation)
