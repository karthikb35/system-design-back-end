"""
03 — Design Patterns in FastAPI: if/elif Ladders vs. Strategy + Circuit Breaker
==============================================================================

SCENARIO: A "send notification" endpoint that must support multiple channels
(email, SMS, push) and call a flaky external provider.

    JUNIOR ANTI-PATTERN  ->  a growing if/elif channel ladder + a raw external
                            call with no protection (retries forever, cascades)
    SENIOR REFACTOR      ->  Strategy (channels) + Factory (selection) +
                            Circuit Breaker (resilience around the flaky call)

Run:  python production_code.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Design Patterns: anti-pattern vs refactor")


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN
# ===========================================================================
# GOTCHA 1 (OCP): every new channel edits this tested function's if/elif ladder.
# GOTCHA 2 (resilience): the "external" call has no timeout, no retry policy, and
#   no circuit breaker. When the provider is down, every request blocks/fails,
#   threads pile up, and the failure CASCADES to the whole service.
# GOTCHA 3 (testability): the channel logic and the network call are welded into
#   the route, so you can't unit-test routing without hitting the network.
class NotifyJunior(BaseModel):
    channel: str
    to: str
    message: str


def _flaky_external_send(to: str, message: str) -> str:
    # Simulates a provider that is currently failing.
    raise ConnectionError("provider unavailable")


@app.post("/junior/notify")
def notify_junior(body: NotifyJunior) -> dict:
    if body.channel == "email":
        return {"sent": f"email->{body.to}"}
    elif body.channel == "sms":
        # no protection around the flaky call — fails hard every time
        return {"sent": _flaky_external_send(body.to, body.message)}
    elif body.channel == "push":
        return {"sent": f"push->{body.to}"}
    else:
        raise HTTPException(400, "unknown channel")


# ===========================================================================
# ✅ SENIOR REFACTOR — Strategy + Factory + Circuit Breaker
# ===========================================================================

# --- STRATEGY: each channel is an interchangeable implementation ------------
class NotificationChannel(Protocol):
    def send(self, to: str, message: str) -> str: ...


class EmailChannel:
    def send(self, to: str, message: str) -> str:
        return f"email->{to}"


class PushChannel:
    def send(self, to: str, message: str) -> str:
        return f"push->{to}"


# --- CIRCUIT BREAKER: protect the service from a sick dependency ------------
class BreakerState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    reset_timeout: float = 30.0
    _state: BreakerState = field(default=BreakerState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)

    def call(self, fn, *args):
        if self._state is BreakerState.OPEN:
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = BreakerState.HALF_OPEN
            else:
                # Fail FAST instead of hanging on a dead provider (503).
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                    "notification provider unavailable (circuit open)")
        try:
            result = fn(*args)
        except Exception:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = BreakerState.OPEN
                self._opened_at = time.monotonic()
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "provider error")
        self._failures = 0
        self._state = BreakerState.CLOSED
        return result


_SMS_BREAKER = CircuitBreaker(failure_threshold=2, reset_timeout=30)


class SmsChannel:
    """Wraps the flaky provider call in the circuit breaker."""

    def send(self, to: str, message: str) -> str:
        return _SMS_BREAKER.call(_flaky_external_send, to, message)


# --- FACTORY: one place that maps a channel name to a strategy --------------
_CHANNELS: dict[str, NotificationChannel] = {
    "email": EmailChannel(),
    "sms": SmsChannel(),
    "push": PushChannel(),
}


def channel_factory(name: str) -> NotificationChannel:
    channel = _CHANNELS.get(name)
    if channel is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown channel")
    return channel


class NotifySenior(BaseModel):
    channel: str
    to: str
    message: str


@app.post("/senior/notify")
def notify_senior(body: NotifySenior) -> dict:
    # The route no longer branches on channel or touches the network directly.
    channel = channel_factory(body.channel)
    return {"sent": channel.send(body.to, body.message)}


# ---------------------------------------------------------------------------
# Demo: the breaker trips and starts failing fast instead of cascading.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    print("email (both fine):", client.post("/senior/notify",
          json={"channel": "email", "to": "a@b.com", "message": "hi"}).json())

    for i in range(4):
        r = client.post("/senior/notify",
                        json={"channel": "sms", "to": "+1", "message": "hi"})
        print(f"sms attempt {i + 1}: HTTP {r.status_code} -> {r.json().get('detail')}")


if __name__ == "__main__":
    _demo()
