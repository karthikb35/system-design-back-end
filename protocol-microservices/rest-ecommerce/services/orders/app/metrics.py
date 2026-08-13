"""Prometheus metrics — the RED method (Rate, Errors, Duration) over HTTP.

Observability has three complementary pillars; this module adds the second:

- logs    : discrete, high-detail events. We already emit one structured JSON
            line per request with a correlation id (see ``observability.py``).
            Great for "what exactly happened to request X", expensive at scale.
- metrics : cheap, pre-aggregated time-series scraped by Prometheus every few
            seconds (this module). They answer "how is the service doing right
            now" — request Rate, Error rate, and Duration distribution (RED).
- traces  : the causal path of a single request across service boundaries
            (the correlation id is the seed of a trace).

Metrics do NOT replace the logs; they summarise them. A latency histogram tells
you the p99 got worse; the logs (found via the correlation id) tell you why.

CARDINALITY WARNING
-------------------
Every distinct combination of label values creates a separate time-series that
Prometheus must store and scan. We therefore label by the route TEMPLATE
("/orders/{order_id}") and never by the raw path ("/orders/9f3c-..."). Labelling
by raw path — or by user id, request id, etc. — would mint a brand-new series
per value, exhausting memory and slowing every query. Keep label sets small and
BOUNDED (method, template, status class).
"""
from __future__ import annotations

import time

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

# Rate + Errors: one counter, sliced by method, route template and status code.
# Error rate is derived at query time (e.g. sum by status=~"5..").
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests, labelled by method, route template and status code.",
    ["method", "path", "status"],
)

# Duration: a histogram gives you quantiles (p50/p95/p99) without shipping every
# sample. Default buckets are tuned for sub-second web latencies.
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds, labelled by method and route template.",
    ["method", "path"],
)


def _route_template(request: Request) -> str:
    """Return the matched route TEMPLATE, not the raw path.

    Falls back to the raw path only for unmatched requests (404s), which are
    naturally bounded. This keeps label cardinality proportional to the number
    of routes, not the number of distinct ids in the URL.
    """
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if template:
        return template
    for candidate in request.app.routes:
        match, _ = candidate.matches(request.scope)
        if match == Match.FULL:
            return getattr(candidate, "path", request.url.path)
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Records the RED metrics for every HTTP request."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        template = _route_template(request)
        REQUEST_COUNT.labels(request.method, template, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, template).observe(elapsed)
        return response


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus scrape endpoint (exposition format)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
