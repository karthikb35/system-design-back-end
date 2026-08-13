"""FastAPI application hosting the Strawberry GraphQL schema for Products."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from .config import get_settings
from .database import init_models
from .metrics import PrometheusMiddleware
from .metrics import router as metrics_router
from .observability import CorrelationMiddleware, configure_logging
from .schema import schema


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # In production the schema is owned by Alembic migrations (`alembic upgrade
    # head`), applied as a deploy step against the products database. create_all
    # is a dev/test convenience only; disable it in prod by setting
    # AUTO_CREATE_SCHEMA=false so the running app never mutates the schema.
    if get_settings().auto_create_schema:
        await init_models()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Products GraphQL service", lifespan=_lifespan)
    app.add_middleware(CorrelationMiddleware, service_name=settings.service_name)
    app.add_middleware(PrometheusMiddleware)

    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")
    app.include_router(metrics_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.service_name}

    return app


app = create_app()
