"""Gateway tests — proxying, aggregation, and fan-out health."""
from __future__ import annotations


async def test_live(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


async def test_ready_fans_out(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["services"] == {"users": "ready", "products": "ready", "orders": "ready"}


async def test_proxy_users_passthrough(client):
    resp = await client.get("/api/users/user-1")
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Ada Lovelace"


async def test_proxy_unknown_user_forwards_404(client):
    resp = await client.get("/api/users/ghost")
    assert resp.status_code == 404


async def test_proxy_products_passthrough(client):
    resp = await client.get("/api/products/prod-1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Widget"


async def test_aggregate_order_summary(client):
    resp = await client.get("/aggregate/orders/order-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == "order-1"
    assert body["buyer_name"] == "Ada Lovelace"       # enriched from Users
    assert body["items"][0]["name"] == "Widget"       # enriched from Products
    assert body["total_cents"] == 2000
