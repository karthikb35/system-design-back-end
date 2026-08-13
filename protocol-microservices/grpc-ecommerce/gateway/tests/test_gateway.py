"""HTTP-level tests for the Gateway driving fake gRPC backends."""
from __future__ import annotations


async def test_health_is_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_readiness_fans_out(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dependencies"] == {"users": "serving", "products": "serving", "orders": "serving"}


async def test_get_user_translates_grpc_to_json(client):
    resp = await client.get("/users/user-1")
    assert resp.status_code == 200
    assert resp.json()["email"] == "buyer@example.com"


async def test_unknown_user_maps_not_found_to_404(client):
    resp = await client.get("/users/ghost")
    assert resp.status_code == 404


async def test_create_user_roundtrips(client):
    resp = await client.post("/users", json={"email": "n@e.com", "full_name": "New", "password": "pw"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "n@e.com"


async def test_place_order_and_get(client):
    placed = await client.post(
        "/orders",
        json={"user_id": "user-1", "items": [{"product_id": "prod-1", "quantity": 2}]},
    )
    assert placed.status_code == 200
    oid = placed.json()["id"]
    assert placed.json()["total_cents"] == 9998

    fetched = await client.get(f"/orders/{oid}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == oid


async def test_aggregate_enriches_order(client):
    placed = await client.post(
        "/orders",
        json={"user_id": "user-1", "items": [{"product_id": "prod-1", "quantity": 1}]},
    )
    oid = placed.json()["id"]
    resp = await client.get(f"/aggregate/orders/{oid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["buyer_name"] == "Buyer One"
    assert body["items"][0]["product_name"] == "Keyboard"
