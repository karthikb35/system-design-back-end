"""GraphQL schema — the transport adapter for the Users service.

This is the GraphQL equivalent of the REST edition's routers or the gRPC
edition's servicer. Strawberry types describe what the schema exposes; the
resolvers open a DB session, call the service layer, and translate domain
exceptions into ``GraphQLError``s (which appear in the response's ``errors``).
"""
from __future__ import annotations

import strawberry
from graphql import GraphQLError
from strawberry.types import Info

from .database import SessionLocal
from .models import User as UserModel
from .repository import UserRepository
from .security import InvalidToken, decode_access_token
from .service import (
    EmailAlreadyExists,
    InvalidCredentials,
    UserNotFound,
    UserService,
    ValidationError,
)


@strawberry.type(description="A registered user. Never exposes the password hash.")
class User:
    id: strawberry.ID
    email: str
    full_name: str
    is_active: bool

    @classmethod
    def from_model(cls, m: UserModel) -> User:
        return cls(id=strawberry.ID(m.id), email=m.email, full_name=m.full_name, is_active=m.is_active)


@strawberry.type(description="A signed JWT access token.")
class AuthToken:
    access_token: str
    token_type: str = "bearer"


def _service(session) -> UserService:
    return UserService(UserRepository(session))


def _require_auth(info: Info) -> str:
    """Enforce a valid ``Authorization: Bearer <jwt>`` header, returning the sub.

    We verify the token *inside the users service* because this is where the
    signing secret lives. In a real service mesh the gateway (or every peer
    service) would independently verify the same token via a shared secret or a
    JWKS endpoint, so the signer and the verifiers stay decoupled; here we keep
    it single-service so the secret never leaves the process that owns it.

    The request is reachable through ``info.context`` because ``main.py`` wires a
    ``context_getter`` that drops the FastAPI ``Request`` into the GraphQL
    context. Any failure surfaces as a ``GraphQLError`` in ``errors[]`` (the
    HTTP status stays 200, per GraphQL semantics).
    """
    request = info.context["request"]
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise GraphQLError("authentication required")
    try:
        return decode_access_token(token)
    except InvalidToken:
        raise GraphQLError("invalid or expired token")


@strawberry.type
class Query:
    @strawberry.field(description="Fetch a single user by id.")
    async def user(self, id: strawberry.ID) -> User:
        async with SessionLocal() as session:
            try:
                return User.from_model(await _service(session).get(str(id)))
            except UserNotFound:
                raise GraphQLError("user not found")

    @strawberry.field(description="List users (paginated). Requires a valid bearer token.")
    async def users(self, info: Info, limit: int = 50, offset: int = 0) -> list[User]:
        # Listing every user is a privileged operation, so unlike the single
        # `user(id)` lookup and the public createUser/login mutations it demands
        # authentication. `info` is injected by Strawberry, not exposed as a
        # GraphQL argument.
        _require_auth(info)
        async with SessionLocal() as session:
            rows = await _service(session).list(limit=limit, offset=offset)
            return [User.from_model(u) for u in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Register a new user.")
    async def create_user(self, email: str, password: str, full_name: str = "") -> User:
        async with SessionLocal() as session:
            try:
                user = await _service(session).register(email, full_name, password)
            except ValidationError as exc:
                raise GraphQLError(str(exc))
            except EmailAlreadyExists:
                raise GraphQLError("email already registered")
            return User.from_model(user)

    @strawberry.mutation(description="Exchange credentials for an access token.")
    async def login(self, email: str, password: str) -> AuthToken:
        async with SessionLocal() as session:
            try:
                token = await _service(session).login(email, password)
            except InvalidCredentials:
                raise GraphQLError("invalid credentials")
            return AuthToken(access_token=token)


schema = strawberry.Schema(query=Query, mutation=Mutation)
