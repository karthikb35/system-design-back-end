"""
08 — Event-Driven Deep Dive: Saga with Compensating Actions
===========================================================

Runnable companion to PDF Chapter "8+ — Event-Driven Architecture & Kafka"
(and Chapter 8 Sagas).

A saga replaces a distributed transaction: a sequence of local steps where, if
a later step fails, earlier steps are UNDONE by compensating actions (in
reverse order). This is an ORCHESTRATION-style saga.

  order -> payment -> shipping
  if shipping fails  -> refund payment -> release order   (compensations)

Run:  python saga.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Step:
    name: str
    action: Callable[[], None]
    compensation: Callable[[], None]


class Saga:
    def __init__(self) -> None:
        self._steps: list[Step] = []

    def add(self, step: Step) -> "Saga":
        self._steps.append(step)
        return self

    def execute(self) -> tuple[bool, list[str]]:
        """Run steps in order; on failure, compensate completed steps in reverse."""
        done: list[Step] = []
        trail: list[str] = []
        try:
            for step in self._steps:
                step.action()
                done.append(step)
                trail.append(f"did:{step.name}")
            return True, trail
        except Exception as exc:  # noqa: BLE001 (demo)
            trail.append(f"FAILED:{done[-1].name if done else '?'}:{exc}")
            for step in reversed(done):        # unwind in reverse order
                step.compensation()
                trail.append(f"compensated:{step.name}")
            return False, trail


@dataclass
class OrderSystem:
    """Tracks side effects so we can assert the saga's behavior."""

    order_active: bool = False
    payment_charged: bool = False
    shipped: bool = False
    fail_shipping: bool = False
    log: list[str] = field(default_factory=list)

    def build_saga(self) -> Saga:
        def place_order() -> None:
            self.order_active = True

        def release_order() -> None:
            self.order_active = False

        def charge_payment() -> None:
            self.payment_charged = True

        def refund_payment() -> None:
            self.payment_charged = False

        def ship() -> None:
            if self.fail_shipping:
                raise RuntimeError("carrier unavailable")
            self.shipped = True

        def cancel_shipment() -> None:
            self.shipped = False

        return (
            Saga()
            .add(Step("order", place_order, release_order))
            .add(Step("payment", charge_payment, refund_payment))
            .add(Step("shipping", ship, cancel_shipment))
        )


def main() -> None:
    print("=" * 68)
    print("EVENT-DRIVEN — saga.py")
    print("=" * 68)

    # Happy path — everything commits.
    ok_sys = OrderSystem()
    ok, trail = ok_sys.build_saga().execute()
    assert ok and ok_sys.order_active and ok_sys.payment_charged and ok_sys.shipped
    print("happy path:", " -> ".join(trail))

    # Failure path — shipping fails, earlier steps are compensated.
    bad_sys = OrderSystem(fail_shipping=True)
    ok, trail = bad_sys.build_saga().execute()
    assert not ok
    assert not bad_sys.shipped            # never shipped
    assert not bad_sys.payment_charged    # refunded
    assert not bad_sys.order_active       # released
    print("failure path:", " -> ".join(trail))
    print("after compensation -> order:", bad_sys.order_active,
          "payment:", bad_sys.payment_charged, "shipped:", bad_sys.shipped)

    print("-" * 68)
    print("All saga demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
