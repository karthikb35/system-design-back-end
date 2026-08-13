"""
01 — DSA in an API: The O(n²) Endpoint vs. the O(n) Refactor
============================================================

SCENARIO: A "bulk username availability" endpoint. The client sends a batch of
desired usernames; the API returns which are already taken.

This is where DSA meets production: the wrong data structure inside a hot
endpoint turns a fast API into a CPU-bound outage as data grows.

    JUNIOR ANTI-PATTERN  ->  membership test against a list  => O(n*m) per call
    SENIOR REFACTOR      ->  membership test against a set    => O(n + m) per call
                            + bounded input + an index dict for O(1) lookups

Run:  python production_code.py       (executes an in-process TestClient demo)
Serve: uvicorn production_code:app --reload
"""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="DSA: anti-pattern vs refactor")

# A simulated "already registered" dataset. In reality this is a DB/cache read.
_TAKEN_LIST: list[str] = [f"user{i}" for i in range(50_000)]   # a Python list
_TAKEN_SET: frozenset[str] = frozenset(_TAKEN_LIST)            # precomputed index


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN
# ===========================================================================
# GOTCHA 1: `name in list` is O(n) — a linear scan. Doing it for m requested
#           names makes the endpoint O(n*m). At 50k users × 500 names that's
#           25M comparisons *per request*, on the event loop, blocking everyone.
# GOTCHA 2: No cap on the input list, so a client can send 1,000,000 names and
#           amplify the cost — an accidental (or deliberate) algorithmic DoS.
# GOTCHA 3: Rebuilds no index; every call re-scans the raw list from scratch.
class BulkCheckJunior(BaseModel):
    usernames: list[str]  # unbounded!


@app.post("/junior/check-usernames")
def check_usernames_junior(body: BulkCheckJunior) -> dict[str, list[str]]:
    taken: list[str] = []
    for name in body.usernames:            # m iterations
        if name in _TAKEN_LIST:            # each is O(n) linear scan  => O(n*m)
            taken.append(name)
    return {"taken": taken}


# ===========================================================================
# ✅ SENIOR REFACTOR
# ===========================================================================
# FIX 1: Test membership against a set/frozenset — O(1) average per lookup, so
#        the whole endpoint is O(n + m). The set is built ONCE at startup, not
#        per request (amortize the indexing cost).
# FIX 2: Bound the input with Pydantic (max_length) so N is provably capped —
#        "what bounds N?" is answered at the API boundary, closing the DoS.
# FIX 3: Deduplicate the request and use set difference — clean and fast.
class BulkCheckSenior(BaseModel):
    # The bound is an ARCHITECTURAL decision surfaced in the contract itself.
    usernames: list[str] = Field(..., min_length=1, max_length=1_000)


@app.post("/senior/check-usernames")
def check_usernames_senior(body: BulkCheckSenior) -> dict[str, list[str]]:
    requested = set(body.usernames)                 # O(m), also dedupes
    taken = sorted(requested & _TAKEN_SET)          # set intersection, O(m)
    available = sorted(requested - _TAKEN_SET)
    return {"taken": taken, "available": available}


# A second facet: O(1) keyed lookup instead of scanning to "find" a record.
_USER_INDEX: dict[str, int] = {name: i for i, name in enumerate(_TAKEN_LIST)}


@app.get("/senior/users/{username}")
def get_user_senior(username: str) -> dict[str, int]:
    # dict lookup is O(1); the junior version would `for u in list: if u == ...`
    if username not in _USER_INDEX:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    return {"username_id": _USER_INDEX[username]}


# ---------------------------------------------------------------------------
# Demonstration: same result, dramatically different cost.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    payload = {"usernames": [f"user{i}" for i in range(0, 1000, 2)] + ["ghost"]}

    t0 = time.perf_counter()
    rj = client.post("/junior/check-usernames", json=payload)
    tj = time.perf_counter() - t0

    t0 = time.perf_counter()
    rs = client.post("/senior/check-usernames", json=payload)
    ts = time.perf_counter() - t0

    print(f"junior O(n*m): {tj*1000:8.2f} ms, taken={len(rj.json()['taken'])}")
    print(f"senior O(n+m): {ts*1000:8.2f} ms, taken={len(rs.json()['taken'])}")
    print(f"speedup      : ~{tj/ts:,.0f}x")

    # The bound rejects an abusive payload at the boundary (HTTP 422).
    abusive = {"usernames": [f"u{i}" for i in range(5000)]}
    print("oversized payload ->", client.post("/senior/check-usernames", json=abusive).status_code)


if __name__ == "__main__":
    _demo()
