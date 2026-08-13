"""Configuration for the API Gateway.

The Gateway is a stateless HTTP -> gRPC translator. It has no database; it only
needs the gRPC addresses of the three backend services.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "gateway"
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    users_service_addr: str = "localhost:50051"
    products_service_addr: str = "localhost:50052"
    orders_service_addr: str = "localhost:50053"

    grpc_timeout_seconds: float = 5.0

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
