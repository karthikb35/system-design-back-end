"""Reverse-proxy helper — forwards a request to a downstream service.

The gateway's job is to be the single public door: it forwards `/api/users/*` to
the Users service, `/api/products/*` to Products, `/api/orders/*` to Orders. This
module centralises the forwarding, timeout, retry, and header propagation so the
routers stay tiny.
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import Response

from .config import get_settings
from .observability import REQUEST_ID_HEADER, request_id_ctx

log = logging.getLogger("gateway.proxy")

# Hop-by-hop headers that must not be forwarded verbatim.
_SKIP_REQUEST_HEADERS = {"host", "content-length", "connection"}


async def forward(method: str, base_url: str, path: str, *, body: bytes | None = None) -> Response:
    """Forward one request to `base_url + path` and return the response.

    Retries transient failures (network errors / 5xx) with exponential backoff.
    """
    settings = get_settings()
    url = f"{base_url}{path}"
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    headers = {REQUEST_ID_HEADER: request_id_ctx.get(), "content-type": "application/json"}
    last_exc: Exception | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, settings.http_max_retries + 1):
            try:
                upstream = await client.request(method, url, content=body, headers=headers)
            except httpx.HTTPError as exc:
                last_exc = exc
            else:
                if upstream.status_code < 500:
                    return Response(
                        content=upstream.content,
                        status_code=upstream.status_code,
                        media_type=upstream.headers.get("content-type"),
                    )
                last_exc = RuntimeError(f"{url} -> {upstream.status_code}")

            if attempt < settings.http_max_retries:
                delay = 0.1 * (2 ** (attempt - 1))
                log.warning("retry %d for %s in %.2fs", attempt, url, delay)
                await asyncio.sleep(delay)

    log.error("gateway could not reach %s: %s", url, last_exc)
    return Response(
        content=b'{"detail":"upstream service unavailable"}',
        status_code=502,
        media_type="application/json",
    )
