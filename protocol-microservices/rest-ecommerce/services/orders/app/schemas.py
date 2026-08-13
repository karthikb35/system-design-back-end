"""API contract (DTOs) for the Orders service."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OrderItemIn(BaseModel):
    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: str = Field(min_length=1)
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    quantity: int
    unit_price_cents: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: str
    total_cents: int
    items: list[OrderItemOut]
