"""Alembic migration environment — Orders GraphQL service (async engine).

DB-per-service: this env targets ONLY the orders database. `target_metadata` is
the orders' `Base.metadata` (both the `orders` and `order_items` tables), so
`alembic revision --autogenerate` diffs against the orders models exclusively.
The database URL comes from the service Settings (app.config), so migrations
always hit the same database the app uses; docker-compose / production set
DATABASE_URL to the real Postgres instance.

Async pattern: Alembic itself is synchronous, so we build the service's
AsyncEngine and drive the (sync) migration ops through `connection.run_sync`.
"""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make the service's `app` package importable when alembic runs from the
# service directory (services/orders/). Belt-and-suspenders alongside the
# `prepend_sys_path = .` setting in alembic.ini.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402,F401 (import registers models on Base.metadata)
from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402

config = context.config

# Configure Python logging from the alembic.ini stanza.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate diffs against this service's own tables only.
target_metadata = Base.metadata

# Inject the DB URL from Settings so migrations target the app's database.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Silence an unused-import lint for the models module we imported for its
# side effect of registering tables on Base.metadata.
_ = models


def run_migrations_offline() -> None:
    """Emit SQL without a live DBAPI connection (`alembic upgrade --sql`)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Build the service's AsyncEngine and run migrations via run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
