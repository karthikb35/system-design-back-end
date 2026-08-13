"""Orders HTTP endpoints — thin routing layer.

The service and its two downstream clients are assembled per request via
dependency injection, so tests can swap the clients for fakes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients import DownstreamError, ProductsClient, ProductUnavailable, UsersClient
from ..database import get_session
from ..dependencies import get_products_client, get_users_client
from ..repository import OrderRepository
from ..schemas import OrderCreate, OrderOut
from ..service import OrderNotFound, OrderService, UserNotFound

router = APIRouter(prefix="/orders", tags=["orders"])


def _service(
    session: AsyncSession = Depends(get_session),
    users: UsersClient = Depends(get_users_client),
    products: ProductsClient = Depends(get_products_client),
) -> OrderService:
    return OrderService(OrderRepository(session), users, products)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_order(payload: OrderCreate, svc: OrderService = Depends(_service)) -> OrderOut:
    try:
        order = await svc.place_order(payload)
    except UserNotFound:
        raise HTTPException(422, detail="buyer does not exist")
    except ProductUnavailable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.detail)
    except DownstreamError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="downstream service unavailable")
    return OrderOut.model_validate(order)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: str, svc: OrderService = Depends(_service)) -> OrderOut:
    try:
        order = await svc.get(order_id)
    except OrderNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="order not found")
    return OrderOut.model_validate(order)


@router.get("", response_model=list[OrderOut])
async def list_orders(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    svc: OrderService = Depends(_service),
) -> list[OrderOut]:
    orders = await svc.list_for_user(user_id, limit=limit, offset=offset)
    return [OrderOut.model_validate(o) for o in orders]
