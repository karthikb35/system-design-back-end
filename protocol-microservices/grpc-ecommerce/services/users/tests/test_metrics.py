"""Metrics interceptor test — RED counters record every RPC (including aborts).

gRPC services have no HTTP ``/metrics`` route, so instead of scraping over HTTP
we drive a couple of RPCs through the same in-process server the other tests use
and read the Prometheus default REGISTRY in-process. This proves the
``MetricsInterceptor`` recorded both a success and a NOT_FOUND abort.
"""
from __future__ import annotations

import asyncio

import grpc
import pytest
from app import metrics
from app.pb import users_pb2


def _count(method_suffix: str, code: str) -> float:
    """Sum ``grpc_requests_total`` samples for an RPC whose full method ends with
    ``method_suffix`` and whose status code label equals ``code``.

    Reading via ``collect()`` keeps the assertion agnostic to the exact sample
    name prometheus_client emits for a ``*_total`` counter, and matching on the
    method suffix avoids hard-coding the proto package in the full method path.
    """
    total = 0.0
    for family in metrics.GRPC_REQUEST_COUNT.collect():
        for sample in family.samples:
            labels = sample.labels
            if (
                sample.name.endswith("_total")
                and labels.get("method", "").endswith(method_suffix)
                and labels.get("code") == code
            ):
                total += sample.value
    return total


async def _await_count(method_suffix: str, code: str, target: float, timeout: float = 2.0) -> float:
    """Poll the counter until it reaches ``target`` (or the timeout elapses).

    The interceptor records each RPC in a ``finally``. For an ABORTED RPC that
    ``finally`` can run a hair AFTER the client already observed the error (the
    abort is transmitted from inside the servicer, before control unwinds back
    through the interceptor), so a bare read immediately after the call would
    race the recording. Polling on the shared in-process event loop closes that
    race deterministically without a fixed sleep. The success path has no race
    (the reply is only sent after the interceptor returns), but we poll it the
    same way for symmetry.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while _count(method_suffix, code) < target and loop.time() < deadline:
        await asyncio.sleep(0.01)
    return _count(method_suffix, code)


async def test_metrics_interceptor_records_success_and_abort(stub):
    before_ok = _count("/CreateUser", "OK")
    before_not_found = _count("/GetUser", "NOT_FOUND")

    # One successful RPC ...
    created = await stub.CreateUser(
        users_pb2.CreateUserRequest(email="metrics@example.com", full_name="M", password="s3cret!")
    )
    assert created.id

    # ... and one that aborts with NOT_FOUND — the interceptor must record the
    # failure code too, not just successes.
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.GetUser(users_pb2.GetUserRequest(id="ghost"))
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND

    assert await _await_count("/CreateUser", "OK", before_ok + 1) == before_ok + 1
    assert await _await_count("/GetUser", "NOT_FOUND", before_not_found + 1) == before_not_found + 1
