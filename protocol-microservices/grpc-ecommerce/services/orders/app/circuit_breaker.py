"""Circuit breaker — stop hammering a dependency that is already down.

WHY
    Retries alone make a partial outage *worse*. When the Products service is
    hard-down, every checkout still pays the full retry budget (N attempts x
    exponential backoff) before failing, and all of that doomed traffic piles
    onto the very dependency that is already struggling. A circuit breaker gives
    the client a short memory of recent failures so that, once a dependency looks
    dead, we *fail fast* instead of queuing more work against it — protecting both
    our own latency (no pointless waiting) and the downstream (no retry storm).

WHAT
    A tiny three-state machine, one instance per downstream dependency:

        CLOSED     Normal operation. Calls flow through; consecutive failures are
                   counted. Reaching `failure_threshold` trips the breaker OPEN.
        OPEN       Too many recent failures. Calls are rejected immediately
                   (``allow()`` returns False) without touching the network, for
                   `recovery_time` seconds.
        HALF_OPEN  After the cooldown, exactly ONE trial call is admitted. If it
                   succeeds the breaker closes; if it fails it re-opens and the
                   cooldown restarts.

HOW
    Callers ask ``allow()`` before each attempt and then report the outcome with
    ``record_success()`` / ``record_failure()``. Transitions are time-based
    (monotonic clock, immune to wall-clock jumps) and guarded by a lock so that
    concurrent coroutines agree on the state and only one trial probe is let
    through in HALF_OPEN.

    This breaker is intentionally **in-process** (per worker/process). A breaker
    shared across replicas would need a coordination store such as Redis, which
    is out of scope for this reference and is called out as a scaling step in
    ``ADVANCED-PATTERNS.md``.
"""
from __future__ import annotations

import threading
import time
from enum import Enum


class CircuitOpen(Exception):
    """Raised (by callers) when a request is rejected because the breaker is OPEN."""

    def __init__(self, name: str) -> None:
        super().__init__(f"circuit '{name}' is open")
        self.name = name


class _State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """A minimal, thread-safe circuit breaker for a single downstream dependency."""

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_time: float = 30.0,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_time = recovery_time
        self._state = _State.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._trial_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        """Current state as a plain string (``"closed"``/``"open"``/``"half_open"``)."""
        return self._state.value

    def allow(self) -> bool:
        """Return True if a call may proceed.

        CLOSED always allows. OPEN rejects until the cooldown elapses, at which
        point it transitions to HALF_OPEN and admits a single trial call. While a
        trial is in flight, further callers are rejected so exactly one probe
        tests the dependency.
        """
        with self._lock:
            if self._state is _State.CLOSED:
                return True
            if self._state is _State.OPEN:
                if time.monotonic() - self._opened_at >= self._recovery_time:
                    self._state = _State.HALF_OPEN
                    self._trial_in_flight = True
                    return True
                return False
            # HALF_OPEN: admit only if no trial is currently being evaluated.
            if not self._trial_in_flight:
                self._trial_in_flight = True
                return True
            return False

    def record_success(self) -> None:
        """A call succeeded: reset the failure count and close the circuit."""
        with self._lock:
            self._failures = 0
            self._trial_in_flight = False
            self._state = _State.CLOSED

    def record_failure(self) -> None:
        """A call failed: count it and, if warranted, open (or re-open) the circuit."""
        with self._lock:
            if self._state is _State.HALF_OPEN:
                # The trial probe failed — go straight back to OPEN and restart
                # the cooldown before the next probe.
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
                self._trial_in_flight = False
                return
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._state = _State.OPEN
                self._opened_at = time.monotonic()
