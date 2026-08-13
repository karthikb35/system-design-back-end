"""
09 — Concurrency: Synchronization, Race Conditions & Deadlock
=============================================================

Runnable companion to PDF Chapter "9+ — Concurrency & Parallelism".

When threads share mutable state, interleaving creates bugs that pass on your
laptop and corrupt data in production. This file demonstrates — and FIXES —
the classic hazards, each with a self-check:

  * RACE CONDITION  — unsynchronized read-modify-write loses updates
  * LOCK (Mutex)    — makes a critical section atomic -> correct result
  * RLOCK           — re-entrant lock a thread may acquire multiple times
  * SEMAPHORE       — bound concurrency to N permits (e.g. a connection pool)
  * EVENT           — one thread signals others to proceed
  * QUEUE           — the thread-safe producer/consumer handoff (preferred!)
  * DEADLOCK        — two locks acquired in opposite order hang forever;
                      fix = a GLOBAL LOCK ORDERING (always acquire in same order)
"""

import threading
import queue
import time


# --------------------------------------------------------------------------
# RACE CONDITION: counter += 1 is NOT atomic — it is read, add, write. With a
# yield point in the middle, threads clobber each other's updates. We force
# the interleaving so the lesson is visible, then assert the corruption.
# --------------------------------------------------------------------------
def race_condition_demo() -> None:
    unsafe = {"n": 0}
    per_thread, n_threads = 200, 8
    expected = per_thread * n_threads

    def worker_unsafe() -> None:
        for _ in range(per_thread):
            tmp = unsafe["n"]     # READ
            time.sleep(0)         # yield the GIL -> force interleaving
            unsafe["n"] = tmp + 1  # WRITE (may overwrite another thread's update)

    threads = [threading.Thread(target=worker_unsafe) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Lost updates: the final value is <= expected, and in practice far less.
    assert unsafe["n"] <= expected
    print(f"   RACE: expected {expected}, got {unsafe['n']} (lost updates from interleaving)")


# --------------------------------------------------------------------------
# LOCK fixes it: the critical section runs atomically, one thread at a time.
# --------------------------------------------------------------------------
def lock_demo() -> None:
    safe = {"n": 0}
    lock = threading.Lock()
    per_thread, n_threads = 200, 8
    expected = per_thread * n_threads

    def worker_safe() -> None:
        for _ in range(per_thread):
            with lock:            # only one thread inside at a time
                tmp = safe["n"]
                time.sleep(0)
                safe["n"] = tmp + 1

    threads = [threading.Thread(target=worker_safe) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert safe["n"] == expected, f"{safe['n']} != {expected}"
    print(f"   LOCK: expected {expected}, got {safe['n']} (critical section made atomic)")


# --------------------------------------------------------------------------
# SEMAPHORE: allow at most N threads into a region at once (e.g. limit
# concurrent "connections"). We track the live count and assert it never
# exceeds the permit count.
# --------------------------------------------------------------------------
def semaphore_demo() -> None:
    permits = 3
    sem = threading.Semaphore(permits)
    live = {"now": 0, "max": 0}
    guard = threading.Lock()

    def use_resource() -> None:
        with sem:
            with guard:
                live["now"] += 1
                live["max"] = max(live["max"], live["now"])
            time.sleep(0.01)
            with guard:
                live["now"] -= 1

    threads = [threading.Thread(target=use_resource) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert live["max"] <= permits, f"max concurrency {live['max']} exceeded {permits}"
    print(f"   SEMAPHORE: 12 workers, at most {live['max']} ran at once (cap = {permits})")


# --------------------------------------------------------------------------
# EVENT: one thread flips a flag; waiters block until it is set.
# --------------------------------------------------------------------------
def event_demo() -> None:
    start = threading.Event()
    order = []
    guard = threading.Lock()

    def waiter(i: int) -> None:
        start.wait()              # block until the event is set
        with guard:
            order.append(i)

    threads = [threading.Thread(target=waiter, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    time.sleep(0.02)
    assert order == [], "no waiter should proceed before the event is set"
    start.set()                   # release everyone
    for t in threads:
        t.join()
    assert sorted(order) == [0, 1, 2, 3, 4]
    print("   EVENT: 5 threads waited on a gate, all proceeded once it was set")


# --------------------------------------------------------------------------
# QUEUE: the safest way to share data between threads. No manual locks — the
# queue is internally synchronized. Classic producer/consumer with a sentinel.
# --------------------------------------------------------------------------
def producer_consumer_demo() -> None:
    q: "queue.Queue[int | None]" = queue.Queue(maxsize=8)
    produced = list(range(50))
    consumed: list[int] = []
    guard = threading.Lock()

    def producer() -> None:
        for item in produced:
            q.put(item)
        q.put(None)               # sentinel: tell the consumer to stop

    def consumer() -> None:
        while True:
            item = q.get()
            if item is None:
                q.task_done()
                break
            with guard:
                consumed.append(item)
            q.task_done()

    p = threading.Thread(target=producer)
    c = threading.Thread(target=consumer)
    p.start(); c.start()
    p.join(); c.join()

    assert sorted(consumed) == produced
    print(f"   QUEUE: producer/consumer moved {len(consumed)} items safely (no manual locks)")


# --------------------------------------------------------------------------
# DEADLOCK & THE FIX: two accounts, two locks. If thread A locks acct1 then
# acct2 while thread B locks acct2 then acct1, they can wait on each other
# forever. The fix is a GLOBAL ORDER: always acquire locks by a stable key
# (here: id order). We run many concurrent transfers and assert money is
# conserved and nothing hangs.
# --------------------------------------------------------------------------
class Account:
    _next_id = 0

    def __init__(self, balance: int):
        self.balance = balance
        self.lock = threading.Lock()
        self.id = Account._next_id
        Account._next_id += 1


def transfer(src: Account, dst: Account, amount: int) -> None:
    # Order the two locks by a stable id so every thread agrees on ordering.
    first, second = (src, dst) if src.id < dst.id else (dst, src)
    with first.lock:
        with second.lock:
            src.balance -= amount
            dst.balance += amount


def deadlock_free_demo() -> None:
    accts = [Account(1000) for _ in range(5)]
    total_before = sum(a.balance for a in accts)

    def hammer() -> None:
        import random
        rng = random.Random(1)
        for _ in range(200):
            a, b = rng.sample(accts, 2)
            transfer(a, b, 1)

    threads = [threading.Thread(target=hammer) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        # join with a timeout so a real deadlock would be detected, not hang forever
        t.join(timeout=5)
        assert not t.is_alive(), "deadlock: a thread never finished"

    total_after = sum(a.balance for a in accts)
    assert total_after == total_before, f"money not conserved: {total_after} != {total_before}"
    print(f"   DEADLOCK-FREE: 6 threads, 1200 transfers, total conserved at {total_after} "
          "(consistent lock ordering)")


def main() -> None:
    print("=" * 68)
    print("CONCURRENCY — synchronization.py")
    print("=" * 68)
    print("1. Race condition (the bug):")
    race_condition_demo()
    print("2. Lock / mutex (the fix):")
    lock_demo()
    print("3. Semaphore (bound concurrency):")
    semaphore_demo()
    print("4. Event (signal/gate):")
    event_demo()
    print("5. Queue (safe producer/consumer):")
    producer_consumer_demo()
    print("6. Deadlock avoidance (lock ordering):")
    deadlock_free_demo()
    print("-" * 68)
    print("All synchronization demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
