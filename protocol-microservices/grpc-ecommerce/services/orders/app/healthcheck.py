"""Tiny health-probe client used by Docker's HEALTHCHECK."""
from __future__ import annotations

import asyncio
import sys

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

TARGET = "localhost:50053"


async def _check() -> int:
    try:
        async with grpc.aio.insecure_channel(TARGET) as channel:
            stub = health_pb2_grpc.HealthStub(channel)
            resp = await stub.Check(health_pb2.HealthCheckRequest(service=""), timeout=2)
            return 0 if resp.status == health_pb2.HealthCheckResponse.SERVING else 1
    except grpc.aio.AioRpcError:
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_check()))
