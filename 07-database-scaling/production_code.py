"""
07 — Database Scaling in FastAPI: The N+1 Query vs. Batched Access + Read Routing
================================================================================

SCENARIO: A "list orders with their customer" endpoint.

    JUNIOR ANTI-PATTERN  ->  the N+1 query problem (1 query for the list, then 1
                            query PER row), plus sending all reads to the primary
    SENIOR REFACTOR      ->  a single batched/joined query (O(1) round-trips) +
                            routing reads to a replica to spare the primary

This models the query COUNT and routing with an in-memory fake "DB" so the
pathology is visible without a real database.

Run:  python production_code.py
"""

from __future__ import annotations

from enum import Enum, auto

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="DB Scaling: anti-pattern vs refactor")


# --- A fake DB that COUNTS round-trips so we can see the N+1 pathology -------
class FakeDB:
    def __init__(self) -> None:
        self.customers = {i: f"customer-{i}" for i in range(1, 6)}
        self.orders = [{"id": oid, "customer_id": (oid % 5) + 1} for oid in range(20)]
        self.query_count = 0        # every "round trip" increments this
        self.primary_reads = 0
        self.replica_reads = 0

    def fetch_orders(self, on_replica: bool = False) -> list[dict]:
        self.query_count += 1
        self._count_target(on_replica)
        return list(self.orders)

    def fetch_customer(self, customer_id: int, on_replica: bool = False) -> str:
        self.query_count += 1
        self._count_target(on_replica)
        return self.customers[customer_id]

    def fetch_customers_bulk(self, ids: set[int], on_replica: bool = False) -> dict[int, str]:
        self.query_count += 1        # ONE round trip for all ids (an IN query / join)
        self._count_target(on_replica)
        return {i: self.customers[i] for i in ids}

    def _count_target(self, on_replica: bool) -> None:
        if on_replica:
            self.replica_reads += 1
        else:
            self.primary_reads += 1


db = FakeDB()


class OrderOut(BaseModel):
    id: int
    customer: str


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN — the N+1 query
# ===========================================================================
# GOTCHA 1 (N+1): 1 query for the orders, then 1 MORE query for EACH order's
#   customer. 20 orders => 21 queries. At 1,000 rows that's 1,001 round trips —
#   each with network + planning overhead. This is the #1 ORM performance bug.
# GOTCHA 2 (primary reads): all reads hit the PRIMARY, wasting the write node's
#   capacity on read traffic that a replica could serve.
@app.get("/junior/orders")
def list_orders_junior() -> list[OrderOut]:
    orders = db.fetch_orders(on_replica=False)                 # 1 query
    result = []
    for o in orders:
        # +1 query PER row (the "N" in N+1) — and on the primary
        name = db.fetch_customer(o["customer_id"], on_replica=False)
        result.append(OrderOut(id=o["id"], customer=name))
    return result


# ===========================================================================
# ✅ SENIOR REFACTOR — batch the access, route reads to a replica
# ===========================================================================
# FIX 1 (kill N+1): fetch the orders, collect the distinct customer_ids, then
#   fetch ALL customers in ONE query (an IN(...) / JOIN). 2 queries total,
#   regardless of row count — O(1) round-trips instead of O(n).
# FIX 2 (read routing): this is a read-only endpoint, so route to a REPLICA and
#   leave the primary free for writes (accepting eventual-consistency lag).
class QueryTarget(Enum):
    PRIMARY = auto()
    REPLICA = auto()


@app.get("/senior/orders")
def list_orders_senior() -> list[OrderOut]:
    orders = db.fetch_orders(on_replica=True)                  # 1 query (replica)
    ids = {o["customer_id"] for o in orders}
    names = db.fetch_customers_bulk(ids, on_replica=True)      # 1 query for ALL
    return [OrderOut(id=o["id"], customer=names[o["customer_id"]]) for o in orders]


# ---------------------------------------------------------------------------
# Demo: compare query counts and where the reads landed.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    db.query_count = db.primary_reads = db.replica_reads = 0
    client.get("/junior/orders")
    print(f"junior: {db.query_count} queries "
          f"(primary={db.primary_reads}, replica={db.replica_reads})  <- N+1")

    db.query_count = db.primary_reads = db.replica_reads = 0
    client.get("/senior/orders")
    print(f"senior: {db.query_count} queries "
          f"(primary={db.primary_reads}, replica={db.replica_reads})  <- batched + replica")


if __name__ == "__main__":
    _demo()
