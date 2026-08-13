"""Aggregation routes — the value a gateway adds beyond plain proxying.

A single client call fans out to several services and the gateway combines the
results. This reduces client round-trips and hides the internal topology.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_settings
from ..observability import REQUEST_ID_HEADER, request_id_ctx

router = APIRouter(prefix="/aggregate", tags=["aggregate"])


class OrderSummaryItem(BaseModel):
    product_id: str
    name: str | None
    quantity: int
    unit_price_cents: int


class OrderSummary(BaseModel):
    order_id: str
    buyer_name: str | None
    total_cents: int
    items: list[OrderSummaryItem]


def _headers() -> dict[str, str]:
    return {REQUEST_ID_HEADER: request_id_ctx.get()}


@router.get("/orders/{order_id}", response_model=OrderSummary)
async def order_summary(order_id: str) -> OrderSummary:
    """Return an order enriched with buyer name and product names.

    Fans out: Orders (the order) -> Users (buyer name) + Products (each name).
    """
    s = get_settings()
    timeout = httpx.Timeout(s.http_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, headers=_headers()) as client:
        order_resp = await client.get(f"{s.orders_service_url}/orders/{order_id}")
        order_resp.raise_for_status()
        order = order_resp.json()

        # Enrich with the buyer's name.
        buyer_name = None
        user_resp = await client.get(f"{s.users_service_url}/users/{order['user_id']}")
        if user_resp.status_code == 200:
            buyer_name = user_resp.json().get("full_name")

        # Enrich each line with the product's name.
        items: list[OrderSummaryItem] = []
        for line in order["items"]:
            name = None
            p_resp = await client.get(f"{s.products_service_url}/products/{line['product_id']}")
            if p_resp.status_code == 200:
                name = p_resp.json().get("name")
            items.append(
                OrderSummaryItem(
                    product_id=line["product_id"],
                    name=name,
                    quantity=line["quantity"],
                    unit_price_cents=line["unit_price_cents"],
                )
            )

    return OrderSummary(
        order_id=order["id"],
        buyer_name=buyer_name,
        total_cents=order["total_cents"],
        items=items,
    )
