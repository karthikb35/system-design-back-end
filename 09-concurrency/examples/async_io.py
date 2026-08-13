"""
09 — Concurrency: Asyncio (single-threaded concurrency)
=======================================================

Runnable companion to PDF Chapter "9+ — Concurrency & Parallelism".

asyncio runs thousands of tasks on ONE thread using an event loop and
cooperative multitasking: a coroutine runs until it `await`s something (I/O),
then voluntarily yields control so the loop can run another coroutine. No GIL
fight, no locks for CPU (only one thing runs at a time) — but a single
CPU-heavy coroutine that never awaits BLOCKS everything.

Demonstrated with self-checks:
  * awaiting concurrently with asyncio.gather (overlap the waiting)
  * asyncio.Lock to protect an await-spanning critical section
  * an async producer/consumer with asyncio.Queue
  * asyncio.wait_for timeouts
  * the golden rule: never call a blocking function in a coroutine
"""

import asyncio
import time


# --------------------------------------------------------------------------
# gather: schedule many coroutines and await them together. 5 tasks that each
# "wait" 0.1s finish in ~0.1s total, because awaiting yields to the loop.
# --------------------------------------------------------------------------
async def fetch(name: str, delay: float) -> str:
    await asyncio.sleep(delay)     # non-blocking wait -> loop runs other tasks
    return f"{name}:{delay}"


async def gather_demo() -> None:
    start = time.perf_counter()
    results = await asyncio.gather(
        fetch("a", 0.1), fetch("b", 0.1), fetch("c", 0.1),
        fetch("d", 0.1), fetch("e", 0.1),
    )
    elapsed = time.perf_counter() - start
    assert len(results) == 5
    assert elapsed < 0.3, f"expected overlap, got {elapsed:.2f}s"
    print(f"   GATHER: 5×0.1s awaits finished in {elapsed:.2f}s on ONE thread")


# --------------------------------------------------------------------------
# asyncio.Lock: even single-threaded, a critical section that spans an await
# can interleave. The lock serializes it. We assert the counter is exact.
# --------------------------------------------------------------------------
async def async_lock_demo() -> None:
    lock = asyncio.Lock()
    state = {"n": 0}

    async def bump() -> None:
        for _ in range(100):
            async with lock:
                tmp = state["n"]
                await asyncio.sleep(0)   # yield inside the critical section
                state["n"] = tmp + 1

    await asyncio.gather(*(bump() for _ in range(10)))
    assert state["n"] == 1000, state["n"]
    print(f"   ASYNC LOCK: 10 tasks × 100 = {state['n']} (await-spanning section serialized)")


# --------------------------------------------------------------------------
# asyncio.Queue: producer/consumer without threads. Backpressure via maxsize.
# --------------------------------------------------------------------------
async def async_producer_consumer_demo() -> None:
    q: asyncio.Queue = asyncio.Queue(maxsize=5)
    produced = list(range(40))
    consumed: list[int] = []

    async def producer() -> None:
        for item in produced:
            await q.put(item)
        await q.put(None)            # sentinel

    async def consumer() -> None:
        while True:
            item = await q.get()
            if item is None:
                break
            consumed.append(item)

    await asyncio.gather(producer(), consumer())
    assert consumed == produced
    print(f"   ASYNC QUEUE: streamed {len(consumed)} items with backpressure (maxsize=5)")


# --------------------------------------------------------------------------
# wait_for: cap how long we wait, then handle the timeout gracefully.
# --------------------------------------------------------------------------
async def timeout_demo() -> None:
    async def slow() -> str:
        await asyncio.sleep(1.0)
        return "done"

    try:
        await asyncio.wait_for(slow(), timeout=0.05)
        raise AssertionError("should have timed out")
    except asyncio.TimeoutError:
        print("   TIMEOUT: a slow await was cancelled after 0.05s (wait_for)")


# --------------------------------------------------------------------------
# The golden rule: a blocking call freezes the whole loop. If you MUST call
# blocking code, push it to a thread with asyncio.to_thread so the loop keeps
# serving. We prove the loop stays responsive while blocking work runs off-loop.
# --------------------------------------------------------------------------
def blocking_cpu(n: int) -> int:
    total = 0
    for i in range(n):
        total += i
    return total


async def offload_blocking_demo() -> None:
    ticks = {"n": 0}

    async def heartbeat() -> None:
        for _ in range(5):
            await asyncio.sleep(0.01)
            ticks["n"] += 1

    async def work() -> int:
        # Without to_thread this loop would freeze the heartbeat.
        return await asyncio.to_thread(blocking_cpu, 2_000_000)

    _, result = await asyncio.gather(heartbeat(), work())
    assert result == sum(range(2_000_000))
    assert ticks["n"] == 5, "the loop stayed responsive during blocking work"
    print(f"   OFFLOAD: blocking work ran off-loop; heartbeat still ticked {ticks['n']}× "
          "(asyncio.to_thread)")


async def run_all() -> None:
    print("1. gather — overlap awaits on one thread:")
    await gather_demo()
    print("2. asyncio.Lock — protect an await-spanning section:")
    await async_lock_demo()
    print("3. asyncio.Queue — async producer/consumer:")
    await async_producer_consumer_demo()
    print("4. wait_for — timeouts:")
    await timeout_demo()
    print("5. to_thread — never block the loop:")
    await offload_blocking_demo()


def main() -> None:
    print("=" * 68)
    print("CONCURRENCY — async_io.py")
    print("=" * 68)
    asyncio.run(run_all())
    print("-" * 68)
    print("Rule: asyncio = concurrency without threads; never block the loop.")
    print("All async_io demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
