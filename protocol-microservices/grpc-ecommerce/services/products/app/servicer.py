"""gRPC servicer — the adapter between protobuf and the service layer.

Domain error -> gRPC status mapping:
  ValidationError   -> INVALID_ARGUMENT
  SkuAlreadyExists  -> ALREADY_EXISTS
  ProductNotFound   -> NOT_FOUND
  InsufficientStock -> FAILED_PRECONDITION
"""
from __future__ import annotations

import grpc

from .database import SessionLocal
from .pb import products_pb2, products_pb2_grpc
from .repository import ProductRepository
from .service import (
    InsufficientStock,
    ProductNotFound,
    ProductService,
    SkuAlreadyExists,
    ValidationError,
)


def _to_reply(p) -> products_pb2.ProductReply:
    return products_pb2.ProductReply(
        id=p.id,
        sku=p.sku,
        name=p.name,
        description=p.description,
        price_cents=p.price_cents,
        stock=p.stock,
    )


class ProductServicer(products_pb2_grpc.ProductServiceServicer):
    async def CreateProduct(self, request, context) -> products_pb2.ProductReply:
        async with SessionLocal() as session:
            svc = ProductService(ProductRepository(session))
            try:
                product = await svc.create(
                    request.sku, request.name, request.description, request.price_cents, request.stock
                )
            except ValidationError as exc:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            except SkuAlreadyExists:
                await context.abort(grpc.StatusCode.ALREADY_EXISTS, "sku already exists")
            return _to_reply(product)

    async def GetProduct(self, request, context) -> products_pb2.ProductReply:
        async with SessionLocal() as session:
            svc = ProductService(ProductRepository(session))
            try:
                product = await svc.get(request.id)
            except ProductNotFound:
                await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
            return _to_reply(product)

    async def ListProducts(self, request, context) -> products_pb2.ListProductsReply:
        async with SessionLocal() as session:
            svc = ProductService(ProductRepository(session))
            limit = request.limit or 50
            products = await svc.list(limit=limit, offset=request.offset)
            return products_pb2.ListProductsReply(products=[_to_reply(p) for p in products])

    async def ReserveStock(self, request, context) -> products_pb2.ProductReply:
        async with SessionLocal() as session:
            svc = ProductService(ProductRepository(session))
            try:
                product = await svc.reserve_stock(request.id, request.quantity)
            except ValidationError as exc:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            except ProductNotFound:
                await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
            except InsufficientStock:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, "insufficient stock")
            return _to_reply(product)

    async def ReleaseStock(self, request, context) -> products_pb2.ProductReply:
        # Compensating action for ReserveStock. Adding stock back can never be
        # "insufficient", so there is no FAILED_PRECONDITION path here.
        async with SessionLocal() as session:
            svc = ProductService(ProductRepository(session))
            try:
                product = await svc.release_stock(request.id, request.quantity)
            except ValidationError as exc:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            except ProductNotFound:
                await context.abort(grpc.StatusCode.NOT_FOUND, "product not found")
            return _to_reply(product)
