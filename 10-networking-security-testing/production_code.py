"""
10 — Networking, Security & Testing: The Secure Request Pipeline
===============================================================

The three example scripts in this folder each isolate ONE idea (password
hashing, JWT, SQL injection, test doubles). This module is the capstone: it
wires them into a single, coherent request pipeline the way a real service
would — the path a request actually travels from credentials to an authorized
action:

    register  ->  hash the password (salted, slow KDF)         [OWASP A02]
    login     ->  verify in constant time, then MINT a token   [OWASP A07]
    request   ->  VERIFY the token's signature + expiry        [OWASP A07]
              ->  look up the user with a PARAMETERIZED query  [OWASP A03]
              ->  check the caller's ROLE (authz != authn)     [OWASP A01]

    JUNIOR MISCONCEPTION  ->  "the JWT payload is encrypted, so a token is a
                            safe place to stash a password or a secret flag,
                            and if a request carries a valid token the user is
                            allowed to do the thing."
    REALITY               ->  a JWT payload is only base64url-ENCODED — readable
                            by anyone who holds the token. The signature proves
                            INTEGRITY (nobody tampered with the claims), not
                            SECRECY. And a valid token only answers *who* you are
                            (authentication); it says NOTHING about *what* you may
                            do (authorization). Those are separate checks.

Standard library only (hashlib, hmac, secrets, base64, json, time) — no PyJWT,
no bcrypt, no database driver — so you can see exactly what each layer does.

Run:  python production_code.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field


# ===========================================================================
# Errors — fail closed, and never leak *why* to the caller in production.
# ===========================================================================
class AuthError(Exception):
    """Authentication failed (bad credentials, bad/expired token)."""


class ForbiddenError(Exception):
    """Authenticated, but not authorized for this action."""


# ===========================================================================
# 1. PASSWORD STORAGE  —  OWASP A02 (Cryptographic Failures)
# ---------------------------------------------------------------------------
# WHY salted + slow: a fast unsalted hash (md5/sha256) of a leaked table is
# cracked in minutes — rainbow tables precompute common passwords, and GPUs try
# billions of guesses per second. A per-user random SALT defeats precomputation
# (identical passwords hash differently), and a deliberately SLOW KDF (PBKDF2
# here; argon2/scrypt/bcrypt in production) makes each guess expensive.
# ===========================================================================
_PBKDF2_ROUNDS = 120_000          # tune upward as CPUs get faster (prod: 600k+ / argon2)


def hash_password(password: str, *, rounds: int = _PBKDF2_ROUNDS) -> str:
    """Return a self-describing record 'pbkdf2_sha256$rounds$salt$hash'.

    The salt and cost are stored WITH the hash so verification is reproducible
    and the cost can be raised later without invalidating old records.
    """
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Recompute with the stored salt/cost and compare in CONSTANT TIME.

    hmac.compare_digest never short-circuits on the first differing byte, so an
    attacker cannot use response timing to recover the hash byte by byte.
    """
    try:
        algo, rounds_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        rounds = int(rounds_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False                                    # malformed record -> fail closed
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return hmac.compare_digest(derived, expected)


# ===========================================================================
# 2. STATELESS TOKENS (JWT)  —  OWASP A07 (Identification & Auth Failures)
# ---------------------------------------------------------------------------
# A JWT is three base64url parts: header.payload.signature. The signature is an
# HMAC of "header.payload" under a server-only secret. Integrity, NOT secrecy.
# `exp` bounds the blast radius of a stolen token; short lifetimes + refresh /
# rotation limit how long a leaked token is useful.
# ===========================================================================
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)                        # restore stripped padding
    return base64.urlsafe_b64decode(text + pad)


