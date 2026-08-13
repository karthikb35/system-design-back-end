"""Security helpers — password hashing and JWT issuing.

Passwords are hashed with bcrypt (salted + slow) using the `bcrypt` library
directly. Tokens are signed JWTs; the signature proves integrity, so downstream
services can trust the claims.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

# bcrypt hashes only the first 72 bytes of a password; we truncate explicitly so
# longer inputs hash deterministically instead of raising.
_MAX_BCRYPT_BYTES = 72


class InvalidToken(Exception):
    """Raised when a JWT fails verification (bad signature, expired, malformed,
    wrong algorithm) or is missing its subject claim.

    This lives beside the token code (rather than in service.py with the other
    domain errors) to avoid a circular import: service.py already imports from
    this module, and decoding is a security concern that belongs here.
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
    """Verify a token's signature + expiry and return its `sub` (the user id).

    `jwt.decode` re-computes the HMAC over the header+payload using our secret
    and rejects the token if it does not match, if it has expired, or if it was
    signed with an unexpected algorithm (we pin `algorithms=[...]` to prevent the
    classic "alg: none" / algorithm-confusion downgrade attack). Any jose failure
    is normalised to a single `InvalidToken` so callers never leak jose specifics.

    We enforce verification in the users service because this is where the signing
    secret lives. In a real multi-service system the products/orders services or
    the gateway would verify the SAME token independently via a shared secret or a
    JWKS endpoint — the whole point of a signed JWT is that any holder of the key
    can validate it locally without a round-trip back to the issuer.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:  # bad signature, expired, malformed, wrong alg
        raise InvalidToken("could not validate token") from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidToken("token missing subject claim")
    return subject
