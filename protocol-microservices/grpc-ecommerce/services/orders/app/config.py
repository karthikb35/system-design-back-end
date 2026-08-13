"""Configuration for the Orders gRPC service.

Besides its own bind address and database, Orders needs the addresses of the two
services it *calls* (Users and Products) plus client tuning (timeout + retries).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "orders"
    grpc_bind: str = "[::]:50053"

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

    # Downstream gRPC targets (overridden by docker-compose service names).
    users_service_addr: str = "localhost:50051"
    products_service_addr: str = "localhost:50052"

    # Client behaviour for the outbound gRPC calls.
    grpc_timeout_seconds: float = 5.0
    grpc_max_retries: int = 3

    # Circuit breaker (per downstream dependency). After `cb_failure_threshold`
    # calls fail in a row the breaker opens and further calls fail fast for
    # `cb_recovery_seconds`, after which a single trial call probes recovery.
    cb_failure_threshold: int = 5
    cb_recovery_seconds: float = 30.0

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
