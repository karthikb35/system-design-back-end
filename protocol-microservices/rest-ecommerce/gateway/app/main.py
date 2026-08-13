"""Application entry point — assembles the API Gateway app (stateless)."""
from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .metrics import PrometheusMiddleware
from .metrics import router as metrics_router
from .observability import CorrelationIdMiddleware, configure_logging
from .routers import aggregate, health, proxy_routes

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    description="The single public entry point; proxies and aggregates the services.",
)

app.add_middleware(CorrelationIdMiddleware, service_name=settings.service_name)
app.add_middleware(PrometheusMiddleware)
app.include_router(health.router)
app.include_router(metrics_router)
app.include_router(aggregate.router)
app.include_router(proxy_routes.router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": settings.service_name,
        "routes": ["/api/users/*", "/api/products/*", "/api/orders/*", "/aggregate/orders/{id}"],
        "docs": "/docs",
    }
