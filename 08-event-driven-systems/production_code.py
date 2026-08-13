"""
08 — Event-Driven in FastAPI: Synchronous Chaining vs. Publish-an-Event
======================================================================

SCENARIO: "Place an order." Placing an order should also update inventory, send
a confirmation email, and notify analytics.

    JUNIOR ANTI-PATTERN  ->  the endpoint synchronously CALLS every downstream
                            service inline. Tight coupling: if email is slow or
                            down, order placement is slow or fails. Adding a
                            consumer means editing the endpoint.
    SENIOR REFACTOR      ->  the endpoint does its own work and PUBLISHES an
                            `OrderPlaced` event; independent, idempotent consumers
                            react asynchronously. Decoupled + resilient.

Run:  python production_code.py
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Event-Driven: anti-pattern vs refactor")


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN — synchronous chaining (temporal + logical coupling)
# ===========================================================================
# GOTCHA 1 (coupling): the endpoint KNOWS about every downstream. Adding a new
#   reaction (e.g., fraud check) means editing this tested function.
# GOTCHA 2 (resilience): if `send_email` is slow or down, order placement is slow
#   or FAILS — a non-critical step takes down the critical path.
# GOTCHA 3 (latency): the client waits for ALL downstream work synchronously.
def update_inventory(order_id: str) -> None: ...
def send_email(order_id: str) -> None:
    raise ConnectionError("email provider down")   # simulate an outage
def notify_analytics(order_id: str) -> None: ...


class OrderJunior(BaseModel):
    item: str


@app.post("/junior/orders")
def place_order_junior(body: OrderJunior) -> dict:
    order_id = f"ord-{uuid.uuid4().hex[:6]}"
    update_inventory(order_id)      # coupled call
    send_email(order_id)            # <-- if this fails, the WHOLE order fails
    notify_analytics(order_id)      # coupled call
    return {"order_id": order_id}


# ===========================================================================
# ✅ SENIOR REFACTOR — publish an event; consumers react independently
# ===========================================================================
@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    payload: dict


class MessageBroker:
    """In-process stand-in for Kafka/RabbitMQ/SQS. At-least-once delivery with a
    dead-letter queue; a failing consumer can't take down the producer."""

    def __init__(self, max_retries: int = 1) -> None:
        self._subs: dict[str, list[Callable[[Event], None]]] = {}
        self._max_retries = max_retries
        self.dead_letter: list[Event] = []

    def subscribe(self, topic: str, handler: Callable[[Event], None]) -> None:
        self._subs.setdefault(topic, []).append(handler)

    def publish(self, topic: str, event: Event) -> None:
        for handler in self._subs.get(topic, []):
            for attempt in range(self._max_retries + 1):
                try:
                    handler(event)
                    break
                except Exception:
                    if attempt == self._max_retries:
                        self.dead_letter.append(event)   # park it, keep serving


broker = MessageBroker()


# --- Idempotent consumers: at-least-once delivery => dedupe on event_id ------
@dataclass
class IdempotentConsumer:
    name: str
    _seen: set[str] = field(default_factory=set)
    handled: list[str] = field(default_factory=list)

    def __call__(self, event: Event) -> None:
        if event.event_id in self._seen:
            return                       # duplicate delivery -> no-op
        self.handled.append(f"{self.name}:{event.payload['order_id']}")
        self._seen.add(event.event_id)


inventory_consumer = IdempotentConsumer("inventory")
analytics_consumer = IdempotentConsumer("analytics")


def _email_consumer(event: Event) -> None:
    raise ConnectionError("email provider down")   # still failing...


broker.subscribe("orders", inventory_consumer)
broker.subscribe("orders", analytics_consumer)
broker.subscribe("orders", _email_consumer)        # ...but it no longer blocks orders


class OrderSenior(BaseModel):
    item: str


@app.post("/senior/orders", status_code=201)
def place_order_senior(body: OrderSenior) -> dict:
    # The endpoint does ONLY its own critical work, then publishes a FACT.
    order_id = f"ord-{uuid.uuid4().hex[:6]}"
    event = Event(event_id=str(uuid.uuid4()), event_type="OrderPlaced",
                  payload={"order_id": order_id, "item": body.item})
    broker.publish("orders", event)     # fire-and-forget to independent consumers
    # Order succeeds even though the email consumer is down (it went to the DLQ).
    return {"order_id": order_id}


# ---------------------------------------------------------------------------
# Demo: the junior endpoint fails when email is down; the senior one succeeds
# and the failure is isolated to a dead-letter queue.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/junior/orders", json={"item": "book"})
    print(f"junior order (email down): HTTP {r.status_code}  <- order FAILED")

    r = client.post("/senior/orders", json={"item": "book"})
    print(f"senior order (email down): HTTP {r.status_code} -> {r.json()}  <- order OK")
    print("  inventory handled:", inventory_consumer.handled)
    print("  analytics handled:", analytics_consumer.handled)
    print("  dead-letter (email) size:", len(broker.dead_letter))

    # Duplicate delivery is safe because consumers are idempotent:
    dup = Event(event_id="dup-1", event_type="OrderPlaced", payload={"order_id": "ord-x"})
    broker.publish("orders", dup)
    broker.publish("orders", dup)   # redelivery
    print("  inventory after duplicate:", inventory_consumer.handled[-1:], "(ran once)")


if __name__ == "__main__":
    _demo()
