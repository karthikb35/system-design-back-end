"""GraphQL-level tests for the Products service."""
from __future__ import annotations

from tests.conftest import gql

CREATE = """
mutation ($sku: String!, $name: String!, $price: Int!, $stock: Int!) {
  createProduct(sku: $sku, name: $name, priceCents: $price, stock: $stock) {
    id sku name priceCents stock
  }
}
"""

GET = """query ($id: ID!) { product(id: $id) { id sku stock } }"""

RESERVE = """
mutation ($id: ID!, $qty: Int!) {
  reserveStock(id: $id, quantity: $qty) { id stock }
}
"""

RELEASE = """
mutation ($id: ID!, $qty: Int!) {
  releaseStock(id: $id, quantity: $qty) { id stock }
}
"""


async def _create(client, sku="KB1", name="Keyboard", price=4999, stock=10):
    return await gql(client, CREATE, {"sku": sku, "name": name, "price": price, "stock": stock})


async def test_create_product(client):
    body = await _create(client)
    p = body["data"]["createProduct"]
    assert p["sku"] == "KB1"
    assert p["priceCents"] == 4999
    assert p["stock"] == 10


async def test_duplicate_sku_is_error(client):
    await _create(client)
    body = await _create(client)
    assert body["data"] is None
    assert "sku already exists" in body["errors"][0]["message"]


async def test_negative_price_is_validation_error(client):
    body = await _create(client, price=-1)
    assert body["data"] is None
    assert "non-negative" in body["errors"][0]["message"]


async def test_get_unknown_product_is_error(client):
    body = await gql(client, GET, {"id": "missing"})
    assert body["data"] is None
    assert "not found" in body["errors"][0]["message"]


async def test_reserve_decrements_stock(client):
    created = await _create(client, stock=5)
    pid = created["data"]["createProduct"]["id"]
    body = await gql(client, RESERVE, {"id": pid, "qty": 3})
    assert body["data"]["reserveStock"]["stock"] == 2


async def test_release_increments_stock(client):
    # Release is the compensating action the Orders saga calls to undo a
    # reservation: it adds the units back.
    created = await _create(client, stock=5)
    pid = created["data"]["createProduct"]["id"]
    assert (await gql(client, RESERVE, {"id": pid, "qty": 3}))["data"]["reserveStock"]["stock"] == 2
    body = await gql(client, RELEASE, {"id": pid, "qty": 3})
    assert body["data"]["releaseStock"]["stock"] == 5  # back to the original


async def test_reserve_more_than_stock_is_error(client):
    created = await _create(client, stock=2)
    pid = created["data"]["createProduct"]["id"]
    body = await gql(client, RESERVE, {"id": pid, "qty": 5})
    assert body["data"] is None
    assert "in stock" in body["errors"][0]["message"]


async def test_reserve_zero_is_validation_error(client):
    created = await _create(client)
    pid = created["data"]["createProduct"]["id"]
    body = await gql(client, RESERVE, {"id": pid, "qty": 0})
    assert body["data"] is None
    assert "positive" in body["errors"][0]["message"]


async def test_reserve_unknown_product_is_error(client):
    body = await gql(client, RESERVE, {"id": "missing", "qty": 1})
    assert body["data"] is None
    assert "not found" in body["errors"][0]["message"]
