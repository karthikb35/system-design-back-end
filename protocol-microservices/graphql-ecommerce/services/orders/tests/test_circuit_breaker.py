"""Unit tests for the circuit breaker state machine (no network, no event loop)."""
from __future__ import annotations

from app.circuit_breaker import CircuitBreaker


def test_starts_closed_and_allows():
    cb = CircuitBreaker("t", failure_threshold=3, recovery_time=60)
    assert cb.state == "closed"
    assert cb.allow() is True


def test_opens_after_threshold_consecutive_failures():
    cb = CircuitBreaker("t", failure_threshold=3, recovery_time=60)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == "open"
    assert cb.allow() is False  # rejected fast while OPEN (before cooldown)


def test_success_resets_failure_count():
    cb = CircuitBreaker("t", failure_threshold=3, recovery_time=60)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()  # a good call wipes the streak
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "closed"


def test_half_open_trial_closes_on_success():
    # recovery_time=0 => cooldown already elapsed, so the next allow() promotes
    # OPEN -> HALF_OPEN and admits a single trial call.
    cb = CircuitBreaker("t", failure_threshold=1, recovery_time=0.0)
    cb.record_failure()
    assert cb.state == "open"
    assert cb.allow() is True
    assert cb.state == "half_open"
    cb.record_success()
    assert cb.state == "closed"


def test_half_open_trial_reopens_on_failure():
    cb = CircuitBreaker("t", failure_threshold=1, recovery_time=0.0)
    cb.record_failure()
    assert cb.allow() is True  # admits the trial probe
    cb.record_failure()  # probe fails
    assert cb.state == "open"
