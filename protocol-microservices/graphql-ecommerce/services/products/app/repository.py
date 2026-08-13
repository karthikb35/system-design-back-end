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

    async def save(self, product: Product) -> Product:
        await self._session.commit()
        await self._session.refresh(product)
        return product
