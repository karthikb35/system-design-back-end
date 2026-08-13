"""gRPC servicer — the adapter between protobuf and the service layer.

Responsibilities (and *only* these):
  1. Open a database session for the RPC and build the service graph.
  2. Convert the incoming protobuf request into plain arguments.
  3. Call the transport-agnostic service.
  4. Convert the domain result (or exception) back into a protobuf reply
     (or a gRPC status code via ``context.abort``).

Mapping of domain errors to gRPC status codes (the gRPC equivalent of HTTP
status codes):
  EmailAlreadyExists  -> ALREADY_EXISTS
  InvalidCredentials  -> UNAUTHENTICATED
  ValidationError     -> INVALID_ARGUMENT
  not found           -> NOT_FOUND
"""
from __future__ import annotations

import grpc

from .database import SessionLocal
from .pb import users_pb2, users_pb2_grpc
from .repository import UserRepository
from .security import InvalidToken, decode_access_token
from .service import (
    EmailAlreadyExists,
    InvalidCredentials,
    UserService,
    ValidationError,
)


def _to_reply(user) -> users_pb2.UserReply:
    return users_pb2.UserReply(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )


async def _require_auth(context) -> str:
    """Enforce a valid ``Bearer`` JWT on a protected RPC; return the caller id.

    We read the ``authorization`` entry from the call metadata (gRPC lowercases
    header keys), split "Bearer <token>", and verify it with the same secret we
    signed it with. On anything missing or malformed we ``abort`` with
    UNAUTHENTICATED — the gRPC equivalent of HTTP 401.

    Why enforce this *here*, inside the users service? In a real mesh the token
    would typically be verified at the edge (the gateway) or by every service via
    a shared secret or a JWKS endpoint. We verify in the users service because
    that is where the signing secret already lives: the process that mints the
    token at Login can validate it with zero key distribution. The same helper
    can later move behind a server interceptor once other services need it.
    """
    metadata = dict(context.invocation_metadata())
    scheme, _, token = metadata.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "missing bearer token")
    try:
        return decode_access_token(token)
    except InvalidToken:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid or expired token")


class UserServicer(users_pb2_grpc.UserServiceServicer):
    async def CreateUser(self, request, context) -> users_pb2.UserReply:
        async with SessionLocal() as session:
            svc = UserService(UserRepository(session))
            try:
                user = await svc.register(request.email, request.full_name, request.password)
            except ValidationError as exc:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            except EmailAlreadyExists:
                await context.abort(grpc.StatusCode.ALREADY_EXISTS, "email already registered")
            return _to_reply(user)

    async def GetUser(self, request, context) -> users_pb2.UserReply:
        async with SessionLocal() as session:
            svc = UserService(UserRepository(session))
            user = await svc.get(request.id)
            if user is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "user not found")
            return _to_reply(user)

    async def ListUsers(self, request, context) -> users_pb2.ListUsersReply:
        # Listing every user is privileged, so this RPC is authenticated while
        # CreateUser/Login stay public (you must be able to register and log in
        # before you hold a token). GetUser is left public here for the gateway's
        # aggregate path; tighten it the same way if that changes.
        await _require_auth(context)
        async with SessionLocal() as session:
            svc = UserService(UserRepository(session))
            limit = request.limit or 50
            users = await svc.list(limit=limit, offset=request.offset)
            return users_pb2.ListUsersReply(users=[_to_reply(u) for u in users])

    async def Login(self, request, context) -> users_pb2.TokenReply:
        async with SessionLocal() as session:
            svc = UserService(UserRepository(session))
            try:
                token = await svc.authenticate(request.email, request.password)
            except InvalidCredentials:
                await context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid credentials")
            return users_pb2.TokenReply(access_token=token, token_type="bearer")
