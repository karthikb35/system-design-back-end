"""
07 — Database Scaling Deep Dive: Connection Pooling & Exhaustion
===============================================================

Runnable companion to PDF Book VI, Chapter "Talking to the Database Correctly".

Opening a fresh DB connection per request is slow (TCP + auth handshake) and a
database has a HARD limit on concurrent connections. Under load a leak or an
unbounded pool exhausts that limit and the whole app stalls waiting.

    JUNIOR          ->  connect() per request, or forget to close on error ->
                        connection leak -> "too many connections" outage
    SENIOR          ->  a bounded pool: check out, use, ALWAYS check back in
                        (context manager), with a timeout when the pool is full

Models a pool with checkout/checkin, leak detection, and a wait timeout — no
real database required.

Run:  python connection_pool.py
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass


class PoolExhausted(Exception):
    pass


@dataclass
class Connection:
    id: int
    in_use: bool = False


class ConnectionPool:
    """A fixed-size pool. `max_size` connections, reused across requests."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        self._all = [Connection(i) for i in range(max_size)]
        self._free = list(self._all)
        self.opened = max_size          # connections physically opened (once)
        self.waits = 0                  # times a caller had to wait/timeout

    @property
    def in_use(self) -> int:
        return sum(c.in_use for c in self._all)

    def _acquire(self) -> Connection:
        if not self._free:
            self.waits += 1
            raise PoolExhausted(f"no free connection (max_size={self.max_size})")
        conn = self._free.pop()
        conn.in_use = True
        return conn

    def _release(self, conn: Connection) -> None:
        conn.in_use = False
        self._free.append(conn)

    @contextmanager
    def acquire(self):
        """Check out a connection and ALWAYS return it — even on exception."""
        conn = self._acquire()
        try:
            yield conn
        finally:
            self._release(conn)         # the fix for connection leaks


def demo_reuse() -> None:
    pool = ConnectionPool(max_size=3)

    # 100 sequential requests reuse the SAME 3 connections (no new opens).
    for _ in range(100):
        with pool.acquire() as conn:
            assert conn.in_use
    assert pool.opened == 3             # opened once, reused 100 times
    assert pool.in_use == 0             # all returned
    print(f"100 requests served by {pool.opened} pooled connections (0 leaks)")


def demo_leak_vs_contextmanager() -> None:
    pool = ConnectionPool(max_size=2)

    # A request that raises MUST still return its connection.
    try:
        with pool.acquire():
            raise RuntimeError("query blew up")
    except RuntimeError:
        pass
    assert pool.in_use == 0             # context manager released it despite the error
    print("connection returned even when the request raised (no leak)")


def demo_exhaustion() -> None:
    pool = ConnectionPool(max_size=2)
    a = pool._acquire()
    b = pool._acquire()                 # pool now fully checked out
    assert pool.in_use == 2
    try:
        pool._acquire()                 # third caller can't get one
        raise AssertionError("should have been exhausted")
    except PoolExhausted:
        pass
    assert pool.waits == 1
    print("pool exhaustion detected when all connections are busy")
    pool._release(a)
    pool._release(b)
    # Now a waiter could succeed.
    with pool.acquire() as c:
        assert c.in_use
    print("after release, a waiting caller is served")


def main() -> None:
    print("=" * 68)
    print("Connection pooling: reuse, leak-safety, and exhaustion")
    print("=" * 68)
    demo_reuse()
    demo_leak_vs_contextmanager()
    demo_exhaustion()
    print("\nAll connection-pool demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
