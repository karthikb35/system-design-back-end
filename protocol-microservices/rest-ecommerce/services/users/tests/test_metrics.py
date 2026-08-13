"""Metrics endpoint test — /metrics exposes the Prometheus request counter."""
from __future__ import annotations


async def test_metrics_endpoint_exposes_request_count(client):
    # Drive one request so the RED counter records at least one sample.
    await client.get("/health/live")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    # The request-count metric name must appear in the exposition output.
    assert "http_requests_total" in resp.text
