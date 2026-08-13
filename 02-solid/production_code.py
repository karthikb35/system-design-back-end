"""
02 — SOLID in FastAPI: The Fat Endpoint vs. the Layered Refactor
================================================================

SCENARIO: "Register a user and charge them." The single most common junior
FastAPI shape is a route function that does *everything* — validation, business
rules, database access, a payment call, and email — all inline.

    JUNIOR ANTI-PATTERN  ->  one route function does 5 jobs + `if provider ==`
                            (violates SRP, OCP, DIP; untestable without HTTP/DB)
    SENIOR REFACTOR      ->  Router -> Service -> Repository, gateways behind an
                            abstraction, all injected via Depends (DIP)

Run:  python production_code.py
"""

from __future__ import annotations

from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title="SOLID: anti-pattern vs refactor")

# Shared fake infrastructure so both versions "work".
_FAKE_DB: dict[str, dict] = {}


# ===========================================================================
# ❌ JUNIOR ANTI-PATTERN — the "God route"
# ===========================================================================
# GOTCHA (SRP): this function changes for FIVE unrelated reasons — validation,
#   pricing, persistence, payment, and notifications. Any change risks the rest.
# GOTCHA (OCP): adding a payment provider means editing this tested function's
#   if/elif ladder — "open for modification", the opposite of what we want.
# GOTCHA (DIP): it hard-codes concrete details (the dict DB, the provider logic,
#   "sending" email), so it CANNOT be unit-tested without spinning up HTTP and
#   monkeypatching globals. Business logic is trapped inside the web layer.
class RegisterJunior(BaseModel):
    email: str
    amount: float
    provider: str


@app.post("/junior/register")
def register_junior(body: RegisterJunior) -> dict:
    # 1. validation (inline)
    if "@" not in body.email:
        raise HTTPException(400, "bad email")
    # 2. business rule (inline)
    total = body.amount * 1.08
    # 3. persistence (inline, concrete)
    if body.email in _FAKE_DB:
        raise HTTPException(409, "exists")
    _FAKE_DB[body.email] = {"total": total}
    # 4. payment (if/elif ladder — OCP violation)
    if body.provider == "stripe":
        ref = f"stripe_{body.email}"
    elif body.provider == "paypal":
        ref = f"paypal_{body.email}"
    else:
        raise HTTPException(400, "unknown provider")
    # 5. notification (inline side effect)
    print(f"[email] welcome {body.email}")
    return {"charged": total, "ref": ref}


# ===========================================================================
# ✅ SENIOR REFACTOR — layers, abstractions, and dependency injection
# ===========================================================================

# --- Contract (validation lives at the boundary) ---------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    amount: float = Field(gt=0)
    provider: str


class RegisterResponse(BaseModel):
    email: EmailStr
    charged: float
    reference: str


# --- Abstractions (DIP + ISP: small, role-based interfaces) ----------------
class UserRepository(Protocol):
    def exists(self, email: str) -> bool: ...
    def save(self, email: str, total: float) -> None: ...


class PaymentGateway(Protocol):  # OCP: new providers implement this, edit nothing
    def charge(self, email: str, amount: float) -> str: ...


class Notifier(Protocol):
    def welcome(self, email: str) -> None: ...


# --- Concrete implementations (swappable at the composition root) ----------
class DictUserRepository:
    def exists(self, email: str) -> bool:
        return email in _FAKE_DB

    def save(self, email: str, total: float) -> None:
        _FAKE_DB[email] = {"total": total}


class StripeGateway:
    def charge(self, email: str, amount: float) -> str:
        return f"stripe_{email}"


class PayPalGateway:  # added WITHOUT touching StripeGateway or the service (OCP)
    def charge(self, email: str, amount: float) -> str:
        return f"paypal_{email}"


class ConsoleNotifier:
    def welcome(self, email: str) -> None:
        print(f"[email] welcome {email}")


# --- Service (business logic; imports no FastAPI => unit-testable) ----------
class RegistrationService:
    def __init__(self, repo: UserRepository, notifier: Notifier) -> None:
        self._repo = repo
        self._notifier = notifier

    def register(self, email: str, amount: float, gateway: PaymentGateway) -> RegisterResponse:
        if self._repo.exists(email):
            raise ValueError("already registered")
        total = round(amount * 1.08, 2)          # the one place pricing changes
        reference = gateway.charge(email, total)
        self._repo.save(email, total)
        self._notifier.welcome(email)
        return RegisterResponse(email=email, charged=total, reference=reference)


# --- Composition root: bind abstractions to concretions in ONE place -------
def get_service() -> RegistrationService:
    return RegistrationService(DictUserRepository(), ConsoleNotifier())


_GATEWAYS: dict[str, PaymentGateway] = {"stripe": StripeGateway(), "paypal": PayPalGateway()}


def get_gateway(provider: str) -> PaymentGateway:
    gateway = _GATEWAYS.get(provider)
    if gateway is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown provider")
    return gateway


ServiceDep = Annotated[RegistrationService, Depends(get_service)]


# --- Router: thin; translate HTTP <-> domain and errors <-> status codes ----
@app.post("/senior/register", response_model=RegisterResponse, status_code=201)
def register_senior(body: RegisterRequest, service: ServiceDep) -> RegisterResponse:
    try:
        return service.register(body.email, body.amount, get_gateway(body.provider))
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


# ---------------------------------------------------------------------------
# Demo: the refactored SERVICE is testable with NO HTTP and NO real DB.
# ---------------------------------------------------------------------------
def _demo() -> None:
    from fastapi.testclient import TestClient

    _FAKE_DB.clear()
    client = TestClient(app)
    print("junior:", client.post("/junior/register",
          json={"email": "a@b.com", "amount": 100, "provider": "stripe"}).json())

    _FAKE_DB.clear()
    print("senior:", client.post("/senior/register",
          json={"email": "a@b.com", "amount": 100, "provider": "paypal"}).json())

    # The payoff — pure unit test of business logic, no web layer:
    _FAKE_DB.clear()
    svc = RegistrationService(DictUserRepository(), ConsoleNotifier())
    out = svc.register("c@d.com", 200, StripeGateway())
    assert out.charged == 216.0
    print("unit-tested service (no HTTP/DB):", out.model_dump())


if __name__ == "__main__":
    _demo()
