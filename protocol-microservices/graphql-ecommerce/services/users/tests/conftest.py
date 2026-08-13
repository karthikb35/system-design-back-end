"""Test fixtures for the Users GraphQL service.

We drive the real FastAPI app over an in-process ASGI transport and reset the
in-memory sqlite schema before every test (StaticPool keeps one connection alive,
so data would otherwise leak between tests).
"""
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


async def gql(
    client: httpx.AsyncClient,
    query: str,
    variables: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """POST a GraphQL document and return the parsed JSON body.

    ``headers`` lets a test attach an ``Authorization`` header to exercise the
    protected ``users`` list query.
    """
    resp = await client.post(
        "/graphql",
        json={"query": query, "variables": variables or {}},
        headers=headers or {},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
