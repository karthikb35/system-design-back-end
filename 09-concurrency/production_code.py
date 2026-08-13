"""
09 — Concurrency: A Correctness-First Bounded Job Runner
========================================================

Runnable, review-grade reference for the concurrency primitives you are most
likely to reach for in a backend service — and the ones most likely to bite you.
Everything here is ONE coherent module: a small "job runner" that we build up
five ways, each isolating a single lesson and each verified with `assert`.

    JUNIOR MISCONCEPTION  ->  "I added threads, so my code is faster, and the GIL
                              protects me so I don't need locks."
    REALITY               ->  Threads overlap WAITING (I/O), not COMPUTING (the GIL
                              serializes Python bytecode). And the GIL protects the
                              interpreter's own internals — NOT your `counter += 1`,
                              which is a read-modify-write and still races.

What we demonstrate (each with a self-check):
  1. a thread-safe counter with a Lock — and the lost-update race WITHOUT it
  2. a Semaphore bounding concurrency, exactly like a fixed-size connection pool
  3. a producer/consumer job runner built on queue.Queue (no manual locks)
  4. an asyncio version doing concurrent I/O with asyncio.gather + a deadline
     enforced by asyncio.wait_for
  5. why CPU-bound work needs PROCESSES, not threads (the GIL), via ProcessPool

Standard library only. Run:  python production_code.py
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager


# ===========================================================================
# 1. THE RACE, AND THE LOCK THAT FIXES IT
# ===========================================================================
# `total["n"] += 1` (or the read/modify/write we spell out below) is NOT atomic:
# it READS the value, ADDS one, then WRITES it back. If a second thread reads the
# same value before the first writes, one increment is silently lost. We insert
# an explicit yield point (time.sleep(0)) to make the interleaving reliable so the
# lesson is visible on every run rather than only under load in production.
def _count_up(use_lock: bool, per_thread: int = 500, n_threads: int = 8) -> int:
    total = {"n": 0}
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(per_thread):
            if use_lock:
                with lock:                 # critical section is now atomic
                    tmp = total["n"]
                    time.sleep(0)          # yield the GIL mid-section
                    total["n"] = tmp + 1
            else:
                tmp = total["n"]           # READ
                time.sleep(0)              # yield -> another thread can clobber us
                total["n"] = tmp + 1       # WRITE (may overwrite a lost update)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return total["n"]


def demo_lock_vs_race() -> None:
    expected = 500 * 8
    racy = _count_up(use_lock=False)
    safe = _count_up(use_lock=True)

    # The unsynchronized version loses updates: it can only ever UNDER-count.
    assert racy <= expected, f"a race cannot over-count: {racy} > {expected}"
    # The locked version is exact, every time.
    assert safe == expected, f"lock must be exact: {safe} != {expected}"
    print(f"   RACE: unsynchronized counter reached {racy}/{expected} (lost updates)")
    print(f"   LOCK: same work under a Lock reached {safe}/{expected} (exact)")


# ===========================================================================
# 2. SEMAPHORE — BOUND CONCURRENCY LIKE A CONNECTION POOL
# ===========================================================================
# A Lock admits ONE holder; a Semaphore admits up to N. That is exactly what a
# connection pool is: "at most `size` callers may hold a connection at once; the
# rest block until one is returned." We expose it as a context manager so callers
# cannot forget to release a permit (the finally block always runs).
class BoundedResourcePool:
    """A fixed-size pool: at most `size` acquisitions may be live simultaneously."""

    def __init__(self, size: int) -> None:
        self._sem = threading.Semaphore(size)
        self._size = size
        self._guard = threading.Lock()     # protects the observability counters
        self._live = 0
        self._peak = 0

    @contextmanager
    def acquire(self) -> Iterator[None]:
        self._sem.acquire()                # blocks here once `size` permits are out
        with self._guard:
            self._live += 1
            self._peak = max(self._peak, self._live)
        try:
            yield
        finally:
            with self._guard:
                self._live -= 1
            self._sem.release()            # ALWAYS return the permit

    @property
    def peak_concurrency(self) -> int:
        return self._peak


def demo_semaphore_pool() -> None:
    pool = BoundedResourcePool(size=3)

    def use_resource() -> None:
        with pool.acquire():
            time.sleep(0.01)               # pretend to use a scarce connection

    threads = [threading.Thread(target=use_resource) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 20 threads competed, but the semaphore guaranteed the invariant.
    assert pool.peak_concurrency <= 3, f"pool leaked: peak {pool.peak_concurrency} > 3"
    print(f"   SEMAPHORE: 20 workers, at most {pool.peak_concurrency} held a permit at once (cap = 3)")


# ===========================================================================
# 3. QUEUE — THE PREFERRED WAY TO SHARE WORK BETWEEN THREADS
# ===========================================================================
# queue.Queue is internally synchronized, so a producer/consumer handoff needs
# NO manual locks around the shared work list — the queue IS the synchronization.
# The idiom: put one sentinel (None) per worker so every worker gets a clean stop
# signal and none blocks forever on an empty queue.
def run_job_queue(jobs: list[int], n_workers: int = 4) -> dict[int, int]:
    q: queue.Queue[int | None] = queue.Queue()
    results: dict[int, int] = {}
    guard = threading.Lock()               # only the results dict needs guarding

    def worker() -> None:
        while True:
            job = q.get()
            try:
                if job is None:            # sentinel -> this worker is done
                    return
                squared = job * job        # the "work"
                with guard:
                    results[job] = squared
            finally:
                q.task_done()

    workers = [threading.Thread(target=worker) for _ in range(n_workers)]
    for w in workers:
        w.start()
    for job in jobs:
        q.put(job)
    for _ in workers:
        q.put(None)                        # one sentinel per worker
    q.join()                               # wait until every item is processed
    for w in workers:
        w.join()
    return results


def demo_job_queue() -> None:
    jobs = list(range(1, 101))
    results = run_job_queue(jobs, n_workers=4)

    assert set(results) == set(jobs), "every job must be processed exactly once"
    assert all(results[j] == j * j for j in jobs), "each result must be correct"
    print(f"   QUEUE: 4 workers processed {len(results)} jobs safely (no manual work-list lock)")


# ===========================================================================
# 4. ASYNCIO — CONCURRENT I/O ON ONE THREAD, WITH A DEADLINE
# ===========================================================================
# For I/O-bound fan-out (call N services, read N files), asyncio overlaps the
# WAITING on a single thread: each coroutine runs until it `await`s, then yields.
# asyncio.gather schedules them together; asyncio.wait_for wraps any awaitable in
# a deadline and cancels it on timeout — the async equivalent of a socket timeout.
async def _fetch(job: int, delay: float) -> tuple[int, int]:
    await asyncio.sleep(delay)             # non-blocking wait -> loop runs others
    return job, job * job


async def _slow_call() -> str:
    await asyncio.sleep(1.0)               # a dependency that is too slow
    return "never returned in time"


async def demo_async() -> None:
    jobs = list(range(1, 21))
    start = time.perf_counter()
    pairs = await asyncio.gather(*(_fetch(j, 0.05) for j in jobs))
    elapsed = time.perf_counter() - start
    results = dict(pairs)

    assert set(results) == set(jobs)
    assert all(results[j] == j * j for j in jobs)
    # 20 sequential 0.05s waits would be 1.0s; overlapped they finish near 0.05s.
    assert elapsed < 0.5, f"expected overlap, got {elapsed:.2f}s"
    print(f"   ASYNC GATHER: {len(results)} concurrent I/O jobs finished in {elapsed:.2f}s on one thread")

    # A deadline turns "hangs forever" into a handled, bounded failure.
    timed_out = False
    try:
        await asyncio.wait_for(_slow_call(), timeout=0.05)
    except TimeoutError:
        timed_out = True
    assert timed_out, "wait_for must cancel a call that overruns its deadline"
    print("   ASYNC DEADLINE: a 1.0s call was cancelled after 0.05s (asyncio.wait_for)")


# ===========================================================================
# 5. CPU-BOUND WORK NEEDS PROCESSES (THE GIL)
# ===========================================================================
# Threads share one interpreter and one GIL, so pure-Python number crunching does
# NOT parallelize across threads. Processes each have their own interpreter, so
# they run on separate cores in true parallel — at the cost of pickling data
# across the process boundary and higher startup. The worker MUST be a top-level,
# importable function so it is picklable under Windows' 'spawn' start method.
def _cpu_sum_of_squares(n: int) -> int:
    total = 0
    for i in range(n):
        total += i * i
    return total


def demo_cpu_processes() -> None:
    chunks = [200_000, 200_000, 200_000, 200_000]
    expected = sum(_cpu_sum_of_squares(c) for c in chunks)   # serial baseline

    with ProcessPoolExecutor(max_workers=4) as pool:
        parallel = sum(pool.map(_cpu_sum_of_squares, chunks))

    # Correctness is the same; the win is wall-clock time on multi-core hardware.
    assert parallel == expected, f"{parallel} != {expected}"
    print(f"   PROCESSES: 4 CPU-bound chunks computed in parallel; result matches serial ({expected:,})")


def main() -> None:
    print("=" * 68)
    print("CONCURRENCY — production_code.py  (a correctness-first job runner)")
    print("=" * 68)
    print("1. Shared counter — the race, and the Lock that fixes it:")
    demo_lock_vs_race()
    print("2. Semaphore — bound concurrency like a connection pool:")
    demo_semaphore_pool()
    print("3. queue.Queue — thread-safe producer/consumer job runner:")
    demo_job_queue()
    print("4. asyncio — concurrent I/O with gather + a deadline via wait_for:")
    asyncio.run(demo_async())
    print("5. CPU-bound — threads can't parallelize it, processes can (the GIL):")
    demo_cpu_processes()
    print("-" * 68)
    print("Rule: threads/async overlap WAITING; processes parallelize COMPUTING;")
    print("      share work through a queue, or guard shared state with a lock.")
    print("All production_code checks passed.")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
