"""Repository layer — the ONLY place that talks to the database."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def get(self, product_id: str) -> Product | None:
        return await self._session.get(Product, product_id)

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self._session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> list[Product]:
        result = await self._session.execute(
            select(Product).order_by(Product.created_at).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def list_after(self, cursor_id: str | None, limit: int) -> list[Product]:
        """Keyset (cursor) pagination: the next ``limit`` rows with id > cursor.

        Why keyset beats OFFSET for deep pages: ``OFFSET n`` makes the database
        walk and throw away the first ``n`` matching rows every time, so page 1000
        re-scans everything before it — cost grows linearly with page depth. A
        keyset seek instead asks "give me the rows just after this id"; the
        primary-key index jumps straight there, so every page costs the same
        O(log n) regardless of depth. The trade-off is you page by an ordered key
        (here the id) rather than by an arbitrary page number.
        """
        stmt = select(Product).order_by(Product.id).limit(limit)
        if cursor_id is not None:
            stmt = stmt.where(Product.id > cursor_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, product: Product) -> Product:
        await self._session.commit()
        await self._session.refresh(product)
        return product
