"""Configuration for the Users GraphQL service."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "users"
    http_host: str = "0.0.0.0"
    http_port: int = 8001

    database_url: str = "sqlite+aiosqlite:///:memory:"

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
    return Settings()
