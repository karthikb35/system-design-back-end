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

    async def list_after(self, limit: int, after_id: str | None) -> list[Product]:
        """Keyset (cursor) pagination: the next `limit` products whose id sorts
        after `after_id`, ordered by id.

        Why prefer this over OFFSET for deep pages: `LIMIT n OFFSET k` still makes
        the database read and throw away the first k rows, so the cost of page N
        grows linearly with N (page 10,000 pays for 10,000 discarded rows). A
        keyset seek turns "next page" into `WHERE id > :cursor ORDER BY id LIMIT
        n`, which the primary-key index satisfies with a single range scan whose
        cost is independent of how deep into the collection we are. The trade-off
        is that keyset only walks forward/sequentially (no random "jump to page
        N"), which is exactly what infinite-scroll / streaming consumers want.
        """
        stmt = select(Product).order_by(Product.id).limit(limit)
        if after_id is not None:
            stmt = stmt.where(Product.id > after_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, product: Product) -> Product:
        """Persist changes to an already-tracked product (e.g. stock update)."""
        await self._session.commit()
        await self._session.refresh(product)
        return product
