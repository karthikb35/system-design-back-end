"""Test fixtures for the Products GraphQL service."""
from __future__ import annotations

import httpx
import pytest_asyncio
from app.database import Base, engine, init_models
from app.main import create_app


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_models()

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def gql(client: httpx.AsyncClient, query: str, variables: dict | None = None) -> dict:
    resp = await client.post("/graphql", json={"query": query, "variables": variables or {}})
    assert resp.status_code == 200, resp.text
    return resp.json()
