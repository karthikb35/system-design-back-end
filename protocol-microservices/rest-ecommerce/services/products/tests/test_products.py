"""End-to-end HTTP tests for the Products service (in-process, in-memory DB)."""
from __future__ import annotations


async def _make(client, sku="SKU-1", stock=10, price=1999):
    resp = await client.post(
        "/products",
        json={"sku": sku, "name": "Widget", "description": "a widget", "price_cents": price, "stock": stock},
    )
    return resp


async def test_health_live(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


async def test_create_and_get_product(client):
    created = await _make(client)
    assert created.status_code == 201
    body = created.json()
    assert body["sku"] == "SKU-1"
    assert body["stock"] == 10

    got = await client.get(f"/products/{body['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]


async def test_duplicate_sku_conflicts(client):
    assert (await _make(client, sku="DUP")).status_code == 201
    assert (await _make(client, sku="DUP")).status_code == 409


async def test_reserve_stock_decrements(client):
    pid = (await _make(client, sku="RES", stock=5)).json()["id"]
    resp = await client.post(f"/products/{pid}/reserve", json={"quantity": 3})
    assert resp.status_code == 200
    assert resp.json()["stock"] == 2


async def test_reserve_more_than_stock_conflicts(client):
    pid = (await _make(client, sku="LOW", stock=1)).json()["id"]
    resp = await client.post(f"/products/{pid}/reserve", json={"quantity": 2})
    assert resp.status_code == 409


async def test_reserve_unknown_product_404(client):
    resp = await client.post("/products/does-not-exist/reserve", json={"quantity": 1})
    assert resp.status_code == 404


async def test_release_stock_increments(client):
    # Release is the compensating action the Orders saga calls to undo a
    # reservation: it adds the units back to stock.
    pid = (await _make(client, sku="REL", stock=5)).json()["id"]
    assert (await client.post(f"/products/{pid}/reserve", json={"quantity": 3})).json()["stock"] == 2
    released = await client.post(f"/products/{pid}/release", json={"quantity": 3})
    assert released.status_code == 200
    assert released.json()["stock"] == 5  # back to the original


async def test_negative_price_rejected_by_validation(client):
    resp = await client.post(
        "/products",
        json={"sku": "BAD", "name": "X", "price_cents": -1, "stock": 0},
    )
    assert resp.status_code == 422


async def test_cursor_pagination_covers_all_without_overlap(client):
    # Seed a known set of products to page through.
    created_ids = set()
    for i in range(5):
        r = await _make(client, sku=f"PAGE-{i}")
        assert r.status_code == 201
        created_ids.add(r.json()["id"])

    # Walk the collection two-at-a-time via the cursor until it is exhausted.
    # The empty cursor bootstraps the walk from the start of the collection.
    seen: list[str] = []
    cursor = ""
    while True:
        resp = await client.get("/products", params={"limit": 2, "cursor": cursor})
        assert resp.status_code == 200
        body = resp.json()
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:  # null cursor signals the end of the collection
            break

    # Keyset guarantees: every row is visited at most once (no overlap between
    # pages) and all of the products we created are covered by the walk. Other
    # tests share the in-memory DB, so we assert coverage as a subset rather than
    # strict equality with the whole table.
    assert len(seen) == len(set(seen))          # no row appeared on two pages
    assert created_ids <= set(seen)             # every seeded product was returned
