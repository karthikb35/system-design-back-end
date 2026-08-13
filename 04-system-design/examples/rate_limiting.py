"""
04 — System Design: Rate Limiting Algorithms
============================================

Runnable companion to PDF Book V "Protecting a service from overload & abuse".

A rate limiter caps how many requests a client may make per unit time. The four
classic algorithms trade smoothness, burst tolerance, and memory:

  * FIXED WINDOW   — count per calendar window (simple; allows 2x burst at edges)
  * SLIDING WINDOW LOG — timestamps in a rolling window (exact; more memory)
  * TOKEN BUCKET   — refill tokens at a steady rate; allows controlled bursts
  * LEAKY BUCKET   — requests drain at a fixed rate (smooths output)

A deterministic fake clock makes the behavior testable without real sleeping.
"""

from __future__ import annotations
from collections import deque


class Clock:
    """Injectable fake time so tests are deterministic (no real sleeping)."""
    def __init__(self, t: float = 0.0):
        self.t = t

    def tick(self, seconds: float) -> None:
        self.t += seconds

    def now(self) -> float:
        return self.t


class FixedWindow:
    def __init__(self, limit: int, window: float, clock: Clock):
        self._limit, self._window, self._clock = limit, window, clock
        self._count = 0
        self._start = clock.now()

    def allow(self) -> bool:
        now = self._clock.now()
        if now - self._start >= self._window:   # new window -> reset
            self._start = now
            self._count = 0
        if self._count < self._limit:
            self._count += 1
            return True
        return False


class SlidingWindowLog:
    def __init__(self, limit: int, window: float, clock: Clock):
        self._limit, self._window, self._clock = limit, window, clock
        self._hits: deque[float] = deque()

    def allow(self) -> bool:
        now = self._clock.now()
        while self._hits and now - self._hits[0] >= self._window:
            self._hits.popleft()                # drop timestamps older than window
        if len(self._hits) < self._limit:
            self._hits.append(now)
            return True
        return False


class TokenBucket:
    def __init__(self, capacity: int, refill_per_sec: float, clock: Clock):
        self._cap = capacity
        self._rate = refill_per_sec
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock.now()

    def allow(self, cost: float = 1.0) -> bool:
        now = self._clock.now()
        self._tokens = min(self._cap, self._tokens + (now - self._last) * self._rate)
        self._last = now
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False


def demo() -> None:
    # Fixed window: 3 per second, 4th denied; resets next window.
    clk = Clock()
    fw = FixedWindow(limit=3, window=1.0, clock=clk)
    assert [fw.allow() for _ in range(4)] == [True, True, True, False]
    clk.tick(1.0)
    assert fw.allow() is True                    # new window
    print("   fixed window: 3 allowed, 4th denied, resets after the window")

    # Sliding window log: rolls continuously, no edge burst.
    clk2 = Clock()
    sw = SlidingWindowLog(limit=2, window=1.0, clock=clk2)
    assert sw.allow() and sw.allow() and not sw.allow()   # 2 then blocked
    clk2.tick(1.01)                              # oldest expires
    assert sw.allow() is True
    print("   sliding window log: exact rolling count; no fixed-window edge burst")

    # Token bucket: burst up to capacity, then throttled to the refill rate.
    clk3 = Clock()
    tb = TokenBucket(capacity=5, refill_per_sec=1.0, clock=clk3)
    assert sum(tb.allow() for _ in range(5)) == 5   # burst of 5
    assert tb.allow() is False                      # bucket empty
    clk3.tick(2.0)                                  # refill 2 tokens
    assert sum(tb.allow() for _ in range(3)) == 2   # only 2 available
    print("   token bucket: allows a burst of 5, then refills at 1/sec")


def main() -> None:
    print("=" * 70)
    print("SYSTEM DESIGN — rate_limiting.py")
    print("=" * 70)
    print("Four algorithms to cap request rate (fake clock = deterministic tests):")
    demo()
    print("-" * 70)
    print("Lesson: token bucket allows controlled bursts; sliding-window is exact; fixed-window is simplest but bursts at edges.")
    print("All rate_limiting demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
