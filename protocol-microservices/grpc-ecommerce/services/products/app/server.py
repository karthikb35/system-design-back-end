"""Server bootstrap — builds and runs the async gRPC server for Products."""
from __future__ import annotations

import asyncio

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from .config import get_settings
from .database import init_models
from .metrics import MetricsInterceptor
from .observability import CorrelationInterceptor, configure_logging
from .pb import products_pb2, products_pb2_grpc
from .servicer import ProductServicer

SERVICE_NAME = products_pb2.DESCRIPTOR.services_by_name["ProductService"].full_name


async def build_server(bind: str) -> tuple[grpc.aio.Server, int]:
    settings = get_settings()
    # Interceptors run outermost-first: MetricsInterceptor wraps the whole call
    # so its timing includes the correlation logging, and it records the final
    # status of every RPC (see app/metrics.py).
    server = grpc.aio.server(
        interceptors=[
            MetricsInterceptor(),
            CorrelationInterceptor(settings.service_name),
        ]
    )

    products_pb2_grpc.add_ProductServiceServicer_to_server(ProductServicer(), server)

    health_servicer = health.aio.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    await health_servicer.set(SERVICE_NAME, health_pb2.HealthCheckResponse.SERVING)
    await health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    port = server.add_insecure_port(bind)
    return server, port


async def serve() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    # In production the schema is owned by Alembic (`alembic upgrade head`);
    # create_all is a dev/test convenience only. Set AUTO_CREATE_SCHEMA=false in
    # prod so the running server never mutates the schema.
    if settings.auto_create_schema:
        await init_models()
    # Expose Prometheus metrics on a SEPARATE admin HTTP port. gRPC itself does
    # not speak the exposition format, so we start prometheus_client's tiny WSGI
    # server here, guarded by metrics_port (0 => disabled, the default, so tests
    # and local runs never bind an extra port).
    if settings.metrics_port:
        from prometheus_client import start_http_server

        start_http_server(settings.metrics_port)
    server, _ = await build_server(settings.grpc_bind)
    await server.start()
    print(f"{settings.service_name} gRPC server listening on {settings.grpc_bind}", flush=True)
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
