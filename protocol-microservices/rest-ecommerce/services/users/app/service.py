"""Service layer — business rules and use-cases.

Sits between the HTTP routers and the repository. Routers stay thin (parse +
delegate); the database stays behind the repository; the rules live here.
Errors are raised as domain exceptions and translated to HTTP by the router.
"""
from __future__ import annotations

from .models import User
from .repository import UserRepository
from .schemas import UserCreate
from .security import create_access_token, hash_password, verify_password


class EmailAlreadyExists(Exception):
    """Raised when registering with an email that is already taken."""


class InvalidCredentials(Exception):
    """Raised when a login attempt fails."""


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register(self, data: UserCreate) -> User:
        if await self._repo.get_by_email(data.email):
            raise EmailAlreadyExists(data.email)
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
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
