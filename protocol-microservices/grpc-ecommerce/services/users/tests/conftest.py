"""Test fixtures — a real in-process gRPC server on an ephemeral port.

This exercises the *whole* stack: interceptor, servicer, service, repository, and
protobuf serialization — the same code paths that run in production, just over a
loopback channel and an in-memory SQLite database.
"""
from __future__ import annotations

import grpc
import pytest_asyncio

from app.database import Base, engine
from app.pb import users_pb2_grpc
from app.server import build_server


async def _reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def stub():
    await _reset_schema()
    server, port = await build_server("127.0.0.1:0")
    await server.start()
    async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
        yield users_pb2_grpc.UserServiceStub(channel)
    await server.stop(grace=None)
