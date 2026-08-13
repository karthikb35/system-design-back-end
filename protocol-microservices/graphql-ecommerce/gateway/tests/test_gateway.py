"""Tests for the unified Gateway graph, including cross-service field resolution."""
from __future__ import annotations

from tests.conftest import gql


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_query_user_via_gateway(client):
    body = await gql(client, 'query { user(id: "user-1") { email fullName } }')
    assert body["data"]["user"]["email"] == "buyer@example.com"


async def test_unknown_user_returns_null(client):
    body = await gql(client, 'query { user(id: "ghost") { email } }')
    assert body["data"]["user"] is None


async def test_place_order_via_gateway(client):
    order = await gql(
        client,
        """mutation ($u: ID!, $items: [OrderItemInput!]!) {
             placeOrder(userId: $u, items: $items) { id totalCents }
           }""",
        {"u": "user-1", "items": [{"productId": "prod-1", "quantity": 2}]},
    )
    assert order["data"]["placeOrder"]["totalCents"] == 9998


async def test_order_composes_buyer_and_product_in_one_query(client):
    placed = await gql(
        client,
        """mutation ($u: ID!, $items: [OrderItemInput!]!) {
             placeOrder(userId: $u, items: $items) { id }
           }""",
        {"u": "user-1", "items": [{"productId": "prod-1", "quantity": 1}]},
    )
    oid = placed["data"]["placeOrder"]["id"]

    # The whole point of the GraphQL gateway: one nested query fans out to 3 services.
    body = await gql(
        client,
        """query ($id: ID!) {
             order(id: $id) {
               totalCents
               buyer { fullName }
               items { quantity product { name } }
             }
           }""",
        {"id": oid},
    )
    data = body["data"]["order"]
    assert data["buyer"]["fullName"] == "Buyer One"
    assert data["items"][0]["product"]["name"] == "Keyboard"


async def test_unknown_order_is_error(client):
    body = await gql(client, 'query { order(id: "missing") { id } }')
    assert body["data"] is None
    assert "order not found" in body["errors"][0]["message"]


async def test_dataloader_batches_and_dedupes_stitching(counting_client):
    # The headline GraphQL gap: without a DataLoader, a nested query over N
    # orders fires one buyer + one product backend call PER row (N+1). With the
    # request-scoped DataLoader those loads batch and dedupe by id.
    client, counting = counting_client

    PLACE = """mutation ($u: ID!, $items: [OrderItemInput!]!) {
      placeOrder(userId: $u, items: $items) { id }
    }"""
    # Four orders for the SAME buyer, alternating between two products. Placing
    # them only selects `id`, so no stitching happens during setup — the counters
    # stay empty until the nested query below.
    for pid in ("prod-1", "prod-2", "prod-1", "prod-2"):
        await gql(client, PLACE, {"u": "user-1", "items": [{"productId": pid, "quantity": 1}]})

    body = await gql(
        client,
        """query {
             orders(userId: "user-1") {
               id
               buyer { fullName }
               items { product { name } }
             }
           }""",
    )
    orders = body["data"]["orders"]
    assert len(orders) == 4
    # Stitched data is still fully correct across all four rows...
    assert {o["buyer"]["fullName"] for o in orders} == {"Buyer One"}
    assert {i["product"]["name"] for o in orders for i in o["items"]} == {"Keyboard", "Mouse"}

    # ...but the DataLoader collapsed the fan-out to ONE backend call per DISTINCT
    # id: 4 buyer loads -> 1 users call, 4 product loads -> 2 products calls.
    assert counting.user_calls == ["user-1"]
    assert sorted(counting.product_calls) == ["prod-1", "prod-2"]
    # Both are strictly fewer than the 4 rows we queried over (no N+1).
    assert len(counting.user_calls) < 4
    assert len(counting.product_calls) < 4
