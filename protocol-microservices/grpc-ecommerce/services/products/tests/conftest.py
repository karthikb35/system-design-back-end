"""Test fixtures — a real in-process gRPC server on an ephemeral port."""
from __future__ import annotations

import grpc
import pytest_asyncio
from app.database import Base, SessionLocal, engine
from app.pb import products_pb2_grpc
from app.repository import ProductRepository
from app.server import build_server
from app.service import ProductService


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
        yield products_pb2_grpc.ProductServiceStub(channel)
    await server.stop(grace=0.5)
    # Dispose the (module-level) engine so its single StaticPool sqlite
    # connection is closed inside this test's event loop, rather than being
    # finalized later by the GC in a dead loop (which raises GeneratorExit).
    await engine.dispose()


@pytest_asyncio.fixture
async def service():
    """A ProductService on a fresh schema for exercising the layer directly.

    The keyset pagination reference lives below the transport (no RPC field), so
    we drive it through the service/repository rather than a gRPC stub.
    """
    await _reset_schema()
    async with SessionLocal() as session:
        yield ProductService(ProductRepository(session))
    await engine.dispose()
