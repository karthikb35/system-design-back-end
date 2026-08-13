"""Security helpers — password hashing (bcrypt) and JWT issuing/verifying (jose)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

_MAX_BCRYPT_BYTES = 72


class InvalidToken(Exception):
    """A JWT failed signature/expiry verification, or carried no subject.

    A dedicated domain error keeps this module transport-agnostic: the servicer
    decides how to surface it (here, a gRPC UNAUTHENTICATED status).
    """


def _to_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_to_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Verify a token's signature + expiry and return its ``sub`` claim.

    ``jwt.decode`` checks the HMAC signature against our secret and enforces the
    ``exp`` claim, raising ``JWTError`` on any tampering or expiry. We translate
    that (and a token that decodes but lacks a subject) into our own domain
    ``InvalidToken`` so callers never depend on jose's exception hierarchy.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidToken("token is invalid or expired") from exc
    subject = payload.get("sub")
    if not subject:
        raise InvalidToken("token is missing the subject claim")
    return subject
