"""Configuration — loaded once from environment variables via pydantic-settings.

Even though the transport is gRPC, we still use pydantic-settings for the same
twelve-factor reason: all config comes from the environment, never hard-coded.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "users"
    # host:port the gRPC server binds to inside its container.
    grpc_bind: str = "[::]:50051"

    database_url: str = "sqlite+aiosqlite:///:memory:"

    # Schema ownership. In production the schema is managed by Alembic
    # migrations (`alembic upgrade head`); create_all is a dev/test convenience
    # only. Set AUTO_CREATE_SCHEMA=false to rely purely on migrations.
    auto_create_schema: bool = True

    # Prometheus exposition port. gRPC servers have no HTTP surface, so metrics
    # are scraped from this SEPARATE admin port via prometheus_client's tiny
    # WSGI server (started in server.serve). 0 disables it — the default so
    # tests never bind a port.
    metrics_port: int = 0

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
