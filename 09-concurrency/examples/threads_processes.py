"""
09 — Concurrency: Threads vs Processes (and the GIL)
====================================================

Runnable companion to PDF Chapter "9+ — Concurrency & Parallelism".

The single most important interview idea here:
  * THREADS share memory, are cheap, and are great for I/O-bound work
    (waiting on network/disk). In CPython the GIL (Global Interpreter Lock)
    lets only ONE thread run Python bytecode at a time, so threads do NOT
    speed up CPU-bound work.
  * PROCESSES each have their own interpreter + memory, so they run Python
    truly in parallel on multiple cores — the right tool for CPU-bound work.
    Cost: no shared memory (data is pickled between them) and higher startup.

Demonstrated with measurable, self-checking demos:
  * a thread pool overlapping simulated I/O (wall-clock << sum of sleeps)
  * why threads can't parallelize CPU work (GIL), and processes can
  * concurrent.futures — the modern, uniform API for both
"""

import math
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


# --------------------------------------------------------------------------
# I/O-BOUND: threads shine. Each task mostly WAITS, releasing the GIL, so
# other threads make progress. Wall-clock time collapses toward the longest
# single task instead of the sum.
# --------------------------------------------------------------------------
def fake_io(seconds: float) -> float:
    time.sleep(seconds)   # time.sleep releases the GIL -> other threads run
    return seconds


def io_bound_with_threads() -> None:
    tasks = [0.2, 0.2, 0.2, 0.2, 0.2]          # 5 tasks × 0.2s = 1.0s if serial
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(fake_io, tasks))
    elapsed = time.perf_counter() - start
    assert sum(results) == 1.0
    # Overlapped: 5 waits run concurrently, so total is ~0.2s, well under 1.0s.
    assert elapsed < 0.6, f"expected overlap, got {elapsed:.2f}s"
    print(f"   I/O-bound: 5×0.2s tasks finished in {elapsed:.2f}s (threads overlap the waiting)")


# --------------------------------------------------------------------------
# CPU-BOUND: pure Python number crunching holds the GIL, so extra threads
# don't help. Processes run on separate cores and cut wall-clock time.
# --------------------------------------------------------------------------
def count_primes(limit: int) -> int:
    def is_prime(n: int) -> bool:
        if n < 2:
            return False
        for d in range(2, int(math.isqrt(n)) + 1):
            if n % d == 0:
                return False
        return True
    return sum(1 for n in range(limit) if is_prime(n))


def cpu_bound_with_processes() -> None:
    chunks = [30_000, 30_000, 30_000, 30_000]
    # Baseline: correct answer computed serially.
    expected = sum(count_primes(c) for c in chunks)

    with ProcessPoolExecutor(max_workers=4) as pool:
        parallel = sum(pool.map(count_primes, chunks))

    assert parallel == expected, f"{parallel} != {expected}"
    print(f"   CPU-bound: {expected:,} primes counted; processes give TRUE parallelism (bypass the GIL)")


def why_threads_dont_help_cpu() -> None:
    # Same CPU work, done with threads: correctness holds, but there is no
    # speedup because the GIL serializes bytecode. We assert only correctness
    # (timings are machine-dependent), and state the lesson.
    chunks = [20_000, 20_000]
    expected = sum(count_primes(c) for c in chunks)
    with ThreadPoolExecutor(max_workers=2) as pool:
        threaded = sum(pool.map(count_primes, chunks))
    assert threaded == expected
    print("   Threads on CPU work: correct, but NOT faster — the GIL lets one run at a time")


def main() -> None:
    print("=" * 68)
    print("CONCURRENCY — threads_processes.py")
    print("=" * 68)
    print("1. Threads for I/O-bound work (overlap the waiting):")
    io_bound_with_threads()
    print("2. Processes for CPU-bound work (real parallelism):")
    cpu_bound_with_processes()
    print("3. Why threads don't speed up CPU work (the GIL):")
    why_threads_dont_help_cpu()
    print("-" * 68)
    print("Rule of thumb: threads for WAITING, processes for COMPUTING.")
    print("All threads_processes demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
