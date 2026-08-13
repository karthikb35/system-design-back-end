"""FastAPI application hosting the unified Gateway GraphQL schema.

The Gateway owns one ``httpx.AsyncClient`` per backend service. They are created
on startup and closed on shutdown, and exposed to resolvers through the GraphQL
context. Tests inject their own clients (pointed at fake in-process apps).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from .clients import BackendClients
from .config import get_settings
from .loaders import build_loaders
from .metrics import PrometheusMiddleware
from .metrics import router as metrics_router
from .observability import CorrelationMiddleware, configure_logging
from .schema import schema


async def _get_context(request: Request) -> dict:
    # `clients` is shared for the app's lifetime; `loaders` are rebuilt PER
    # REQUEST so their batching/caching is request-scoped and never bleeds one
    # caller's data into another's.
    clients = request.app.state.clients
    return {"clients": clients, "loaders": build_loaders(clients)}


def create_app(clients: BackendClients | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    injected = clients is not None

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        owned: list[httpx.AsyncClient] = []
        if not injected:
            users_http = httpx.AsyncClient(base_url=settings.users_service_url)
            products_http = httpx.AsyncClient(base_url=settings.products_service_url)
            orders_http = httpx.AsyncClient(base_url=settings.orders_service_url)
            owned = [users_http, products_http, orders_http]
            app.state.clients = BackendClients(users_http, products_http, orders_http)
        try:
            yield
        finally:
            for c in owned:
                await c.aclose()

    app = FastAPI(title="E-commerce API Gateway (GraphQL)", lifespan=_lifespan)
    app.add_middleware(CorrelationMiddleware, service_name=settings.service_name)
    app.add_middleware(PrometheusMiddleware)

    app.state.clients = clients

    graphql_app = GraphQLRouter(schema, context_getter=_get_context)
    app.include_router(graphql_app, prefix="/graphql")
    app.include_router(metrics_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.service_name}

    return app


app = create_app()
