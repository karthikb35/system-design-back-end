"""FastAPI application hosting the Orders GraphQL schema.

Orders is also a GraphQL *client*, so it owns two ``httpx.AsyncClient``s (one per
downstream service) wrapped in typed clients. Those are stored on ``app.state``
and exposed to resolvers through the GraphQL ``context``. Tests inject their own
clients (pointed at fake in-process apps); when none are injected, the lifespan
builds real ones from settings and closes them on shutdown.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from .clients import ProductsGraphQLClient, UsersGraphQLClient
from .config import get_settings
from .database import init_models
from .metrics import PrometheusMiddleware
from .metrics import router as metrics_router
from .observability import CorrelationMiddleware, configure_logging
from .schema import schema


async def _get_context(request: Request) -> dict:
    return {
        "users_client": request.app.state.users_client,
        "products_client": request.app.state.products_client,
    }


def create_app(
    users_client: UsersGraphQLClient | None = None,
    products_client: ProductsGraphQLClient | None = None,
) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    injected = users_client is not None and products_client is not None

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        # In production the schema is owned by Alembic migrations (`alembic
        # upgrade head`), applied as a deploy step against the orders database.
        # create_all is a dev/test convenience only; disable it in prod by
        # setting AUTO_CREATE_SCHEMA=false so the app never mutates the schema.
        if settings.auto_create_schema:
            await init_models()
        owned: list[httpx.AsyncClient] = []
        if not injected:
            users_http = httpx.AsyncClient(base_url=settings.users_service_url)
            products_http = httpx.AsyncClient(base_url=settings.products_service_url)
            owned = [users_http, products_http]
            app.state.users_client = UsersGraphQLClient(users_http)
            app.state.products_client = ProductsGraphQLClient(products_http)
        try:
            yield
        finally:
            for c in owned:
                await c.aclose()

    app = FastAPI(title="Orders GraphQL service", lifespan=_lifespan)
    app.add_middleware(CorrelationMiddleware, service_name=settings.service_name)
    app.add_middleware(PrometheusMiddleware)

    app.state.users_client = users_client
    app.state.products_client = products_client

    graphql_app = GraphQLRouter(schema, context_getter=_get_context)
    app.include_router(graphql_app, prefix="/graphql")
    app.include_router(metrics_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.service_name}

    return app


app = create_app()
