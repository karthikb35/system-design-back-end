"""Configuration — loaded once from environment variables via pydantic-settings.

Twelve-factor style: all config comes from the environment, never hard-coded, so
the same image runs in dev/staging/prod with different values injected.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "users"

    # Async SQLAlchemy URL. Defaults to in-memory SQLite so the app/tests run
    # with zero infrastructure; docker-compose overrides it with Postgres.
    database_url: str = "sqlite+aiosqlite:///:memory:"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Schema ownership. In production the schema is managed by Alembic
    # migrations (`alembic upgrade head`); create_all is a dev/test convenience
    # only. Set AUTO_CREATE_SCHEMA=false to rely purely on migrations.
    auto_create_schema: bool = True

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the environment is parsed exactly once per process."""
    return Settings()
