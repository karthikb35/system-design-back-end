"""Database wiring — the async SQLAlchemy engine, session factory, and helpers.

One engine per process (a connection pool), and one short-lived AsyncSession per
request (created and closed by the `get_session` dependency).
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """Declarative base that all ORM models inherit from."""


_settings = get_settings()

_engine_kwargs: dict = {"echo": False, "future": True}
if _settings.database_url.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool

    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(_settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a request-scoped session, always closed."""
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """Create tables if they don't exist (dev/demo convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
