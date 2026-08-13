"""GraphQL-level tests for the Orders service against fake dependencies."""
from __future__ import annotations

from tests.conftest import gql

PLACE = """
mutation ($userId: ID!, $items: [OrderItemInput!]!) {
  placeOrder(userId: $userId, items: $items) {
    id userId status totalCents
    items { productId quantity unitPriceCents }
  }
}
"""

GET = """query ($id: ID!) { order(id: $id) { id totalCents } }"""

LIST = """query ($userId: ID!) { orders(userId: $userId) { id } }"""


_DEFAULT = object()


async def _place(client, user_id="user-1", items=_DEFAULT):
    if items is _DEFAULT:
        items = [{"productId": "prod-1", "quantity": 2}]
    return await gql(client, PLACE, {"userId": user_id, "items": items})


async def test_place_order_computes_total_from_snapshot(client):
    body = await _place(client, items=[{"productId": "prod-1", "quantity": 2}, {"productId": "prod-2", "quantity": 1}])
    order = body["data"]["placeOrder"]
    assert order["totalCents"] == 12498  # 2*4999 + 1*2500
    assert order["status"] == "confirmed"
    assert len(order["items"]) == 2
    assert order["items"][0]["unitPriceCents"] == 4999


async def test_unknown_user_is_error(client):
    body = await _place(client, user_id="ghost")
    assert body["data"] is None
    assert "buyer does not exist" in body["errors"][0]["message"]


async def test_unknown_product_is_error(client):
    body = await _place(client, items=[{"productId": "nope", "quantity": 1}])
    assert body["data"] is None
    assert "not found" in body["errors"][0]["message"]


async def test_insufficient_stock_is_error(client):
    body = await _place(client, items=[{"productId": "prod-2", "quantity": 5}])
    assert body["data"] is None
    assert "in stock" in body["errors"][0]["message"]


async def test_partial_failure_compensates_reserved_stock(client, products_state):
    # prod-1 (stock 10) is reserved first, then prod-2 (stock 1) is oversold at
    # qty 5 -> the checkout fails. The saga must release prod-1 back to 10 (it
    # would remain at 8 without compensation).
    body = await _place(
        client,
        items=[{"productId": "prod-1", "quantity": 2}, {"productId": "prod-2", "quantity": 5}],
    )
    assert body["data"] is None
    assert "in stock" in body["errors"][0]["message"]
    assert products_state["prod-1"]["stock"] == 10  # released back
    assert products_state["prod-2"]["stock"] == 1  # never reserved


async def test_empty_items_is_validation_error(client):
    body = await _place(client, items=[])
    assert body["data"] is None
    assert "at least one item" in body["errors"][0]["message"]


async def test_get_order_roundtrips(client):
    placed = await _place(client)
    oid = placed["data"]["placeOrder"]["id"]
    body = await gql(client, GET, {"id": oid})
    assert body["data"]["order"]["id"] == oid


async def test_get_unknown_order_is_error(client):
    body = await gql(client, GET, {"id": "missing"})
    assert body["data"] is None
    assert "order not found" in body["errors"][0]["message"]


async def test_list_orders_for_user(client):
    await _place(client, items=[{"productId": "prod-1", "quantity": 1}])
    await _place(client, items=[{"productId": "prod-1", "quantity": 1}])
    body = await gql(client, LIST, {"userId": "user-1"})
    assert len(body["data"]["orders"]) == 2
