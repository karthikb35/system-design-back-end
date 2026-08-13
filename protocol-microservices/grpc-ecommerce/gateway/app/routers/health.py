"""Health endpoints — the Gateway's own liveness plus a fan-out readiness check.

``GET /health`` is always 200 (the Gateway process is up). ``GET /health/ready``
probes every backend service's gRPC Health service in parallel and reports each
one, returning 503 if any dependency is not SERVING.
"""
from __future__ import annotations

import asyncio

import grpc
from fastapi import APIRouter, Request, Response
from grpc_health.v1 import health_pb2, health_pb2_grpc

from ..config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


async def _probe(addr: str) -> bool:
    try:
        async with grpc.aio.insecure_channel(addr) as channel:
            stub = health_pb2_grpc.HealthStub(channel)
            resp = await stub.Check(health_pb2.HealthCheckRequest(service=""), timeout=2)
            return resp.status == health_pb2.HealthCheckResponse.SERVING
    except grpc.aio.AioRpcError:
        return False


@router.get("/health/ready")
async def ready(request: Request, response: Response):
    s = get_settings()
    targets = {
        "users": s.users_service_addr,
        "products": s.products_service_addr,
        "orders": s.orders_service_addr,
    }
    results = await asyncio.gather(*[_probe(addr) for addr in targets.values()])
    statuses = {name: ("serving" if ok else "down") for name, ok in zip(targets, results)}
    if not all(results):
        response.status_code = 503
    return {"status": "ready" if all(results) else "degraded", "dependencies": statuses}
