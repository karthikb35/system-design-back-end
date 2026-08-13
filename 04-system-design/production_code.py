"""
04 — System Design in FastAPI: The Non-Idempotent, Blocking Endpoint
====================================================================

SCENARIO: A "charge payment" endpoint. Clients (and load balancers) retry on
timeout, and the charge triggers slow downstream work.

    JUNIOR ANTI-PATTERN  ->  no idempotency key (retries double-charge) and heavy
                            work done synchronously on the request path
    SENIOR REFACTOR      ->  idempotency-key dependency (exactly-once EFFECT) +
                            offload slow work to a background task

Run:  python production_code.py
"""

from __future__ import annotations

from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="System Design: anti-pattern vs refactor")

_LEDGER: dict[str, dict] = {}                 # charge_id -> record
_IDEMPOTENCY: dict[str, dict] = {}            # idempotency_key -> stored response
_charge_seq = {"n": 0}


def _do_charge(amount: float) -> dict:
    _charge_seq["n"] += 1
    cid = f"txn-{_charge_seq['n']}"
    _LEDGER[cid] = {"amount": amount}
    return {"charge_id": cid, "amount": amount}


def _slow_receipt_email(charge_id: str) -> None:
    # Simulates expensive downstream work that does NOT belong on the hot path.
    # (imagine PDF render + SMTP — hundreds of ms to seconds)
    _ = charge_id


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN
# ===========================================================================
# GOTCHA 1 (idempotency): the client times out and retries; there's nothing to
#   deduplicate on, so the customer is charged TWICE. Networks are at-least-once.
# GOTCHA 2 (blocking work on the request path): the receipt email runs inline,
#   inflating p99 latency and holding the connection/worker for the whole time.
class ChargeJunior(BaseModel):
    amount: float


@app.post("/junior/charge")
def charge_junior(body: ChargeJunior) -> dict:
    result = _do_charge(body.amount)          # side effect with no dedupe
    _slow_receipt_email(result["charge_id"])  # slow work blocks the response
    return result


# ===========================================================================
# ✅ SENIOR REFACTOR
# ===========================================================================
# FIX 1 (idempotency): require an Idempotency-Key header. The first request with
#   a key performs the charge and STORES the response keyed by it; any retry with
#   the same key REPLAYS the stored response without re-charging. This converts
#   at-least-once delivery into exactly-once EFFECT.
# FIX 2 (offload): push the slow receipt email to a BackgroundTask so the request
#   returns immediately; the hot path only does the essential work.
class ChargeSenior(BaseModel):
    amount: float = Field(gt=0)


def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Idempotency-Key header is required for charges",
        )
    return idempotency_key


KeyDep = Annotated[str, Depends(require_idempotency_key)]


@app.post("/senior/charge", status_code=status.HTTP_201_CREATED)
def charge_senior(body: ChargeSenior, key: KeyDep, background: BackgroundTasks) -> dict:
    # Retry detected -> replay the stored result, DO NOT charge again.
    if key in _IDEMPOTENCY:
        return {**_IDEMPOTENCY[key], "idempotent_replay": True}

    result = _do_charge(body.amount)
    # Persist the result under the key BEFORE returning, so a crash-then-retry
    # is still safe (the retry finds the stored response).
    _IDEMPOTENCY[key] = result

    # Slow work leaves the request path entirely.
    background.add_task(_slow_receipt_email, result["charge_id"])
    return {**result, "idempotent_replay": False}


# ---------------------------------------------------------------------------
# Demo: the junior endpoint double-charges on retry; the senior one doesn't.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    _LEDGER.clear(); _charge_seq["n"] = 0
    client.post("/junior/charge", json={"amount": 100})
    client.post("/junior/charge", json={"amount": 100})   # simulated retry
    print(f"junior ledger entries after retry: {len(_LEDGER)}  (double charge!)")

    _LEDGER.clear(); _IDEMPOTENCY.clear(); _charge_seq["n"] = 0
    headers = {"Idempotency-Key": "abc-123"}
    r1 = client.post("/senior/charge", json={"amount": 100}, headers=headers)
    r2 = client.post("/senior/charge", json={"amount": 100}, headers=headers)  # retry
    print(f"senior ledger entries after retry: {len(_LEDGER)}  (charged once)")
    print("  first :", r1.json())
    print("  retry :", r2.json())
    print("  missing key ->", client.post("/senior/charge", json={"amount": 5}).status_code)


if __name__ == "__main__":
    _demo()
