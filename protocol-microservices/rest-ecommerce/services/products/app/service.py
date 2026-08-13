"""Service layer — catalog business rules.

The important rule lives in `reserve_stock`: an order may only be fulfilled if
there is enough inventory. Enforcing this here (not in the router) keeps the
rule in one place and unit-testable.
"""
from __future__ import annotations

from .models import Product
from .repository import ProductRepository
from .schemas import ProductCreate


class SkuAlreadyExists(Exception):
    """Raised when creating a product with a SKU that is already taken."""


class ProductNotFound(Exception):
    """Raised when a product id does not exist."""


class InsufficientStock(Exception):
    """Raised when a reservation asks for more units than are in stock."""


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    async def create(self, data: ProductCreate) -> Product:
        if await self._repo.get_by_sku(data.sku):
            raise SkuAlreadyExists(data.sku)
        product = Product(
            sku=data.sku,
            name=data.name,
            description=data.description,
            price_cents=data.price_cents,
            stock=data.stock,
        )
        return await self._repo.add(product)

    async def get(self, product_id: str) -> Product:
        product = await self._repo.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    async def list(self, limit: int = 50, offset: int = 0) -> list[Product]:
        return await self._repo.list(limit=limit, offset=offset)

    async def list_keyset(self, limit: int, after_id: str | None) -> list[Product]:
        """Cursor-based listing (see `ProductRepository.list_after`)."""
        return await self._repo.list_after(limit=limit, after_id=after_id)

    async def reserve_stock(self, product_id: str, quantity: int) -> Product:
        product = await self.get(product_id)
        if product.stock < quantity:
            raise InsufficientStock(f"{product_id}: have {product.stock}, need {quantity}")
        product.stock -= quantity
        return await self._repo.save(product)

    async def release_stock(self, product_id: str, quantity: int) -> Product:
        """Compensating action for :meth:`reserve_stock`: return ``quantity`` units
        to stock.

        The Orders saga calls this when a checkout fails after some items were
        already reserved. Releasing only ever *increases* stock, so it is always
        safe and idempotent-friendly (re-running it just adds inventory back),
        which is exactly the property a valid compensation needs.
        """
        product = await self.get(product_id)
        product.stock += quantity
        return await self._repo.save(product)
