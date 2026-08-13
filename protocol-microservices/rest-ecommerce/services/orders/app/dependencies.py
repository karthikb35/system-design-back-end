"""Injectable dependencies for the Orders service.

Defining the downstream clients as FastAPI dependencies lets tests override them
(`app.dependency_overrides`) with in-memory fakes, so the whole checkout flow can
be tested without running the Users or Products services.
"""
from __future__ import annotations

from .clients import ProductsClient, UsersClient


def get_users_client() -> UsersClient:
    return UsersClient()


def get_products_client() -> ProductsClient:
    return ProductsClient()
