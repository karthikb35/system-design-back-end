"""Health endpoints — liveness and readiness (Kubernetes-style).

- /health/live  : is the process up? (never touches the DB)
- /health/ready : can it serve traffic? (checks the DB connection)

They answer different questions: a failing liveness probe restarts the pod; a
failing readiness probe just removes it from the load balancer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict:
    return {"status": "alive"}


@router.get("/health/ready")
async def ready(response: Response, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:  # noqa: BLE001 - report not-ready on any DB error
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not-ready"}
