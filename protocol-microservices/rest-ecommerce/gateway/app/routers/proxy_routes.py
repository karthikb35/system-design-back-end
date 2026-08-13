"""Pass-through proxy routes.

Each catch-all route forwards the request to the matching downstream service.
This keeps the public API surface stable even if internal service URLs change.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..config import get_settings
from ..proxy import forward

router = APIRouter(prefix="/api", tags=["proxy"])


def _urls():
    s = get_settings()
    return {
        "users": s.users_service_url,
        "products": s.products_service_url,
        "orders": s.orders_service_url,
    }


@router.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_users(path: str, request: Request) -> Response:
    body = await request.body()
    return await forward(request.method, _urls()["users"], f"/users/{path}", body=body)


@router.api_route("/products/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_products(path: str, request: Request) -> Response:
    body = await request.body()
    return await forward(request.method, _urls()["products"], f"/products/{path}", body=body)


@router.api_route("/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_orders(path: str, request: Request) -> Response:
    body = await request.body()
    return await forward(request.method, _urls()["orders"], f"/orders/{path}", body=body)
