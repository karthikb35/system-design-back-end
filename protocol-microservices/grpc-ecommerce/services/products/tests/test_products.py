"""End-to-end gRPC tests for the Products service (real server, in-memory DB)."""
from __future__ import annotations

import grpc
import pytest
from app.pb import products_pb2


async def _make(stub, sku="SKU-1", stock=10, price=1999):
    return await stub.CreateProduct(
        products_pb2.CreateProductRequest(
            sku=sku, name="Widget", description="a widget", price_cents=price, stock=stock
        )
    )


async def test_create_and_get(stub):
    created = await _make(stub)
    assert created.sku == "SKU-1"
    assert created.stock == 10
    got = await stub.GetProduct(products_pb2.GetProductRequest(id=created.id))
    assert got.id == created.id


async def test_get_unknown_not_found(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.GetProduct(products_pb2.GetProductRequest(id="nope"))
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND


async def test_duplicate_sku_already_exists(stub):
    await _make(stub, sku="DUP")
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await _make(stub, sku="DUP")
    assert exc.value.code() == grpc.StatusCode.ALREADY_EXISTS


async def test_reserve_decrements(stub):
    created = await _make(stub, sku="RES", stock=5)
    reply = await stub.ReserveStock(products_pb2.ReserveStockRequest(id=created.id, quantity=3))
    assert reply.stock == 2


async def test_reserve_insufficient_failed_precondition(stub):
    created = await _make(stub, sku="LOW", stock=1)
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.ReserveStock(products_pb2.ReserveStockRequest(id=created.id, quantity=2))
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION


async def test_reserve_unknown_not_found(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.ReserveStock(products_pb2.ReserveStockRequest(id="nope", quantity=1))
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND


async def test_release_increments(stub):
    # Release is the compensating action the Orders saga calls to undo a
    # reservation: it adds the units back.
    created = await _make(stub, sku="REL", stock=5)
    reserved = await stub.ReserveStock(products_pb2.ReserveStockRequest(id=created.id, quantity=3))
    assert reserved.stock == 2
    released = await stub.ReleaseStock(products_pb2.ReleaseStockRequest(id=created.id, quantity=3))
    assert released.stock == 5  # back to the original


async def test_negative_price_invalid_argument(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.CreateProduct(
            products_pb2.CreateProductRequest(sku="BAD", name="X", price_cents=-1, stock=0)
        )
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT


async def test_list(stub):
    for i in range(3):
        await _make(stub, sku=f"S{i}")
    reply = await stub.ListProducts(products_pb2.ListProductsRequest(limit=10, offset=0))
    assert len(reply.products) == 3


async def test_keyset_pagination_walks_all_items_without_overlap(service):
    # Seed a catalog, then page through it with the keyset method directly.
    created_ids = []
    for i in range(5):
        product = await service.create(
            sku=f"K{i}", name=f"Keyset {i}", description="", price_cents=100 + i, stock=1
        )
        created_ids.append(product.id)

    seen: list[str] = []
    cursor: str | None = None
    while True:
        items, cursor = await service.list_keyset(cursor_id=cursor, limit=2)
        seen.extend(p.id for p in items)
        if cursor is None:
            break

    # Every id shows up exactly once (no gaps, no overlap) and the walk
    # terminates with next_cursor == None once the catalog is exhausted.
    assert cursor is None
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == set(created_ids)
