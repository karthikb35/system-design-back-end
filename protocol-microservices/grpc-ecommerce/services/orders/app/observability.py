"""Observability — a gRPC server interceptor + JSON structured logging.

The Orders service both *receives* RPCs (this interceptor) and *makes* them (see
clients.py). The same ``request_id_ctx`` is read by the clients so the id is
forwarded downstream — one correlation id spans Gateway -> Orders -> Users/Products.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid

import grpc

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

REQUEST_ID_KEY = "x-request-id"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_ctx.get(),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def _metadata_get(metadata, key: str) -> str | None:
    for k, v in metadata or ():
        if k == key:
            return v
    return None


class CorrelationInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, service_name: str) -> None:
        self._log = logging.getLogger(service_name)

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None or not handler.unary_unary:
            return handler

        inner = handler.unary_unary
        method = handler_call_details.method
        log = self._log

        async def wrapper(request, context):
            rid = _metadata_get(handler_call_details.invocation_metadata, REQUEST_ID_KEY) or str(uuid.uuid4())
            token = request_id_ctx.set(rid)
            start = time.perf_counter()
            try:
                return await inner(request, context)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                log.info("%s -> %s in %.1fms", method, context.code() or "OK", elapsed_ms)
                # Under grpc.aio the RPC coroutine can be finalized in a different
                # context than the one that set the token (e.g. when a call is
                # cancelled during server shutdown), which makes reset() raise a
                # ValueError. Guard it so teardown never surfaces a spurious
                # error that pytest would escalate to a failed test.
                try:
                    request_id_ctx.reset(token)
                except ValueError:
                    request_id_ctx.set("-")

        # NOTE: this helper lives on `grpc`, NOT `grpc.aio`.
        return grpc.unary_unary_rpc_method_handler(
            wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
