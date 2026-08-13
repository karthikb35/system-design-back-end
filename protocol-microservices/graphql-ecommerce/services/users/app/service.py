"""Service layer — business rules, transport-agnostic.

Knows nothing about GraphQL. Raises plain domain exceptions; the schema layer
turns those into GraphQL errors.
"""
from __future__ import annotations

import re

from .models import User
from .repository import UserRepository
from .security import create_access_token, hash_password, verify_password

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    """Input failed a business validation rule."""


class EmailAlreadyExists(Exception):
    """A user with this email already exists."""


class UserNotFound(Exception):
    """No user with the given id."""


class InvalidCredentials(Exception):
    """Email/password did not match."""


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register(self, email: str, full_name: str, password: str) -> User:
        if not _EMAIL_RE.match(email or ""):
            raise ValidationError("a valid email is required")
        if len(password or "") < 8:
            raise ValidationError("password must be at least 8 characters")
        if await self._repo.get_by_email(email) is not None:
            raise EmailAlreadyExists(email)
        user = User(email=email, full_name=full_name or "", hashed_password=hash_password(password))
        return await self._repo.add(user)

    async def get(self, user_id: str) -> User:
        user = await self._repo.get(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    async def list(self, limit: int = 50, offset: int = 0) -> list[User]:
        return await self._repo.list(limit=limit, offset=offset)

    async def login(self, email: str, password: str) -> str:
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentials()
        return create_access_token(user.id)
