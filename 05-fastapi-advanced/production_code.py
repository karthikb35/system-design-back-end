"""
05 — FastAPI Advanced: The Blocking `async` Route vs. Correct Concurrency
========================================================================

THE #1 FastAPI PRODUCTION FOOTGUN: putting a blocking (synchronous) call inside
an `async def` route. FastAPI runs async routes on ONE event loop; a blocking
call freezes that loop, stalling EVERY concurrent request — a self-inflicted
outage that looks fine under single-request testing.

    JUNIOR ANTI-PATTERN  ->  `time.sleep()` / blocking I/O inside `async def`
    SENIOR REFACTOR      ->  await async I/O, OR offload blocking work to a
                            threadpool, OR use a plain `def` route

Run:  python production_code.py     (measures the event-loop stall)
"""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

app = FastAPI(title="FastAPI concurrency: anti-pattern vs refactor")


def _blocking_io(seconds: float = 0.2) -> str:
    # Represents a synchronous library call (old DB driver, `requests`, heavy CPU).
    time.sleep(seconds)
    return "done"


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN
# ===========================================================================
# GOTCHA: `time.sleep()` (or any blocking call) inside `async def` blocks the
#   SINGLE event loop. While this route sleeps, NO other request — not even a
#   trivial /health — can be served. Throughput collapses under concurrency.
#   It "works" in local testing because you only send one request at a time.
@app.get("/junior/report")
async def report_junior() -> dict:
    result = _blocking_io()        # <-- freezes the event loop for everyone
    return {"result": result}


# ===========================================================================
# ✅ SENIOR REFACTOR — three correct options
# ===========================================================================
# OPTION A: keep the route async but OFFLOAD the blocking call to a threadpool,
#   so the event loop stays free to serve other requests while it runs.
@app.get("/senior/report-threadpool")
async def report_threadpool() -> dict:
    result = await run_in_threadpool(_blocking_io)   # doesn't block the loop
    return {"result": result}


# OPTION B: if the work is genuinely async I/O, `await` a native async call.
async def _async_io(seconds: float = 0.2) -> str:
    await asyncio.sleep(seconds)   # non-blocking; yields control to the loop
    return "done"


@app.get("/senior/report-async")
async def report_async() -> dict:
    return {"result": await _async_io()}


# OPTION C: if the whole handler is blocking, define it as a PLAIN `def` route.
#   FastAPI automatically runs `def` routes in its threadpool, so they don't
#   block the loop. (Simplest correct fix for legacy blocking code.)
@app.get("/senior/report-sync")
def report_sync() -> dict:
    return {"result": _blocking_io()}


# A trivial endpoint used to PROVE the loop was (or wasn't) blocked.
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Demo: prove the footgun directly on an event loop (no server needed).
# We run a slow task concurrently with a "health check" task and measure how
# long the health check is DELAYED. Blocking the loop delays it by the full
# sleep; offloading to a thread keeps the loop responsive.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.concurrency import run_in_threadpool

    async def blocking_task() -> None:
        _blocking_io(0.3)               # ❌ blocks the loop for everyone

    async def offloaded_task() -> None:
        await run_in_threadpool(_blocking_io, 0.3)   # ✅ loop stays free

    async def scenario(slow) -> float:
        # A concurrent "health probe" records how long after the shared start
        # the event loop lets it run. If the loop is blocked, it runs late.
        start = time.perf_counter()
        ran_at: dict[str, float] = {}

        async def health_probe() -> None:
            ran_at["ms"] = (time.perf_counter() - start) * 1000

        # slow task is scheduled first; the probe is "ready" immediately.
        await asyncio.gather(slow(), health_probe())
        return ran_at["ms"]

    junior_delay = asyncio.run(scenario(blocking_task))
    senior_delay = asyncio.run(scenario(offloaded_task))
    print(f"health probe ran after JUNIOR (blocking) : {junior_delay:6.1f} ms  <- loop was frozen")
    print(f"health probe ran after SENIOR (threadpool): {senior_delay:6.1f} ms  <- loop stayed free")


if __name__ == "__main__":
    _demo()
