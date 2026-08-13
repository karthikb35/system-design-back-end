"""
08 — Event-Driven Deep Dive: Event Sourcing + CQRS
==================================================

Runnable companion to PDF Chapter "8+ — Event-Driven Architecture & Kafka".

Demonstrates the two styles together, in memory:
  * EVENT SOURCING — the event log is the source of truth; current state is a
    projection derived by replaying events (like a bank statement -> balance).
  * CQRS           — the WRITE model appends events; separate READ models are
    projections optimized for queries, updated from the same log.
  * Snapshots      — avoid replaying from zero every time.

Run:  python event_sourcing_cqrs.py
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===========================================================================
# EVENTS (past-tense facts) — the source of truth
# ===========================================================================
@dataclass(frozen=True)
class AccountOpened:
    account_id: str


@dataclass(frozen=True)
class Deposited:
    account_id: str
    amount: int


@dataclass(frozen=True)
class Withdrawn:
    account_id: str
    amount: int


Event = AccountOpened | Deposited | Withdrawn


# ===========================================================================
# WRITE MODEL — validates commands and APPENDS events
# ===========================================================================
class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def stream(self) -> list[Event]:
        return list(self._events)  # replayable log


class AccountWriteModel:
    def __init__(self, store: EventStore) -> None:
        self._store = store

    def open(self, account_id: str) -> None:
        self._store.append(AccountOpened(account_id))

    def deposit(self, account_id: str, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._store.append(Deposited(account_id, amount))

    def withdraw(self, account_id: str, amount: int) -> None:
        if amount > current_balance(self._store, account_id):
            raise ValueError("insufficient funds")  # rule enforced on write side
        self._store.append(Withdrawn(account_id, amount))


# ===========================================================================
# PROJECTIONS (READ MODELS) — derived by folding the event stream
# ===========================================================================
def current_balance(store: EventStore, account_id: str) -> int:
    """Event sourcing: rebuild state by replaying events."""
    balance = 0
    for e in store.stream():
        if isinstance(e, Deposited) and e.account_id == account_id:
            balance += e.amount
        elif isinstance(e, Withdrawn) and e.account_id == account_id:
            balance -= e.amount
    return balance


@dataclass
class TransactionCountView:
    """A DIFFERENT read model over the SAME log (CQRS: many projections)."""

    counts: dict[str, int] = field(default_factory=dict)

    def rebuild(self, store: EventStore) -> TransactionCountView:
        self.counts.clear()
        for e in store.stream():
            if isinstance(e, (Deposited, Withdrawn)):
                self.counts[e.account_id] = self.counts.get(e.account_id, 0) + 1
        return self


@dataclass
class Snapshot:
    """Periodic snapshot so we don't replay from offset 0 forever."""

    balance: int
    upto_offset: int


def balance_from_snapshot(store: EventStore, account_id: str, snap: Snapshot) -> int:
    balance = snap.balance
    for e in store.stream()[snap.upto_offset:]:  # only newer events
        if isinstance(e, Deposited) and e.account_id == account_id:
            balance += e.amount
        elif isinstance(e, Withdrawn) and e.account_id == account_id:
            balance -= e.amount
    return balance


def main() -> None:
    print("=" * 68)
    print("EVENT-DRIVEN — event_sourcing_cqrs.py")
    print("=" * 68)

    store = EventStore()
    write = AccountWriteModel(store)
    write.open("acc-1")
    write.deposit("acc-1", 100)
    write.deposit("acc-1", 50)
    write.withdraw("acc-1", 30)

    # Read model #1: balance is a PROJECTION of the events.
    assert current_balance(store, "acc-1") == 120
    print("event sourcing: balance replayed from log =", current_balance(store, "acc-1"))

    # Write-side rule enforcement.
    try:
        write.withdraw("acc-1", 10_000)
    except ValueError as e:
        assert "insufficient" in str(e)
    print("write model rejected overdraft (rule on the write side)")

    # Read model #2: a different projection over the same log (CQRS).
    view = TransactionCountView().rebuild(store)
    assert view.counts == {"acc-1": 3}
    print("CQRS: separate read model (txn counts) =", view.counts)

    # Snapshot optimization.
    snap = Snapshot(balance=150, upto_offset=3)  # after the two deposits
    assert balance_from_snapshot(store, "acc-1", snap) == 120
    print("snapshot: resumed from offset 3, final balance = 120")

    print("-" * 68)
    print("All event-sourcing/CQRS demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
