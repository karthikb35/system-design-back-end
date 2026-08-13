"""
05 — FastAPI Advanced Deep Dive: Retries, Backoff, Jitter & Circuit Breaker
===========================================================================

Runnable companion to PDF Book VI, Chapter "Resilient Service Calls".

Calling another service? It WILL fail sometimes. Two failure modes to avoid:
  * naive immediate retries -> a "retry storm" that DDoSes the struggling
    dependency and turns a blip into an outage
  * retrying a dependency that is fully down -> wasted latency on every call

    JUNIOR          ->  `for _ in range(3): try call`  (no wait, no breaker)
    SENIOR          ->  exponential backoff + jitter, capped attempts, wrapped
                        in a circuit breaker that fails fast when the dep is down

Uses an injectable fake clock so the tests are deterministic (no real sleeping).

Run:  python retry_backoff.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


class Clock:
    """Injectable fake time — advance manually instead of sleeping."""

    def __init__(self) -> None:
        self.now = 0.0

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class TransientError(Exception):
    pass


def backoff_delays(base: float, attempts: int, cap: float, jitter: random.Random) -> list[float]:
    """Exponential backoff with full jitter: delay = rand(0, min(cap, base*2^i))."""
    delays: list[float] = []
    for i in range(attempts):
        ceiling = min(cap, base * (2 ** i))
        delays.append(jitter.uniform(0, ceiling))
    return delays


def call_with_retry(fn, *, clock: Clock, attempts: int, base: float, cap: float,
                    jitter: random.Random):
    """Retry `fn` up to `attempts` times with exponential backoff + jitter."""
    delays = backoff_delays(base, attempts, cap, jitter)
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except TransientError as exc:
            last = exc
            if i < attempts - 1:
                clock.sleep(delays[i])       # wait longer each time
    raise last  # exhausted retries


# ===========================================================================
# CIRCUIT BREAKER — closed -> open -> half-open
# ===========================================================================
@dataclass
class CircuitBreaker:
    clock: Clock
    fail_threshold: int = 3
    cooldown: float = 5.0
    _failures: int = 0
    _state: str = "closed"
    _opened_at: float = field(default=0.0)

    @property
    def state(self) -> str:
        # Auto-transition open -> half-open once the cooldown elapses.
        if self._state == "open" and self.clock.now - self._opened_at >= self.cooldown:
            self._state = "half-open"
        return self._state

    def call(self, fn):
        state = self.state
        if state == "open":
            raise TransientError("circuit open — failing fast")
        try:
            result = fn()
        except TransientError:
            self._failures += 1
            if self._failures >= self.fail_threshold:
                self._state = "open"
                self._opened_at = self.clock.now
            raise
        # success: half-open probe recovered, or normal closed success
        self._failures = 0
        self._state = "closed"
        return result


def demo_backoff() -> None:
    clock = Clock()
    jitter = random.Random(42)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:          # fails twice, succeeds on the 3rd
            raise TransientError("boom")
        return "ok"

    result = call_with_retry(flaky, clock=clock, attempts=5, base=0.1, cap=2.0, jitter=jitter)
    assert result == "ok"
    assert calls["n"] == 3
    assert clock.now > 0            # we backed off between attempts
    print(f"retry: succeeded on attempt {calls['n']}, total backoff {clock.now:.3f}s")

    # Delays are non-decreasing in ceiling and never exceed the cap.
    d = backoff_delays(0.1, 6, 2.0, random.Random(1))
    assert all(x <= 2.0 for x in d)
    print("backoff delays (capped at 2.0s):", [round(x, 3) for x in d])


def demo_circuit() -> None:
    clock = Clock()
    breaker = CircuitBreaker(clock, fail_threshold=3, cooldown=5.0)

    def dead():
        raise TransientError("dependency down")

    # Three failures trip the breaker open.
    for _ in range(3):
        try:
            breaker.call(dead)
        except TransientError:
            pass
    assert breaker.state == "open"

    # While open, calls fail FAST without touching the dependency.
    touched = {"n": 0}

    def counted_dead():
        touched["n"] += 1
        raise TransientError("down")

    try:
        breaker.call(counted_dead)
    except TransientError:
        pass
    assert touched["n"] == 0        # dependency was NOT called — failed fast
    print("circuit OPEN: dependency spared (fail-fast)")

    # After cooldown -> half-open; a success closes it again.
    clock.sleep(5.0)
    assert breaker.state == "half-open"
    assert breaker.call(lambda: "recovered") == "recovered"
    assert breaker.state == "closed"
    print("circuit recovered: half-open probe succeeded -> closed")


def main() -> None:
    print("=" * 68)
    print("Retries + backoff + jitter, and a circuit breaker")
    print("=" * 68)
    demo_backoff()
    print()
    demo_circuit()
    print("\nAll retry/circuit-breaker demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
