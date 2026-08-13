"""Application entry point — assembles the FastAPI app for the Products service."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .database import init_models
from .metrics import PrometheusMiddleware
from .metrics import router as metrics_router
from .observability import CorrelationIdMiddleware, configure_logging
from .routers import health, products

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In production the schema is owned by Alembic migrations (`alembic upgrade
    # head`), applied as a deploy step against this service's own database.
    # create_all is a dev/test convenience only; disable it in prod by setting
    # AUTO_CREATE_SCHEMA=false so the running app never mutates the schema.
    if settings.auto_create_schema:
        await init_models()
    yield


app = FastAPI(
    title="Products Service",
    version="1.0.0",
    description="Owns the product catalog and inventory for the e-commerce system.",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware, service_name=settings.service_name)
app.add_middleware(PrometheusMiddleware)
app.include_router(health.router)
app.include_router(metrics_router)
app.include_router(products.router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {"service": settings.service_name, "docs": "/docs"}
