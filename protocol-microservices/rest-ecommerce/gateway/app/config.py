"""Configuration for the API Gateway (stateless — no database)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "gateway"

    users_service_url: str = "http://localhost:8001"
    products_service_url: str = "http://localhost:8002"
    orders_service_url: str = "http://localhost:8003"

    http_timeout_seconds: float = 5.0
    http_max_retries: int = 3

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
