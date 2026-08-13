"""GraphQL-level tests for the Users service."""
from __future__ import annotations

from tests.conftest import gql

CREATE = """
mutation ($email: String!, $password: String!, $fullName: String!) {
  createUser(email: $email, password: $password, fullName: $fullName) {
    id email fullName isActive
  }
}
"""

GET = """
query ($id: ID!) { user(id: $id) { id email fullName } }
"""

LOGIN = """
mutation ($email: String!, $password: String!) {
  login(email: $email, password: $password) { accessToken tokenType }
}
"""

LIST_USERS = """
query { users { id email fullName } }
"""


async def _create(client, email="a@b.com", password="password1", full_name="Ann"):
    return await gql(client, CREATE, {"email": email, "password": password, "fullName": full_name})


async def _token(client, email="a@b.com", password="password1"):
    """Mint a real signed token by going through the login mutation."""
    await _create(client, email=email, password=password)
    body = await gql(client, LOGIN, {"email": email, "password": password})
    return body["data"]["login"]["accessToken"]


async def test_create_user_returns_user_without_password(client):
    body = await _create(client)
    user = body["data"]["createUser"]
    assert user["email"] == "a@b.com"
    assert user["isActive"] is True
    assert "password" not in user


async def test_duplicate_email_is_error(client):
    await _create(client)
    body = await _create(client)
    assert body["data"] is None
    assert "already registered" in body["errors"][0]["message"]


async def test_invalid_email_is_validation_error(client):
    body = await _create(client, email="not-an-email")
    assert body["data"] is None
    assert "valid email" in body["errors"][0]["message"]


async def test_short_password_is_validation_error(client):
    body = await _create(client, password="short")
    assert body["data"] is None
    assert "at least 8" in body["errors"][0]["message"]


async def test_get_user_roundtrips(client):
    created = await _create(client)
    uid = created["data"]["createUser"]["id"]
    body = await gql(client, GET, {"id": uid})
    assert body["data"]["user"]["email"] == "a@b.com"


async def test_get_unknown_user_is_error(client):
    body = await gql(client, GET, {"id": "missing"})
    assert body["data"] is None
    assert "not found" in body["errors"][0]["message"]


async def test_login_success_and_failure(client):
    await _create(client)
    ok = await gql(client, LOGIN, {"email": "a@b.com", "password": "password1"})
    assert ok["data"]["login"]["accessToken"]
    assert ok["data"]["login"]["tokenType"] == "bearer"

    bad = await gql(client, LOGIN, {"email": "a@b.com", "password": "wrong"})
    assert bad["data"] is None
    assert "invalid credentials" in bad["errors"][0]["message"]


async def test_users_list_requires_auth(client):
    # No Authorization header at all: the protected list must refuse and surface
    # the failure in errors[] (data.users null), not as an HTTP status.
    await _create(client)
    body = await gql(client, LIST_USERS)
    assert body["data"] is None
    assert "authentication required" in body["errors"][0]["message"]


async def test_users_list_with_valid_token_returns_users(client):
    token = await _token(client)
    body = await gql(client, LIST_USERS, headers={"Authorization": f"Bearer {token}"})
    assert body.get("errors") is None
    emails = [u["email"] for u in body["data"]["users"]]
    assert "a@b.com" in emails


async def test_users_list_with_garbage_token_is_error(client):
    await _create(client)
    body = await gql(client, LIST_USERS, headers={"Authorization": "Bearer not-a-real-jwt"})
    assert body["data"] is None
    assert "invalid or expired token" in body["errors"][0]["message"]
