"""Observability — correlation id middleware + JSON logging for the Gateway.

The Gateway is the edge: it mints an ``x-request-id`` if absent, stores it in a
context var, and forwards it as a header on every backend GraphQL call.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "x-request-id"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_ctx.get(),
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def outbound_headers() -> dict[str, str]:
    return {REQUEST_ID_HEADER: request_id_ctx.get()}


class CorrelationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, service_name: str = "gateway") -> None:
        super().__init__(app)
        self._log = logging.getLogger(service_name)

    async def dispatch(self, request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = rid
            self._log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
            return response
        finally:
            request_id_ctx.reset(token)
