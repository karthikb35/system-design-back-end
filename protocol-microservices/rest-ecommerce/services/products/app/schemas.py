"""API contract (DTOs) — the exact shapes that cross the wire.

Keeping these separate from the ORM models means the database schema can evolve
without silently changing the public API, and vice versa.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1024)
    price_cents: int = Field(ge=0)
    stock: int = Field(default=0, ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    description: str
    price_cents: int
    stock: int


class StockReservation(BaseModel):
    """Body for reserving (decrementing) stock — used by the Orders service."""

    quantity: int = Field(gt=0)


class ProductPage(BaseModel):
    """Keyset-pagination envelope: one page of products plus the cursor needed to
    request the page after it. `next_cursor` is null once the collection is
    exhausted, which is the client's signal to stop paging.
    """

    items: list[ProductOut]
    next_cursor: str | None = None
