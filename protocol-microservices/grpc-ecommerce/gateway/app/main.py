"""FastAPI application factory for the API Gateway.

The Gateway is an HTTP -> gRPC translator. On startup it opens one gRPC channel
per backend service (stored on ``app.state.clients``); on shutdown it closes
them. Routers read the clients off the app state.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .clients import BackendClients
from .config import get_settings
from .metrics import PrometheusMiddleware
from .metrics import router as metrics_router
from .observability import CorrelationMiddleware, configure_logging
from .routers import aggregate, health, proxy_routes


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.clients = BackendClients()
    try:
        yield
    finally:
        await app.state.clients.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="E-commerce API Gateway (gRPC backend)", lifespan=_lifespan)
    app.add_middleware(CorrelationMiddleware)
    # Added last => outermost, so it times the full request (including the
    # correlation middleware) and always sees the final status code.
    app.add_middleware(PrometheusMiddleware)

    app.include_router(health.router)
    app.include_router(metrics_router)
    app.include_router(aggregate.router)
    app.include_router(proxy_routes.router)
    return app


app = create_app()
