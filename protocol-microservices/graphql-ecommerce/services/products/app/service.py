"""Service layer — catalog rules including stock reservation."""
from __future__ import annotations

from .models import Product
from .repository import ProductRepository


class ValidationError(Exception):
    """Input failed a business validation rule."""


class SkuAlreadyExists(Exception):
    """A product with this SKU already exists."""


class ProductNotFound(Exception):
    """No product with the given id."""


class InsufficientStock(Exception):
    """Not enough stock to satisfy the requested quantity."""


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    async def create(self, sku: str, name: str, description: str, price_cents: int, stock: int) -> Product:
        if not sku or not name:
            raise ValidationError("sku and name are required")
        if price_cents < 0:
            raise ValidationError("price_cents must be non-negative")
        if stock < 0:
            raise ValidationError("stock must be non-negative")
        if await self._repo.get_by_sku(sku) is not None:
            raise SkuAlreadyExists(sku)
        product = Product(
            sku=sku, name=name, description=description or "", price_cents=price_cents, stock=stock
        )
        return await self._repo.add(product)

    async def get(self, product_id: str) -> Product:
        product = await self._repo.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    async def list(self, limit: int = 50, offset: int = 0) -> list[Product]:
        return await self._repo.list(limit=limit, offset=offset)

    async def reserve_stock(self, product_id: str, quantity: int) -> Product:
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        product = await self.get(product_id)
        if product.stock < quantity:
            raise InsufficientStock(f"only {product.stock} of {product_id} in stock")
        product.stock -= quantity
        return await self._repo.save(product)

    async def release_stock(self, product_id: str, quantity: int) -> Product:
        """Compensating action for ``reserve_stock``: return ``quantity`` units.

        The Orders saga calls this to undo a reservation when a checkout fails
        partway through. Releasing only ever *increases* stock, so it is always
        safe to run (and safe to re-run) — the property a valid compensation needs.
        """
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        product = await self.get(product_id)
        product.stock += quantity
        return await self._repo.save(product)
