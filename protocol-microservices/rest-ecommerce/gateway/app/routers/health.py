"""Gateway health — liveness plus an aggregated view of downstream readiness."""
from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter

from ..config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict:
    return {"status": "alive"}


async def _probe(client: httpx.AsyncClient, name: str, base_url: str) -> tuple[str, str]:
    try:
        resp = await client.get(f"{base_url}/health/ready")
        return name, "ready" if resp.status_code == 200 else "not-ready"
    except httpx.HTTPError:
        return name, "unreachable"


@router.get("/health/ready")
async def ready() -> dict:
    """Fan out to every downstream service's readiness probe, in parallel."""
    s = get_settings()
    targets = {
        "users": s.users_service_url,
        "products": s.products_service_url,
        "orders": s.orders_service_url,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
        results = await asyncio.gather(
            *(_probe(client, name, url) for name, url in targets.items())
        )
    statuses = dict(results)
    overall = "ready" if all(v == "ready" for v in statuses.values()) else "degraded"
    return {"status": overall, "services": statuses}
