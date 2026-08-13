"""GraphQL schema — the transport adapter for the Products service."""
from __future__ import annotations

import strawberry
from graphql import GraphQLError

from .database import SessionLocal
from .models import Product as ProductModel
from .repository import ProductRepository
from .service import (
    InsufficientStock,
    ProductNotFound,
    ProductService,
    SkuAlreadyExists,
    ValidationError,
)


@strawberry.type(description="A catalog product. Price is an integer number of cents.")
class Product:
    id: strawberry.ID
    sku: str
    name: str
    description: str
    price_cents: int
    stock: int

    @classmethod
    def from_model(cls, m: ProductModel) -> Product:
        return cls(
            id=strawberry.ID(m.id),
            sku=m.sku,
            name=m.name,
            description=m.description,
            price_cents=m.price_cents,
            stock=m.stock,
        )


def _service(session) -> ProductService:
    return ProductService(ProductRepository(session))


@strawberry.type
class Query:
    @strawberry.field(description="Fetch a single product by id.")
    async def product(self, id: strawberry.ID) -> Product:
        async with SessionLocal() as session:
            try:
                return Product.from_model(await _service(session).get(str(id)))
            except ProductNotFound:
                raise GraphQLError("product not found")

    @strawberry.field(description="List products (paginated).")
    async def products(self, limit: int = 50, offset: int = 0) -> list[Product]:
        async with SessionLocal() as session:
            rows = await _service(session).list(limit=limit, offset=offset)
            return [Product.from_model(p) for p in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Add a product to the catalog.")
    async def create_product(
        self, sku: str, name: str, price_cents: int, description: str = "", stock: int = 0
    ) -> Product:
        async with SessionLocal() as session:
            try:
                product = await _service(session).create(sku, name, description, price_cents, stock)
            except ValidationError as exc:
                raise GraphQLError(str(exc))
            except SkuAlreadyExists:
                raise GraphQLError("sku already exists")
            return Product.from_model(product)

    @strawberry.mutation(description="Reserve (decrement) stock during checkout.")
    async def reserve_stock(self, id: strawberry.ID, quantity: int) -> Product:
        async with SessionLocal() as session:
            try:
                product = await _service(session).reserve_stock(str(id), quantity)
            except ValidationError as exc:
                raise GraphQLError(str(exc))
            except ProductNotFound:
                raise GraphQLError("product not found")
            except InsufficientStock as exc:
                raise GraphQLError(str(exc))
            return Product.from_model(product)

    @strawberry.mutation(
        description="Release (increment) previously-reserved stock — saga compensation."
    )
    async def release_stock(self, id: strawberry.ID, quantity: int) -> Product:
        # Compensating action for reserve_stock. Adding stock back can never be
        # "insufficient", so there is no InsufficientStock path here.
        async with SessionLocal() as session:
            try:
                product = await _service(session).release_stock(str(id), quantity)
            except ValidationError as exc:
                raise GraphQLError(str(exc))
            except ProductNotFound:
                raise GraphQLError("product not found")
            return Product.from_model(product)


schema = strawberry.Schema(query=Query, mutation=Mutation)
