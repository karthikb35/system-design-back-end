"""End-to-end tests for the Orders gRPC service against fake dependencies."""
from __future__ import annotations

import grpc
import pytest
from app.pb import orders_pb2


async def _place(stub, user_id="user-1", items=None):
    items = items or [("prod-1", 2)]
    return await stub.PlaceOrder(
        orders_pb2.PlaceOrderRequest(
            user_id=user_id,
            items=[orders_pb2.OrderItemInput(product_id=p, quantity=q) for p, q in items],
        )
    )


async def test_place_order_computes_total_from_snapshot(stub):
    reply = await _place(stub, items=[("prod-1", 2), ("prod-2", 1)])
    # 2 * 4999 + 1 * 2500
    assert reply.total_cents == 12498
    assert reply.status == "confirmed"
    assert len(reply.items) == 2
    assert reply.items[0].unit_price_cents == 4999


async def test_unknown_user_is_failed_precondition(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await _place(stub, user_id="ghost")
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION


async def test_unknown_product_is_failed_precondition(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await _place(stub, items=[("nope", 1)])
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION


async def test_insufficient_stock_is_failed_precondition(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await _place(stub, items=[("prod-2", 5)])  # only 1 in stock
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION


async def test_partial_failure_compensates_reserved_stock(stub, fake_products):
    # prod-1 (stock 10) is reserved first, then prod-2 (stock 1) is oversold at
    # qty 5 -> the checkout fails. The saga must release prod-1 back to 10 (it
    # would remain at 8 without compensation).
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await _place(stub, items=[("prod-1", 2), ("prod-2", 5)])
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    assert fake_products.products["prod-1"][2] == 10  # released back
    assert fake_products.products["prod-2"][2] == 1  # never reserved


async def test_empty_items_is_invalid_argument(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.PlaceOrder(orders_pb2.PlaceOrderRequest(user_id="user-1", items=[]))
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT


async def test_get_order_roundtrips(stub):
    placed = await _place(stub)
    fetched = await stub.GetOrder(orders_pb2.GetOrderRequest(id=placed.id))
    assert fetched.id == placed.id
    assert fetched.total_cents == placed.total_cents


async def test_get_unknown_order_is_not_found(stub):
    with pytest.raises(grpc.aio.AioRpcError) as exc:
        await stub.GetOrder(orders_pb2.GetOrderRequest(id="missing"))
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND


async def test_list_orders_for_user(stub):
    await _place(stub)
    await _place(stub)
    reply = await stub.ListOrders(orders_pb2.ListOrdersRequest(user_id="user-1"))
    assert len(reply.orders) == 2
