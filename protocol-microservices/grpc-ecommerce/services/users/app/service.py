"""Service layer — business rules, transport-agnostic.

This is byte-for-byte the same idea as the REST edition's service layer: it knows
nothing about gRPC (or HTTP). It raises *domain* exceptions; the servicer maps
those to gRPC status codes.
"""
from __future__ import annotations

from .models import User
from .repository import UserRepository
from .security import create_access_token, hash_password, verify_password


class EmailAlreadyExists(Exception):
    """Registering with an email that is already taken."""


class InvalidCredentials(Exception):
    """A login attempt failed."""


class ValidationError(Exception):
    """Input failed a business validation rule."""


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register(self, email: str, full_name: str, password: str) -> User:
        if not email or "@" not in email:
            raise ValidationError("a valid email is required")
        if len(password) < 6:
            raise ValidationError("password must be at least 6 characters")
        if await self._repo.get_by_email(email):
            raise EmailAlreadyExists(email)
        user = User(email=email, full_name=full_name, hashed_password=hash_password(password))
        return await self._repo.add(user)

    async def get(self, user_id: str) -> User | None:
        return await self._repo.get(user_id)

    async def list(self, limit: int = 50, offset: int = 0) -> list[User]:
        return await self._repo.list(limit=limit, offset=offset)

    async def authenticate(self, email: str, password: str) -> str:
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentials(email)
        return create_access_token(subject=user.id)
