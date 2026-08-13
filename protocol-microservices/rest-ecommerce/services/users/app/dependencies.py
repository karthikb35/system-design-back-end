"""FastAPI dependencies — request-time authentication.

This is the enforcement half of auth. Login (in the service layer) MINTS a JWT;
this dependency VERIFIES one on every protected request and hands the route the
authenticated subject (the user id) so handlers never parse headers themselves.

We enforce here in the users service because it owns the signing secret. In a
real deployment the products/orders services or the gateway would run the same
check against a shared secret or a JWKS endpoint; a signed JWT is verifiable by
any holder of the key without calling back to the issuer.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import InvalidToken, decode_access_token

# auto_error=False so a MISSING credential returns our own 401 (with the
# WWW-Authenticate hint) instead of HTTPBearer's default 403 — that way "no
# token" and "bad token" are indistinguishable to a client, as they should be.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Extract and verify the Bearer token; return the authenticated user id.

    Raises 401 for a missing/non-Bearer header or any token that fails
    verification (bad signature, expired, malformed, missing subject).
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(credentials.credentials)
    except InvalidToken:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
