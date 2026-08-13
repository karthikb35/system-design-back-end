"""Configuration — loaded once from environment variables via pydantic-settings.

In addition to the database URL, the Orders service needs the URLs of the two
services it depends on (Users and Products) plus HTTP client tuning.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "orders"
    database_url: str = "sqlite+aiosqlite:///:memory:"

    # Downstream service base URLs (overridden by docker-compose service names).
    users_service_url: str = "http://localhost:8001"
    products_service_url: str = "http://localhost:8002"

    # HTTP client behaviour for service-to-service calls.
    http_timeout_seconds: float = 5.0
    http_max_retries: int = 3

    # Circuit breaker (per downstream dependency). Once `cb_failure_threshold`
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
