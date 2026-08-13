"""Test fixtures — an httpx client wired to the app over an in-memory SQLite DB."""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import init_models
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await init_models()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
