"""Service layer — catalog business rules (transport-agnostic).

The core rule is in ``reserve_stock``: never oversell. It raises domain
exceptions; the servicer maps them to gRPC status codes.
"""
from __future__ import annotations

from .models import Product
from .repository import ProductRepository


class SkuAlreadyExists(Exception):
    """Creating a product with a SKU that already exists."""


class ProductNotFound(Exception):
    """A product id does not exist."""


class InsufficientStock(Exception):
    """A reservation asked for more units than are in stock."""


class ValidationError(Exception):
    """Input failed a business validation rule."""


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    async def create(self, sku: str, name: str, description: str, price_cents: int, stock: int) -> Product:
        if not sku or not name:
            raise ValidationError("sku and name are required")
        if price_cents < 0 or stock < 0:
            raise ValidationError("price_cents and stock must be non-negative")
        if await self._repo.get_by_sku(sku):
            raise SkuAlreadyExists(sku)
        product = Product(
            sku=sku, name=name, description=description, price_cents=price_cents, stock=stock
        )
        return await self._repo.add(product)

    async def get(self, product_id: str) -> Product:
        product = await self._repo.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    async def list(self, limit: int = 50, offset: int = 0) -> list[Product]:
        return await self._repo.list(limit=limit, offset=offset)

    async def list_keyset(
        self, cursor_id: str | None = None, limit: int = 50
    ) -> tuple[list[Product], str | None]:
        """Return one keyset page plus the cursor to fetch the next one.

        The caller passes ``cursor_id=None`` for the first page, then feeds back
        the returned ``next_cursor`` for each subsequent page. ``next_cursor`` is
        the id of the last row when a full page came back (there may be more), and
        ``None`` once a short page proves the catalog is exhausted — the signal to
        stop paging. This is the transport-agnostic half of keyset pagination;
        wiring it to an RPC field is out of scope (would require a proto change).
        """
        items = await self._repo.list_after(cursor_id, limit)
        next_cursor = items[-1].id if len(items) == limit else None
        return items, next_cursor

    async def reserve_stock(self, product_id: str, quantity: int) -> Product:
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        product = await self.get(product_id)
        if product.stock < quantity:
            raise InsufficientStock(f"{product_id}: have {product.stock}, need {quantity}")
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
