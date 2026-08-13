"""End-to-end HTTP tests for the Users service (in-process, in-memory DB)."""
from __future__ import annotations

import pytest


async def test_health_live(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


async def test_create_and_get_user(client):
    resp = await client.post(
        "/users",
        json={"email": "ada@example.com", "full_name": "Ada Lovelace", "password": "s3cret!"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "ada@example.com"
    assert "password" not in body and "hashed_password" not in body  # never leaked

    got = await client.get(f"/users/{body['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]


async def test_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "full_name": "Dup", "password": "s3cret!"}
    assert (await client.post("/users", json=payload)).status_code == 201
    second = await client.post("/users", json=payload)
    assert second.status_code == 409


async def test_login_returns_token(client):
    await client.post(
        "/users",
        json={"email": "log@example.com", "full_name": "Log In", "password": "s3cret!"},
    )
    ok = await client.post("/users/login", json={"email": "log@example.com", "password": "s3cret!"})
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"
    assert ok.json()["access_token"]

    bad = await client.post("/users/login", json={"email": "log@example.com", "password": "wrong"})
    assert bad.status_code == 401


async def test_invalid_email_is_rejected_by_validation(client):
    resp = await client.post(
        "/users",
        json={"email": "not-an-email", "full_name": "X", "password": "s3cret!"},
    )
    assert resp.status_code == 422  # Pydantic validation at the boundary


async def _register_and_login(client, email="auth@example.com", password="s3cret!") -> str:
    """Register a user and return a valid Bearer token for them."""
    await client.post(
        "/users",
        json={"email": email, "full_name": "Auth User", "password": password},
    )
    resp = await client.post("/users/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def test_list_users_requires_auth(client):
    # Without a token the privileged roster listing must be refused.
    unauth = await client.get("/users")
    assert unauth.status_code == 401

    # With a valid Bearer token it succeeds.
    token = await _register_and_login(client, email="list@example.com")
    ok = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)


async def test_me_returns_the_authenticated_user(client):
    token = await _register_and_login(client, email="me@example.com")
    resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


async def test_garbage_and_missing_tokens_are_rejected(client):
    # A structurally-invalid / tampered token fails signature verification -> 401.
    tampered = await client.get(
        "/users", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert tampered.status_code == 401

    # A missing Authorization header on a protected route is also 401.
    assert (await client.get("/users/me")).status_code == 401
