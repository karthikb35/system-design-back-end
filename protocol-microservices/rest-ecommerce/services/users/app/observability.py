"""Observability — a correlation-ID middleware + JSON structured logging.

Every request gets an `X-Request-ID` (reused if the caller already sent one, so
the id propagates across services). The id is stored in a contextvar and added
to every log line, making a single request traceable across the whole system.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"


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


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns/propagates a request id and logs one line per request."""

    def __init__(self, app, service_name: str) -> None:
        super().__init__(app)
        self._log = logging.getLogger(service_name)

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._log.info(
                "%s %s -> handled in %.1fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = rid
        return response
