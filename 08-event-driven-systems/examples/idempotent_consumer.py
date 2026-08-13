"""
08 — Event-Driven Deep Dive: In-Memory Broker, At-Least-Once & Idempotency
==========================================================================

Runnable companion to PDF Chapter "8+ — Event-Driven Architecture & Kafka".

Simulates the Kafka delivery model WITHOUT a real broker so it runs anywhere:
  * a partitioned, RETAINED log (events aren't deleted on consume)
  * offsets, consumer position, replay
  * AT-LEAST-ONCE delivery (duplicates on retry)
  * an IDEMPOTENT consumer (dedupe on event_id) -> exactly-once EFFECT
  * a dead-letter queue for poison messages

Run:  python idempotent_consumer.py
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Event:
    type: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class Partition:
    """An append-only, retained log — like one Kafka partition."""

    def __init__(self) -> None:
        self._log: list[Event] = []

    def append(self, event: Event) -> int:
        self._log.append(event)
        return len(self._log) - 1  # the new offset

    def read_from(self, offset: int) -> list[tuple[int, Event]]:
        return list(enumerate(self._log))[offset:]  # replayable history


class Topic:
    """Routes events to partitions by key so a key's events stay ordered."""

    def __init__(self, partitions: int = 2) -> None:
        self.partitions = [Partition() for _ in range(partitions)]

    def publish(self, key: str, event: Event) -> None:
        idx = hash(key) % len(self.partitions)  # same key -> same partition
        self.partitions[idx].append(event)


class IdempotentConsumer:
    """Process-then-commit + dedupe on event_id = exactly-once effect."""

    def __init__(self, handler: Callable[[Event], None]) -> None:
        self._handler = handler
        self._processed: set[str] = set()   # real world: DB/Redis dedupe store
        self._offsets: dict[int, int] = {}  # committed offset per partition
        self.dead_letters: list[Event] = []
        self.side_effects = 0

    def poll(self, topic: Topic, max_retries: int = 3) -> None:
        for pidx, partition in enumerate(topic.partitions):
            start = self._offsets.get(pidx, 0)
            for offset, event in partition.read_from(start):
                if event.event_id in self._processed:
                    self._offsets[pidx] = offset + 1  # already done; advance
                    continue
                for attempt in range(1, max_retries + 1):
                    try:
                        self._handler(event)
                        self.side_effects += 1
                        self._processed.add(event.event_id)  # mark done
                        break
                    except Exception:  # noqa: BLE001 (demo)
                        if attempt == max_retries:
                            self.dead_letters.append(event)  # poison -> DLQ
                self._offsets[pidx] = offset + 1  # commit AFTER processing


def main() -> None:
    print("=" * 68)
    print("EVENT-DRIVEN — idempotent_consumer.py")
    print("=" * 68)

    charged: list[str] = []

    def charge(event: Event) -> None:
        if event.payload.get("poison"):
            raise ValueError("cannot process poison message")
        charged.append(event.payload["order_id"])

    topic = Topic(partitions=2)
    e1 = Event("OrderPlaced", {"order_id": "A-1"})
    e2 = Event("OrderPlaced", {"order_id": "A-2"})
    poison = Event("OrderPlaced", {"order_id": "A-3", "poison": True})

    topic.publish("A-1", e1)
    topic.publish("A-2", e2)
    topic.publish("A-1", e1)   # DUPLICATE delivery (at-least-once reality)
    topic.publish("A-3", poison)

    consumer = IdempotentConsumer(charge)
    consumer.poll(topic)

    # The duplicate of e1 must NOT double-charge -> exactly-once effect.
    assert charged.count("A-1") == 1, charged
    assert "A-2" in charged
    assert len(consumer.dead_letters) == 1  # poison parked in DLQ
    print("charged (deduped):", charged)
    print("side effects:", consumer.side_effects, "| DLQ size:", len(consumer.dead_letters))

    # Replay is possible because the log is RETAINED, but a fresh consumer
    # with its own dedupe store won't re-run effects it already recorded.
    replay = IdempotentConsumer(charge)
    replay.poll(topic)
    assert charged.count("A-1") == 2  # a NEW consumer group reprocesses history
    print("replay by a new consumer reprocessed history (independent group)")

    print("-" * 68)
    print("All idempotency/at-least-once demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
