"""Server bootstrap — builds and runs the async gRPC server for Orders.

Unlike Users/Products, Orders is also a gRPC *client*, so it opens channels to
the Users and Products services and wraps them in typed clients that the servicer
uses. ``build_server`` accepts those clients so tests can inject clients pointed
at fake in-process servers.
"""
from __future__ import annotations

import asyncio

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from .clients import ProductsGrpcClient, UsersGrpcClient
from .config import get_settings
from .database import init_models
from .metrics import MetricsInterceptor
from .observability import CorrelationInterceptor, configure_logging
from .pb import orders_pb2, orders_pb2_grpc
from .servicer import OrderServicer

SERVICE_NAME = orders_pb2.DESCRIPTOR.services_by_name["OrderService"].full_name


async def build_server(
    bind: str,
    users_client: UsersGrpcClient,
    products_client: ProductsGrpcClient,
) -> tuple[grpc.aio.Server, int]:
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

    orders_pb2_grpc.add_OrderServiceServicer_to_server(
        OrderServicer(users_client, products_client), server
    )

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

    # Long-lived channels to the downstream services.
    users_channel = grpc.aio.insecure_channel(settings.users_service_addr)
    products_channel = grpc.aio.insecure_channel(settings.products_service_addr)
    users_client = UsersGrpcClient(users_channel)
    products_client = ProductsGrpcClient(products_channel)

    server, _ = await build_server(settings.grpc_bind, users_client, products_client)
    await server.start()
    print(f"{settings.service_name} gRPC server listening on {settings.grpc_bind}", flush=True)
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
