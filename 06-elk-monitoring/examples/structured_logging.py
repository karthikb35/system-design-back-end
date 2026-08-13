"""
06 — Observability Deep Dive: Structured Logging, Correlation IDs & RED Metrics
==============================================================================

Runnable companion to PDF Book VI, Chapter "Observability: Logs, Metrics, Traces".

You can't debug what you can't search. Three pillars of observability, in memory:
  * STRUCTURED LOGS  — JSON lines, not f-strings, so ELK/Loki can filter & aggregate
  * CORRELATION ID   — a per-request id carried in a contextvar so every log line
                       of one request is stitchable across services
  * RED METRICS      — Rate, Errors, Duration per endpoint (the golden signals)

    JUNIOR          ->  print(f"user {u} did {x}")  — unsearchable, no request id,
                        secrets leak into logs
    SENIOR          ->  log.info("order.placed", order_id=..., request_id=...) as
                        JSON, secrets redacted, metrics recorded

Run:  python structured_logging.py
"""

from __future__ import annotations

import contextvars
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field

# Correlation id lives in a contextvar: set once per request, read everywhere.
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_REDACT = {"password", "token", "authorization", "secret", "card"}


def _redact(fields: dict) -> dict:
    return {k: ("***" if k.lower() in _REDACT else v) for k, v in fields.items()}


class JsonLogger:
    """Emits structured JSON log lines and keeps them for assertions."""

    def __init__(self) -> None:
        self.lines: list[dict] = []

    def log(self, level: str, event: str, **fields) -> dict:
        record = {
            "ts": round(time.time(), 3),
            "level": level,
            "event": event,
            "request_id": _request_id.get(),
            **_redact(fields),
        }
        self.lines.append(record)
        # In production this goes to stdout for Filebeat/Fluent Bit to ship.
        json.dumps(record)  # prove it is serializable
        return record

    def info(self, event: str, **f) -> dict:
        return self.log("INFO", event, **f)

    def error(self, event: str, **f) -> dict:
        return self.log("ERROR", event, **f)


@dataclass
class RedMetrics:
    """Rate / Errors / Duration per endpoint — the 'RED' method."""

    count: dict = field(default_factory=lambda: defaultdict(int))
    errors: dict = field(default_factory=lambda: defaultdict(int))
    durations: dict = field(default_factory=lambda: defaultdict(list))

    def observe(self, endpoint: str, duration_ms: float, ok: bool) -> None:
        self.count[endpoint] += 1
        if not ok:
            self.errors[endpoint] += 1
        self.durations[endpoint].append(duration_ms)

    def p95(self, endpoint: str) -> float:
        xs = sorted(self.durations[endpoint])
        if not xs:
            return 0.0
        idx = min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))
        return xs[idx]

    def error_rate(self, endpoint: str) -> float:
        n = self.count[endpoint]
        return self.errors[endpoint] / n if n else 0.0


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, ms: float) -> None:
        self.now += ms


def handle_request(log: JsonLogger, metrics: RedMetrics, clock: Clock,
                   *, endpoint: str, request_id: str, work_ms: float,
                   fail: bool = False, password: str = "hunter2") -> None:
    """Simulate one request end-to-end with correlation + metrics."""
    token = _request_id.set(request_id)
    start = clock.now
    try:
        log.info("request.start", endpoint=endpoint, password=password)  # secret redacted
        clock.advance(work_ms)
        if fail:
            raise ValueError("downstream failure")
        log.info("request.end", endpoint=endpoint, status=200)
        metrics.observe(endpoint, clock.now - start, ok=True)
    except ValueError as exc:
        log.error("request.failed", endpoint=endpoint, status=500, reason=str(exc))
        metrics.observe(endpoint, clock.now - start, ok=False)
    finally:
        _request_id.reset(token)


def demo() -> None:
    log, metrics, clock = JsonLogger(), RedMetrics(), Clock()

    handle_request(log, metrics, clock, endpoint="/orders", request_id="req-1", work_ms=40)
    handle_request(log, metrics, clock, endpoint="/orders", request_id="req-2", work_ms=120, fail=True)
    handle_request(log, metrics, clock, endpoint="/orders", request_id="req-3", work_ms=60)

    # Every log line is correlated to its request.
    req1_lines = [r for r in log.lines if r["request_id"] == "req-1"]
    assert len(req1_lines) == 2 and all(r["request_id"] == "req-1" for r in req1_lines)

    # Secrets never hit the logs.
    assert all(r.get("password", "***") == "***" for r in log.lines if "password" in r)
    assert not any("hunter2" in json.dumps(r) for r in log.lines)

    # RED metrics captured rate, errors, and duration.
    assert metrics.count["/orders"] == 3
    assert metrics.errors["/orders"] == 1
    assert abs(metrics.error_rate("/orders") - 1/3) < 1e-9
    assert metrics.p95("/orders") >= 60

    print(f"logged {len(log.lines)} structured lines, all correlated")
    print(f"/orders  rate=3  errors=1  error_rate={metrics.error_rate('/orders'):.0%}  p95={metrics.p95('/orders')}ms")
    print("sample line:", json.dumps(log.lines[1]))


def main() -> None:
    print("=" * 68)
    print("Structured logging + correlation IDs + RED metrics")
    print("=" * 68)
    demo()
    print("\nAll observability demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
