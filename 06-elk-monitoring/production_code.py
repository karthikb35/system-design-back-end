"""
06 — ELK / Observability in FastAPI: print()-Debugging vs. Structured Logging
============================================================================

SCENARIO: You need to debug a failing request in production across an ELK stack.

    JUNIOR ANTI-PATTERN  ->  f-string / print logging, no correlation ID, secrets
                            leaked into logs; unsearchable and un-aggregatable
    SENIOR REFACTOR      ->  structured JSON logs + a correlation-ID middleware
                            (contextvar) so one request is traceable across lines

Run:  python production_code.py
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

app = FastAPI(title="ELK: anti-pattern vs refactor")


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN
# ===========================================================================
# GOTCHA 1: free-text logs are unsearchable/un-aggregatable in Elasticsearch —
#   you cannot query `status:500 AND latency_ms:>1000`.
# GOTCHA 2: no correlation ID, so you can't stitch together the lines belonging
#   to ONE request among thousands interleaved from concurrent traffic.
# GOTCHA 3: it logs the password — logs are widely readable and long-lived; this
#   is a serious security incident waiting to happen.
@app.post("/junior/login")
def login_junior(username: str, password: str) -> dict:
    print(f"User {username} logging in with password {password}")   # DON'T
    print("login handled")                                          # unstructured
    return {"ok": True}


# ===========================================================================
# ✅ SENIOR REFACTOR — structured JSON logs + correlation IDs
# ===========================================================================
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line — exactly what Beats/Logstash ingest and what
    Elasticsearch indexes into queryable fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": _correlation_id.get(),
        }
        if isinstance(getattr(record, "context", None), dict):
            payload.update(record.context)     # merge structured extra fields
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)   # 12-factor: log to stdout
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


log = _build_logger()


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    # Accept an inbound X-Request-ID (from an upstream/gateway) or mint one, then
    # stamp it on every log line for this request via the contextvar.
    cid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    _correlation_id.set(cid)
    start = time.monotonic()
    log.info("request.start", extra={"context": {"path": request.url.path}})
    response = await call_next(request)
    latency = round((time.monotonic() - start) * 1000, 2)
    # Consistent field names => dashboards can aggregate latency/status.
    log.info("request.end", extra={"context": {
        "path": request.url.path, "status": response.status_code, "latency_ms": latency}})
    response.headers["X-Request-ID"] = cid    # return it so clients can correlate
    return response


@app.post("/senior/login")
def login_senior(username: str) -> dict:
    # NEVER log the password. Log a structured business event instead.
    log.info("user.login", extra={"context": {"username": username, "outcome": "success"}})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Demo: two requests; note every senior line shares one correlation_id and is
# valid JSON ready for Elasticsearch.
# ---------------------------------------------------------------------------
def _demo() -> None:
    client = TestClient(app)
    print("---- JUNIOR (unstructured, leaks password) ----")
    client.post("/junior/login", params={"username": "ada", "password": "hunter2"})
    print("---- SENIOR (structured JSON, correlated, no secrets) ----")
    r = client.post("/senior/login", params={"username": "ada"},
                    headers={"X-Request-ID": "trace-42"})
    print("response X-Request-ID header ->", r.headers.get("X-Request-ID"))


if __name__ == "__main__":
    _demo()
