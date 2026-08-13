"""
10 — Security Deep Dive: JSON Web Tokens (JWT) from Scratch
==========================================================

Runnable companion to PDF Book VII, Chapter "Authentication & Authorization".

Builds a signed JWT with only the standard library so you SEE what a token is:
three base64url parts — header.payload.signature — where the signature is an
HMAC over "header.payload" with a server secret.

    JUNIOR MISCONCEPTION  ->  "the payload is encrypted / safe to put secrets in"
    REALITY               ->  JWT payloads are only base64-ENCODED (readable by
                            anyone); the signature only proves INTEGRITY, not
                            secrecy. Never put secrets in a JWT.

Demonstrates: signing, verifying, tamper detection, and expiry (`exp`).

Run:  python jwt_auth.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json


class InvalidToken(Exception):
    pass


def _b64url_encode(raw: bytes) -> str:
    # JWT uses URL-safe base64 WITHOUT padding.
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)      # restore stripped padding
    return base64.urlsafe_b64decode(text + pad)


def sign(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def verify(token: str, secret: str, *, now: int) -> dict:
    try:
        h, p, s = token.split(".")
    except ValueError:
        raise InvalidToken("malformed token")

    # Recompute the signature and compare in CONSTANT TIME (no early-exit leak).
    expected = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(s)):
        raise InvalidToken("bad signature — token was tampered with or wrong key")

    payload = json.loads(_b64url_decode(p))
    if "exp" in payload and now >= payload["exp"]:
        raise InvalidToken("token expired")
    return payload


def demo() -> None:
    secret = "server-side-signing-key"
    token = sign({"sub": "user-42", "role": "admin", "exp": 1000}, secret)
    print("token:", token[:48], "...")

    # A valid token verifies and returns its claims.
    claims = verify(token, secret, now=500)
    assert claims["sub"] == "user-42" and claims["role"] == "admin"
    print("verified claims:", claims)

    # The payload is only ENCODED, not encrypted — anyone can read it.
    _, p, _ = token.split(".")
    assert json.loads(_b64url_decode(p))["role"] == "admin"
    print("payload is readable without the secret (base64, not encryption)")

    # Tampering with the payload breaks the signature.
    h, p, s = token.split(".")
    forged_payload = _b64url_encode(json.dumps({"sub": "user-42", "role": "superadmin", "exp": 1000}).encode())
    forged = f"{h}.{forged_payload}.{s}"
    try:
        verify(forged, secret, now=500)
        raise AssertionError("forged token should be rejected")
    except InvalidToken as exc:
        print("tamper rejected:", exc)

    # Wrong secret is rejected.
    try:
        verify(token, "attacker-guess", now=500)
        raise AssertionError("wrong-key token should be rejected")
    except InvalidToken:
        print("wrong signing key rejected")

    # Expired token is rejected.
    try:
        verify(token, secret, now=2000)   # now > exp
        raise AssertionError("expired token should be rejected")
    except InvalidToken as exc:
        print("expiry enforced:", exc)


def main() -> None:
    print("=" * 68)
    print("JWT from scratch: sign, verify, tamper detection, expiry")
    print("=" * 68)
    demo()
    print("\nAll JWT demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
