"""Prometheus metrics for the gRPC server — the RED method over RPCs.

The HTTP world records Rate/Errors/Duration with a middleware; gRPC has no HTTP
middleware, so its equivalent is a **server interceptor**. This module defines
the two RED time-series and a ``MetricsInterceptor`` that records them for every
RPC — crucially INCLUDING aborts/errors, because a metrics signal that only
counts successes hides exactly the failures you page on.

NO ``/metrics`` ROUTE HERE
--------------------------
These services speak gRPC (HTTP/2 + protobuf frames), not the Prometheus text
exposition format, so — unlike the FastAPI gateway — there is nothing to bolt a
``GET /metrics`` handler onto. In production the exposition endpoint is started
on a SEPARATE admin HTTP port via ``prometheus_client.start_http_server(port)``
in the server bootstrap (see ``server.serve``); Prometheus scrapes that side
port while application traffic keeps flowing over the gRPC port untouched.

CARDINALITY WARNING
-------------------
Every distinct label-value combination is a separate time-series. We label by
the RPC FULL METHOD ("/ecommerce.orders.OrderService/PlaceOrder") and the gRPC
status code NAME ("OK", "NOT_FOUND", ...), both of which are BOUNDED by the
service definition. Never label by request fields (order id, user id, ...) —
that would mint a new series per value and exhaust Prometheus.
"""
from __future__ import annotations

import time

import grpc
from prometheus_client import Counter, Histogram

# Rate + Errors: one counter sliced by the RPC full method and the status code
# name. Error rate is derived at query time, e.g.
#   sum by (method) (rate(grpc_requests_total{code!="OK"}[5m])).
GRPC_REQUEST_COUNT = Counter(
    "grpc_requests_total",
    "Total gRPC requests, labelled by RPC full method and status code.",
    ["method", "code"],
)

# Duration: a histogram yields p50/p95/p99 without shipping every sample. Default
# buckets are tuned for sub-second latencies, which fits these in-process RPCs.
GRPC_REQUEST_LATENCY = Histogram(
    "grpc_request_duration_seconds",
    "gRPC request latency in seconds, labelled by RPC full method.",
    ["method"],
)


class MetricsInterceptor(grpc.aio.ServerInterceptor):
    """Records the RED metrics for every unary-unary RPC.

    All of this system's RPCs are unary-unary, so we only wrap that handler kind
    (mirroring the ``CorrelationInterceptor``). We time the call and, in a
    ``finally``, read ``context.code()`` — which ``abort()``/``set_code`` have
    already populated by the time control returns here — so successes AND aborts
    are recorded with the right status. ``None`` means the handler returned
    normally, i.e. OK.
    """

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None or not handler.unary_unary:
            return handler

        inner = handler.unary_unary
        method = handler_call_details.method

        async def wrapper(request, context):
            start = time.perf_counter()
            try:
                return await inner(request, context)
            finally:
                elapsed = time.perf_counter() - start
                # abort()/set_code record the status on the context before
                # control reaches here; None => the handler returned OK.
                code = context.code() or grpc.StatusCode.OK
                GRPC_REQUEST_LATENCY.labels(method).observe(elapsed)
                GRPC_REQUEST_COUNT.labels(method, code.name).inc()

        return grpc.unary_unary_rpc_method_handler(
            wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
