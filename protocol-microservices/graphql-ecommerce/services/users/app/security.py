"""Password hashing (bcrypt) and JWT issuing (python-jose).

We call the ``bcrypt`` library directly rather than via passlib: passlib 1.7.4
reads ``bcrypt.__about__`` which was removed in bcrypt 5.x, so it crashes at
import time. bcrypt also has a hard 72-byte input limit, so we truncate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

_MAX_BCRYPT_BYTES = 72


class InvalidToken(Exception):
    """A bearer token was missing, malformed, expired, or had a bad signature.

    Transport-agnostic on purpose: security.py knows nothing about GraphQL, so
    the schema layer catches this and turns it into a ``GraphQLError``.
    """


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    claims = {"sub": subject, "exp": expire}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Verify a JWT's signature + expiry and return its ``sub`` (the user id).

    ``jose`` checks the HMAC signature against ``jwt_secret`` and enforces the
    ``exp`` claim, raising ``JWTError`` on any failure (bad signature, expired,
    malformed). We normalise every failure — including a token that verifies but
    carries no ``sub`` — into a single ``InvalidToken`` so callers have one thing
    to catch.
    """
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidToken("could not validate token") from exc
    subject = claims.get("sub")
    if not subject:
        raise InvalidToken("token is missing a subject")
    return str(subject)
