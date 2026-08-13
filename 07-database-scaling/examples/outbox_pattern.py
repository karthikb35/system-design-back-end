"""
07 — Database Scaling Deep Dive: The Transactional Outbox Pattern
================================================================

Runnable companion to PDF Book VI, Chapter "Reliable Writes & Events".

THE DUAL-WRITE PROBLEM: an endpoint saves an order to the DB, then publishes an
`OrderPlaced` event to Kafka. If the process crashes BETWEEN the two, you get an
order with no event (or an event with no order) — permanent inconsistency. You
cannot wrap a database and a message broker in one atomic transaction.

    JUNIOR          ->  db.save(order); broker.publish(event)   # two systems,
                        no atomicity -> lost or phantom events on crash
    SENIOR          ->  TRANSACTIONAL OUTBOX: write the order AND an outbox row
                        in ONE db transaction; a relay reads the outbox and
                        publishes, marking rows sent (at-least-once).

Run:  python outbox_pattern.py
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OutboxRow:
    id: int
    event_type: str
    payload: dict
    sent: bool = False


class Database:
    """A fake DB whose commit is atomic: order + outbox row land together."""

    def __init__(self) -> None:
        self.orders: dict[str, dict] = {}
        self.outbox: list[OutboxRow] = []
        self._next = 1

    def save_order_with_event(self, order: dict, event_type: str, fail_after_order: bool = False) -> None:
        """One atomic transaction: either BOTH the order and outbox row, or NEITHER."""
        staged_order = dict(order)
        staged_row = OutboxRow(self._next, event_type, dict(order))
        if fail_after_order:
            # Simulate a crash mid-transaction -> nothing is committed (rollback).
            raise RuntimeError("crash before commit")
        # commit
        self.orders[staged_order["id"]] = staged_order
        self.outbox.append(staged_row)
        self._next += 1


class Broker:
    def __init__(self) -> None:
        self.published: list[dict] = []

    def publish(self, event_type: str, payload: dict) -> None:
        self.published.append({"type": event_type, "payload": payload})


class OutboxRelay:
    """Polls unsent outbox rows and publishes them (at-least-once)."""

    def __init__(self, db: Database, broker: Broker) -> None:
        self.db = db
        self.broker = broker

    def poll_once(self) -> int:
        sent = 0
        for row in self.db.outbox:
            if not row.sent:
                self.broker.publish(row.event_type, row.payload)
                row.sent = True         # marked AFTER publish -> at-least-once
                sent += 1
        return sent


def demo_atomicity() -> None:
    db = Database()

    # Crash mid-transaction: neither the order nor the event survives.
    try:
        db.save_order_with_event({"id": "o1", "total": 10}, "OrderPlaced", fail_after_order=True)
    except RuntimeError:
        pass
    assert "o1" not in db.orders
    assert db.outbox == []
    print("crash before commit: no order AND no event (consistent)")

    # Successful transaction: order + outbox row committed together.
    db.save_order_with_event({"id": "o2", "total": 20}, "OrderPlaced")
    assert "o2" in db.orders
    assert len(db.outbox) == 1 and db.outbox[0].sent is False
    print("commit: order + outbox row persisted atomically")


def demo_relay() -> None:
    db, broker = Database(), Broker()
    db.save_order_with_event({"id": "o3", "total": 30}, "OrderPlaced")
    db.save_order_with_event({"id": "o4", "total": 40}, "OrderPlaced")
    relay = OutboxRelay(db, broker)

    # First poll publishes both pending events.
    assert relay.poll_once() == 2
    assert len(broker.published) == 2
    assert all(r.sent for r in db.outbox)

    # Second poll publishes nothing (already sent) — no duplicates on steady state.
    assert relay.poll_once() == 0
    assert len(broker.published) == 2
    print("relay published 2 events, then nothing new on re-poll")

    # A relay crash after publish but before marking would re-send -> consumers
    # must be idempotent (see 08-event-driven-systems/examples/idempotent_consumer.py).
    print("at-least-once: consumers must dedupe by event id")


def main() -> None:
    print("=" * 68)
    print("Transactional outbox: no lost or phantom events")
    print("=" * 68)
    demo_atomicity()
    print()
    demo_relay()
    print("\nAll outbox demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
