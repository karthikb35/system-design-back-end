"""End-to-end gRPC tests for the Users service (real server, in-memory DB)."""
from __future__ import annotations

import grpc
import pytest

from app.pb import users_pb2


async def test_create_and_get_user(stub):
    created = await stub.CreateUser(
        users_pb2.CreateUserRequest(email="ada@example.com", full_name="Ada", password="s3cret!")
    )
    assert created.email == "ada@example.com"
    assert created.id

    got = await stub.GetUser(users_pb2.GetUserRequest(id=created.id))
    assert got.id == created.id


async def test_get_unknown_user_not_found(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.GetUser(users_pb2.GetUserRequest(id="nope"))
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND


async def test_duplicate_email_already_exists(stub):
    req = users_pb2.CreateUserRequest(email="dup@example.com", full_name="Dup", password="s3cret!")
    await stub.CreateUser(req)
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.CreateUser(req)
    assert exc.value.code() == grpc.StatusCode.ALREADY_EXISTS


async def test_short_password_invalid_argument(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.CreateUser(
            users_pb2.CreateUserRequest(email="x@example.com", full_name="X", password="123")
        )
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT


async def test_login_success_and_failure(stub):
    await stub.CreateUser(
        users_pb2.CreateUserRequest(email="log@example.com", full_name="Log", password="s3cret!")
    )
    ok = await stub.Login(users_pb2.LoginRequest(email="log@example.com", password="s3cret!"))
    assert ok.token_type == "bearer"
    assert ok.access_token

    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.Login(users_pb2.LoginRequest(email="log@example.com", password="wrong"))
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_list_users(stub):
    for i in range(3):
        await stub.CreateUser(
            users_pb2.CreateUserRequest(email=f"u{i}@example.com", full_name=f"U{i}", password="s3cret!")
        )
    # ListUsers is now authenticated, so mint a real token via the login flow.
    token = (
        await stub.Login(users_pb2.LoginRequest(email="u0@example.com", password="s3cret!"))
    ).access_token
    reply = await stub.ListUsers(
        users_pb2.ListUsersRequest(limit=10, offset=0),
        metadata=[("authorization", f"Bearer {token}")],
    )
    assert len(reply.users) == 3


async def test_list_users_without_auth_is_unauthenticated(stub):
    # No authorization metadata at all -> the RPC must be rejected.
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.ListUsers(users_pb2.ListUsersRequest(limit=10, offset=0))
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_list_users_with_valid_bearer_token_succeeds(stub):
    await stub.CreateUser(
        users_pb2.CreateUserRequest(email="auth@example.com", full_name="Auth", password="s3cret!")
    )
    token = (
        await stub.Login(users_pb2.LoginRequest(email="auth@example.com", password="s3cret!"))
    ).access_token
    reply = await stub.ListUsers(
        users_pb2.ListUsersRequest(limit=10, offset=0),
        metadata=[("authorization", f"Bearer {token}")],
    )
    assert len(reply.users) == 1


async def test_list_users_with_garbage_token_is_unauthenticated(stub):
    # A well-formed "Bearer <x>" header whose token fails signature verification.
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.ListUsers(
            users_pb2.ListUsersRequest(limit=10, offset=0),
            metadata=[("authorization", "Bearer not-a-real-token")],
        )
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED
