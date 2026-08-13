"""Configuration for the Products gRPC service."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "products"
    grpc_bind: str = "[::]:50052"

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

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