def issue_token(subject: str, role: str, secret: str, *, now: int, ttl: int = 900) -> str:
    """Mint a signed HS256 token whose claims carry the subject, role, and exp."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "role": role, "iat": now, "exp": now + ttl}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(signature)}"


def verify_token(token: str, secret: str, *, now: int) -> dict:
    """Validate signature THEN expiry, returning the claims. Raises AuthError.

    Order matters: recompute the signature and compare in constant time before
    trusting ANY field in the payload — an unverified payload is attacker input.
    """
    try:
        h, p, s = token.split(".")
    except ValueError:
        raise AuthError("malformed token")
    expected = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(s)):
        raise AuthError("bad signature — tampered token or wrong key")
    claims = json.loads(_b64url_decode(p))
    if now >= claims.get("exp", 0):
        raise AuthError("token expired")
    return claims


# ===========================================================================
# 3. DATA ACCESS  —  OWASP A03 (Injection)
# ---------------------------------------------------------------------------
# The vulnerability is always the same shape: untrusted input concatenated into
# a query STRING, so the input can change the query's STRUCTURE. Parameterized
# queries send SQL and DATA on separate channels, so input is ALWAYS data.
# We model a toy engine so the injection is visible without a real database.
# ===========================================================================
@dataclass
class UserRepository:
    """In-memory 'users' table with a naive interpreter, to contrast lookups."""

    _rows: dict[str, dict] = field(default_factory=dict)

    def add(self, record: dict) -> None:
        self._rows[record["name"]] = record

    # ---- VULNERABLE: interprets a concatenated query string ---------------
    def find_by_name_unsafe(self, user_input: str) -> list[dict]:
        # The footgun a real driver would execute: input is spliced into SQL.
        raw_sql = f"SELECT * FROM users WHERE name = '{user_input}'"
        # A tautology like  ' OR '1'='1  makes the predicate always true, so an
        # attacker retrieves EVERY row — an authentication bypass on a login path.
        lowered = raw_sql.lower()
        if "or '1'='1" in lowered or "or 1=1" in lowered:
            return list(self._rows.values())
        # Otherwise behave like the real engine parsing the submitted string.
        name = raw_sql.split("'")[1] if "'" in raw_sql else ""
        row = self._rows.get(name)
        return [row] if row else []

    # ---- SAFE: SQL and parameters are separate; input is only DATA --------
    def find_by_name(self, sql_template: str, params: tuple) -> list[dict]:
        if sql_template.count("?") != len(params):
            raise ValueError("parameter count does not match placeholders")
        # The driver binds params as opaque values — they can never be parsed as
        # SQL, so ' OR '1'='1 is just a (non-existent) username to look up.
        (wanted,) = params
        row = self._rows.get(wanted)
        return [row] if row else []


# ===========================================================================
# 4. AUTHORIZATION  —  OWASP A01 (Broken Access Control)
# ---------------------------------------------------------------------------
# Authentication answered WHO you are (a valid token). Authorization answers
# WHAT you may do. They are DIFFERENT checks — a valid admin-shaped token from a
# 'user' account must still be refused an admin action. Enforce on the server;
# never trust a role the client asserts outside a signed, server-issued claim.
# ===========================================================================
def require_role(claims: dict, needed: str) -> None:
    if claims.get("role") != needed:
        raise ForbiddenError(f"role '{claims.get('role')}' may not perform a '{needed}' action")


# ===========================================================================
# 5. THE PIPELINE  —  compose the layers into the real request path.
# ===========================================================================
@dataclass
class AuthService:
    """Ties hashing + tokens + parameterized lookup + authz into one flow."""

    secret: str
    repo: UserRepository = field(default_factory=UserRepository)

    def register(self, name: str, password: str, role: str) -> None:
        # Store ONLY the salted hash; the plaintext never touches the record.
        self.repo.add({"name": name, "role": role, "password_hash": hash_password(password)})

    def login(self, name: str, password: str, *, now: int) -> str:
        # Look the user up with a PARAMETERIZED query so a crafted username can
        # never bypass the check via injection.
        rows = self.repo.find_by_name("SELECT * FROM users WHERE name = ?", (name,))
        # Constant-time verify. Return the SAME error for "no such user" and
        # "wrong password" so we don't leak which usernames exist.
        if not rows or not verify_password(password, rows[0]["password_hash"]):
            raise AuthError("invalid credentials")
        return issue_token(name, rows[0]["role"], self.secret, now=now)

    def perform(self, token: str, needed_role: str, *, now: int) -> dict:
        # 1) authenticate: is the token genuine and unexpired?
        claims = verify_token(token, self.secret, now=now)
        # 2) authorize: does this identity hold the required role?
        require_role(claims, needed_role)
        return {"actor": claims["sub"], "action": needed_role, "status": "ok"}


# ===========================================================================
# SELF-TESTS — plain asserts (what pytest would run), grouped by concern.
# ===========================================================================
def test_password_hashing() -> None:
    stored = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", stored) is True
    assert verify_password("wrong password", stored) is False
    # Unique salts: the same password yields different records for two users.
    a, b = hash_password("hunter2"), hash_password("hunter2")
    assert a != b and verify_password("hunter2", a) and verify_password("hunter2", b)
    # Fail closed on a corrupt record instead of raising.
    assert verify_password("anything", "not-a-record") is False
    # The plaintext is never present in the stored value.
    assert "correct horse" not in stored


def test_jwt_integrity_and_expiry() -> None:
    secret = "server-only-signing-key"
    token = issue_token("user-42", "admin", secret, now=1000, ttl=900)
    claims = verify_token(token, secret, now=1100)
    assert claims["sub"] == "user-42" and claims["role"] == "admin"
    # The payload is only base64url-encoded — readable WITHOUT the secret.
    _, payload_b64, _ = token.split(".")
    assert json.loads(_b64url_decode(payload_b64))["role"] == "admin"
    # Tampering with the claims invalidates the signature.
    h, _p, s = token.split(".")
    forged_p = _b64url_encode(json.dumps({"sub": "user-42", "role": "superadmin", "exp": 9999}).encode())
    _assert_auth_error(lambda: verify_token(f"{h}.{forged_p}.{s}", secret, now=1100), "tamper")
    # Wrong signing key is rejected.
    _assert_auth_error(lambda: verify_token(token, "attacker-guess", now=1100), "wrong key")
    # Expiry is enforced (now >= exp).
    _assert_auth_error(lambda: verify_token(token, secret, now=5000), "expiry")


def test_sql_injection_prevention() -> None:
    repo = UserRepository()
    for name, role in [("alice", "user"), ("bob", "user"), ("root", "admin")]:
        repo.add({"name": name, "role": role})
    # Normal lookup returns exactly one row on either path.
    assert repo.find_by_name_unsafe("alice")[0]["role"] == "user"
    assert repo.find_by_name("SELECT * FROM users WHERE name = ?", ("alice",))[0]["role"] == "user"
    # Injection: the classic tautology exfiltrates the whole table (auth bypass).
    leaked = repo.find_by_name_unsafe("' OR '1'='1")
    assert len(leaked) == 3
    # The SAME payload via a parameterized query matches nothing — it is data.
    assert repo.find_by_name("SELECT * FROM users WHERE name = ?", ("' OR '1'='1",)) == []
    # Arity is validated, catching template/param mismatches.
    _assert_value_error(lambda: repo.find_by_name("... name = ? AND role = ?", ("alice",)))


def test_authorization_is_not_authentication() -> None:
    svc = AuthService(secret="s3cr3t")
    svc.register("admin_ann", "pw-ann", role="admin")
    svc.register("user_uma", "pw-uma", role="user")
    now = 2000
    admin_token = svc.login("admin_ann", "pw-ann", now=now)
    user_token = svc.login("user_uma", "pw-uma", now=now)
    # Authenticated AND authorized: admin performs an admin action.
    assert svc.perform(admin_token, "admin", now=now)["status"] == "ok"
    # Authenticated but NOT authorized: a valid user token is refused admin work.
    _assert_forbidden(lambda: svc.perform(user_token, "admin", now=now))
    # Wrong password never mints a token in the first place.
    _assert_auth_error(lambda: svc.login("admin_ann", "wrong", now=now), "bad password")
    # A crafted username cannot bypass login via injection.
    _assert_auth_error(lambda: svc.login("' OR '1'='1", "whatever", now=now), "injection login")


def test_full_pipeline_happy_path() -> None:
    svc = AuthService(secret="pipeline-secret")
    svc.register("carol", "s3cure-pw", role="admin")
    now = int(time.time())
    token = svc.login("carol", "s3cure-pw", now=now)
    result = svc.perform(token, "admin", now=now)
    assert result == {"actor": "carol", "action": "admin", "status": "ok"}


# --- tiny assertion helpers (keep the tests above readable) -----------------
def _assert_auth_error(fn, label: str) -> None:
    try:
        fn()
    except AuthError:
        return
    raise AssertionError(f"expected AuthError for: {label}")


def _assert_forbidden(fn) -> None:
    try:
        fn()
    except ForbiddenError:
        return
    raise AssertionError("expected ForbiddenError")


def _assert_value_error(fn) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def main() -> None:
    print("=" * 68)
    print("Secure request pipeline: hash -> token -> query -> authorize")
    print("=" * 68)
    checks = [
        ("password hashing (salted PBKDF2 + constant-time verify)", test_password_hashing),
        ("JWT integrity, tamper detection, and expiry", test_jwt_integrity_and_expiry),
        ("SQL injection prevention (parameterized vs concatenated)", test_sql_injection_prevention),
        ("authorization is a separate check from authentication", test_authorization_is_not_authentication),
        ("end-to-end pipeline happy path", test_full_pipeline_happy_path),
    ]
    for name, fn in checks:
        fn()
        print(f"  [OK] {name}")
    print("\nall checks passed")


if __name__ == "__main__":
    main()
