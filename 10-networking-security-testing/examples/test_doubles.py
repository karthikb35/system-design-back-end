"""
10 — Testing Deep Dive: The Test Pyramid & Test Doubles
======================================================

Runnable companion to PDF Book VII, Chapter "Testing Strategy".

Shows the ideas behind good tests WITHOUT needing pytest installed — the same
concepts map 1:1 onto pytest fixtures/mocks:
  * a small "system under test" (an OrderService with a payment dependency)
  * UNIT test with a FAKE/STUB dependency (fast, isolated, deterministic)
  * a MOCK that records calls (verify behavior/interactions)
  * INTEGRATION test against a real in-memory collaborator
  * PROPERTY-BASED style test (assert an invariant over many random inputs)
  * a demonstration of a FLAKY test (time/randomness) and how to remove the flake

    JUNIOR ANTI-PATTERN  ->  few slow end-to-end tests hitting real network/DB;
                            flaky, slow, hard to pinpoint failures
    SENIOR REFACTOR      ->  a PYRAMID: many fast unit tests, some integration,
                            few e2e; inject dependencies so they're swappable

Run:  python test_doubles.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol


# ===========================================================================
# SYSTEM UNDER TEST — depends on a PaymentGateway abstraction (injected)
# ===========================================================================
class PaymentGateway(Protocol):
    def charge(self, customer: str, amount: int) -> str: ...


@dataclass
class OrderService:
    gateway: PaymentGateway
    placed: list[dict] = field(default_factory=list)

    def place_order(self, customer: str, amount: int) -> dict:
        if amount <= 0:
            raise ValueError("amount must be positive")
        receipt = self.gateway.charge(customer, amount)   # the collaborator
        order = {"customer": customer, "amount": amount, "receipt": receipt}
        self.placed.append(order)
        return order


# ===========================================================================
# TEST DOUBLES
# ===========================================================================
class StubGateway:
    """STUB/FAKE: returns canned data, no real network — for fast unit tests."""

    def charge(self, customer: str, amount: int) -> str:
        return f"receipt-{customer}-{amount}"


class MockGateway:
    """MOCK: records interactions so a test can VERIFY how it was called."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def charge(self, customer: str, amount: int) -> str:
        self.calls.append((customer, amount))
        return "ok"


class RealInMemoryGateway:
    """A real (if in-memory) collaborator — for an INTEGRATION test."""

    def __init__(self) -> None:
        self.ledger: dict[str, int] = {}

    def charge(self, customer: str, amount: int) -> str:
        self.ledger[customer] = self.ledger.get(customer, 0) + amount
        return f"txn-{len(self.ledger)}"


# ===========================================================================
# THE TESTS (plain asserts == what pytest would run)
# ===========================================================================
def test_unit_with_stub() -> None:
    svc = OrderService(StubGateway())
    order = svc.place_order("alice", 30)
    assert order["receipt"] == "receipt-alice-30"       # deterministic, no I/O
    assert svc.placed == [order]


def test_unit_validation_raises() -> None:
    svc = OrderService(StubGateway())
    try:
        svc.place_order("bob", 0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass                                            # boundary validated


def test_mock_verifies_interaction() -> None:
    mock = MockGateway()
    svc = OrderService(mock)
    svc.place_order("carol", 50)
    assert mock.calls == [("carol", 50)]                # verify BEHAVIOR/calls


def test_integration_with_real_collaborator() -> None:
    gw = RealInMemoryGateway()
    svc = OrderService(gw)
    svc.place_order("dave", 10)
    svc.place_order("dave", 15)
    assert gw.ledger["dave"] == 25                      # state after real interaction


def test_property_invariant() -> None:
    # PROPERTY-BASED style: an invariant must hold for MANY random inputs.
    rng = random.Random(1234)
    svc = OrderService(StubGateway())
    total = 0
    for _ in range(500):
        amount = rng.randint(1, 1000)
        svc.place_order("eve", amount)
        total += amount
    # invariant: sum of recorded orders == sum of charged amounts
    assert sum(o["amount"] for o in svc.placed) == total


def demo_flaky_vs_deterministic() -> None:
    # A FLAKY test depends on real randomness/time; seeding makes it deterministic.
    def flaky() -> bool:
        return random.random() > 0.5                    # passes ~half the time
    def deterministic(seed: int) -> bool:
        return random.Random(seed).random() > 0.5       # same result every run
    r1 = deterministic(42)
    r2 = deterministic(42)
    assert r1 == r2                                      # reproducible -> not flaky
    _ = flaky                                            # referenced for the lesson
    print("flaky source removed by seeding randomness (reproducible tests)")


def run(name, fn) -> None:
    fn()
    print(f"  ✔ {name}")


def main() -> None:
    print("=" * 68)
    print("Test pyramid & test doubles (stub / mock / integration / property)")
    print("=" * 68)
    print("UNIT (fast, isolated):")
    run("test_unit_with_stub", test_unit_with_stub)
    run("test_unit_validation_raises", test_unit_validation_raises)
    run("test_mock_verifies_interaction", test_mock_verifies_interaction)
    print("INTEGRATION (real collaborator):")
    run("test_integration_with_real_collaborator", test_integration_with_real_collaborator)
    print("PROPERTY-BASED (invariant over many inputs):")
    run("test_property_invariant", test_property_invariant)
    print("DETERMINISM:")
    demo_flaky_vs_deterministic()
    print("\nAll testing demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
