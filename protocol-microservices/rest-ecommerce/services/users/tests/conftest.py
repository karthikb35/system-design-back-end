"""Test fixtures — an httpx client wired to the app over an in-memory SQLite DB.

The app already defaults to `sqlite+aiosqlite:///:memory:`, so no Postgres is
needed. We create the schema once per test and use ASGITransport so requests go
straight to the app in-process (fast, no network).
"""
from __future__ import annotations

import pytest
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
