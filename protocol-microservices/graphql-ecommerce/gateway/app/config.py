"""Configuration for the GraphQL API Gateway.

The Gateway is a stateless GraphQL server that composes the three backend
GraphQL services. It has no database; it only needs their endpoints.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "gateway"
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    users_service_url: str = "http://localhost:8001"
    products_service_url: str = "http://localhost:8002"
    orders_service_url: str = "http://localhost:8003"

    http_timeout_seconds: float = 5.0

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
