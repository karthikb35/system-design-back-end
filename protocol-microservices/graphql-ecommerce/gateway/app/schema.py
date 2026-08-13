"""The unified Gateway schema — a single graph over three services.

This is where GraphQL shines compared to REST/gRPC. Instead of a bespoke
``/aggregate/orders/{id}`` endpoint, the Gateway exposes ONE graph where an
``Order`` naturally has a ``buyer: User`` field and each ``OrderItem`` has a
``product: Product`` field. The client asks for exactly the nesting it wants and
the Gateway resolves each field by calling the owning service — only when that
field is actually requested.

```graphql
query {
  order(id: "…") {
    totalCents
    buyer { fullName }
    items { quantity product { name } }
  }
}
```
"""
from __future__ import annotations

import strawberry
from strawberry.types import Info


def _clients(info: Info):
    return info.context["clients"]


def _loaders(info: Info):
    # Request-scoped DataLoaders (see app/loaders.py) that batch the buyer/product
    # fan-out to defeat the N+1 problem.
    return info.context["loaders"]


@strawberry.type
class User:
    id: strawberry.ID
    email: str
    full_name: str
    is_active: bool

    @classmethod
    def from_dict(cls, d: dict) -> User:
        return cls(id=strawberry.ID(d["id"]), email=d["email"], full_name=d["fullName"], is_active=d["isActive"])


@strawberry.type
class AuthToken:
    access_token: str
    token_type: str


@strawberry.type
class Product:
    id: strawberry.ID
    sku: str
    name: str
    description: str
    price_cents: int
    stock: int

    @classmethod
    def from_dict(cls, d: dict) -> Product:
        return cls(
            id=strawberry.ID(d["id"]),
            sku=d["sku"],
            name=d["name"],
            description=d["description"],
            price_cents=d["priceCents"],
            stock=d["stock"],
        )


@strawberry.type
class OrderItem:
    product_id: strawberry.ID
    quantity: int
    unit_price_cents: int

    @strawberry.field(description="The product for this line, fetched from the Products service on demand.")
    async def product(self, info: Info) -> Product | None:
        # Batched via the request's products DataLoader: N items across a request
        # collapse into ONE Products backend call per distinct id (N+1 -> 1+1).
        d = await _loaders(info)["products"].load(str(self.product_id))
        return Product.from_dict(d) if d else None


@strawberry.type
class Order:
    id: strawberry.ID
    user_id: strawberry.ID
    status: str
    total_cents: int
    items: list[OrderItem]

    @strawberry.field(description="The buyer, fetched from the Users service on demand.")
    async def buyer(self, info: Info) -> User | None:
        # Batched via the request's users DataLoader: many orders sharing a buyer
        # dedupe to a single Users backend call (N+1 -> 1+1).
        d = await _loaders(info)["users"].load(str(self.user_id))
        return User.from_dict(d) if d else None

    @classmethod
    def from_dict(cls, d: dict) -> Order:
        return cls(
            id=strawberry.ID(d["id"]),
            user_id=strawberry.ID(d["userId"]),
            status=d["status"],
            total_cents=d["totalCents"],
            items=[
                OrderItem(
                    product_id=strawberry.ID(i["productId"]),
                    quantity=i["quantity"],
                    unit_price_cents=i["unitPriceCents"],
                )
                for i in d["items"]
            ],
        )


@strawberry.input
class OrderItemInput:
    product_id: strawberry.ID
    quantity: int


@strawberry.type
class Query:
    @strawberry.field
    async def user(self, id: strawberry.ID, info: Info) -> User | None:
        d = await _clients(info).get_user(str(id))
        return User.from_dict(d) if d else None

    @strawberry.field
    async def users(self, info: Info, limit: int = 50, offset: int = 0) -> list[User]:
        return [User.from_dict(u) for u in await _clients(info).list_users(limit, offset)]

    @strawberry.field
    async def product(self, id: strawberry.ID, info: Info) -> Product | None:
        d = await _clients(info).get_product(str(id))
        return Product.from_dict(d) if d else None

    @strawberry.field
    async def products(self, info: Info, limit: int = 50, offset: int = 0) -> list[Product]:
        return [Product.from_dict(p) for p in await _clients(info).list_products(limit, offset)]

    @strawberry.field
    async def order(self, id: strawberry.ID, info: Info) -> Order:
        return Order.from_dict(await _clients(info).get_order(str(id)))

    @strawberry.field
    async def orders(self, user_id: strawberry.ID, info: Info, limit: int = 50, offset: int = 0) -> list[Order]:
        rows = await _clients(info).list_orders(str(user_id), limit, offset)
        return [Order.from_dict(o) for o in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, email: str, password: str, info: Info, full_name: str = "") -> User:
        return User.from_dict(await _clients(info).create_user(email, password, full_name))

    @strawberry.mutation
    async def login(self, email: str, password: str, info: Info) -> AuthToken:
        d = await _clients(info).login(email, password)
        return AuthToken(access_token=d["accessToken"], token_type=d["tokenType"])

    @strawberry.mutation
    async def create_product(
        self, sku: str, name: str, price_cents: int, info: Info, description: str = "", stock: int = 0
    ) -> Product:
        return Product.from_dict(
            await _clients(info).create_product(sku, name, price_cents, description, stock)
        )

    @strawberry.mutation
    async def place_order(self, user_id: strawberry.ID, items: list[OrderItemInput], info: Info) -> Order:
        payload = [{"productId": str(i.product_id), "quantity": i.quantity} for i in items]
        return Order.from_dict(await _clients(info).place_order(str(user_id), payload))


schema = strawberry.Schema(query=Query, mutation=Mutation)
