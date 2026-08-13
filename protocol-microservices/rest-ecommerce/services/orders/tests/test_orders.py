"""End-to-end tests for the Orders service with faked downstream clients."""
from __future__ import annotations


async def test_health_live(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200


async def test_place_order_happy_path(client):
    resp = await client.post(
        "/orders",
        json={
            "user_id": "user-1",
            "items": [
                {"product_id": "prod-1", "quantity": 2},  # 2 x 1000
                {"product_id": "prod-2", "quantity": 1},  # 1 x 2500
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["total_cents"] == 2 * 1000 + 2500  # 4500
    assert len(body["items"]) == 2


async def test_place_order_unknown_user_422(client):
    resp = await client.post(
        "/orders",
        json={"user_id": "ghost", "items": [{"product_id": "prod-1", "quantity": 1}]},
    )
    assert resp.status_code == 422


async def test_place_order_insufficient_stock_409(client):
    resp = await client.post(
        "/orders",
        json={"user_id": "user-1", "items": [{"product_id": "prod-2", "quantity": 99}]},
    )
    assert resp.status_code == 409


async def test_place_order_unknown_product_409(client):
    resp = await client.post(
        "/orders",
        json={"user_id": "user-1", "items": [{"product_id": "nope", "quantity": 1}]},
    )
    assert resp.status_code == 409


async def test_place_order_compensates_reserved_stock_on_partial_failure(client, catalog):
    # prod-1 (stock 5) is reserved first, then prod-2 (stock 2) is oversold at
    # qty 99 -> the whole checkout fails with 409. The saga must release prod-1's
    # reservation so its stock returns to 5 (it would be 3 without compensation).
    resp = await client.post(
        "/orders",
        json={
            "user_id": "user-1",
            "items": [
                {"product_id": "prod-1", "quantity": 2},
                {"product_id": "prod-2", "quantity": 99},
            ],
        },
    )
    assert resp.status_code == 409
    assert catalog["prod-1"]["stock"] == 5  # released back by compensation
    assert catalog["prod-2"]["stock"] == 2  # never successfully reserved


async def test_get_and_list_orders(client):
    created = await client.post(
        "/orders",
        json={"user_id": "user-1", "items": [{"product_id": "prod-1", "quantity": 1}]},
    )
    oid = created.json()["id"]

    got = await client.get(f"/orders/{oid}")
    assert got.status_code == 200
    assert got.json()["id"] == oid

    listed = await client.get("/orders", params={"user_id": "user-1"})
    assert listed.status_code == 200
    assert any(o["id"] == oid for o in listed.json())


async def test_get_unknown_order_404(client):
    resp = await client.get("/orders/does-not-exist")
    assert resp.status_code == 404


async def test_empty_items_rejected_by_validation(client):
    resp = await client.post("/orders", json={"user_id": "user-1", "items": []})
    assert resp.status_code == 422
