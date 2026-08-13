"""Aggregation endpoint — one call to the Gateway, several calls fanned out.

``GET /aggregate/orders/{id}`` returns an order enriched with the buyer's name
and each line item's product name. This is a classic API-gateway responsibility:
the client makes a single request and the Gateway composes the response from
multiple backend services in parallel.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request

from ..clients import BackendClients

router = APIRouter(prefix="/aggregate", tags=["aggregate"])


def _clients(request: Request) -> BackendClients:
    return request.app.state.clients


@router.get("/orders/{order_id}")
async def enriched_order(order_id: str, request: Request):
    clients = _clients(request)
    order = await clients.get_order(order_id)

    # Fan out: buyer + every distinct product, all in parallel.
    product_ids = {i["product_id"] for i in order["items"]}
    buyer_task = clients.get_user(order["user_id"])
    product_tasks = {pid: clients.get_product(pid) for pid in product_ids}

    buyer, *products = await asyncio.gather(
        buyer_task, *product_tasks.values(), return_exceptions=True
    )
    product_by_id = {}
    for pid, result in zip(product_tasks.keys(), products):
        if not isinstance(result, Exception):
            product_by_id[pid] = result

    enriched_items = [
        {
            **item,
            "product_name": product_by_id.get(item["product_id"], {}).get("name"),
        }
        for item in order["items"]
    ]

    return {
        **order,
        "buyer_name": None if isinstance(buyer, Exception) else buyer["full_name"],
        "items": enriched_items,
    }
