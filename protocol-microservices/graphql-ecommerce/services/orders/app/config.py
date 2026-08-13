"""Configuration for the Orders GraphQL service.

Besides its own port and database, Orders needs the GraphQL endpoints of the two
services it *calls* (Users and Products) plus client tuning (timeout + retries).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "orders"
    http_host: str = "0.0.0.0"
    http_port: int = 8003

    database_url: str = "sqlite+aiosqlite:///:memory:"

    # Downstream GraphQL endpoints (overridden by docker-compose service names).
    users_service_url: str = "http://localhost:8001"
    products_service_url: str = "http://localhost:8002"

    http_timeout_seconds: float = 5.0
    http_max_retries: int = 3

    # Circuit breaker (per downstream dependency). After `cb_failure_threshold`
    # calls fail in a row the breaker opens and further calls fail fast for
    # `cb_recovery_seconds`, after which a single trial call probes recovery.
    cb_failure_threshold: int = 5
    cb_recovery_seconds: float = 30.0

    # Schema ownership. In production the schema is managed by Alembic
    # migrations (`alembic upgrade head`); create_all is a dev/test convenience
    # only. Set AUTO_CREATE_SCHEMA=false to rely purely on migrations.
    auto_create_schema: bool = True

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
