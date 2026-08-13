"""Products HTTP endpoints — thin routing layer.

The `reserve` endpoint is the one the Orders service calls when a customer
checks out: it atomically decrements stock or returns 409 if there isn't enough.
"""
from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..repository import ProductRepository
from ..schemas import ProductCreate, ProductOut, ProductPage, StockReservation
from ..service import (
    InsufficientStock,
    ProductNotFound,
    ProductService,
    SkuAlreadyExists,
)

router = APIRouter(prefix="/products", tags=["products"])


def _service(session: AsyncSession = Depends(get_session)) -> ProductService:
    """Assemble the service graph for one request (dependency injection)."""
    return ProductService(ProductRepository(session))


def _encode_cursor(item_id: str) -> str:
    """Opaque cursor = base64 of the last-seen id. Encoding keeps the wire token
    opaque so clients treat it as a handle rather than coupling to our id scheme.
    """
    return base64.urlsafe_b64encode(item_id.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> str:
    try:
        return base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        # A malformed cursor is a client error, not a 500.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid cursor")


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, svc: ProductService = Depends(_service)) -> ProductOut:
    try:
        product = await svc.create(payload)
    except SkuAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="sku already exists")
    return ProductOut.model_validate(product)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, svc: ProductService = Depends(_service)) -> ProductOut:
    try:
        product = await svc.get(product_id)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    return ProductOut.model_validate(product)


@router.get("", response_model=None)
async def list_products(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cursor: str | None = Query(
        None,
        description="Opaque keyset cursor. When provided, seek past the last-seen "
        "id (offset is ignored) and the response is a paged envelope.",
    ),
    svc: ProductService = Depends(_service),
) -> list[ProductOut] | ProductPage:
    # Two pagination modes share one endpoint:
    #
    # Keyset/cursor mode (when `cursor` is present): seeks `id > cursor` and is
    # cheap at any depth — preferred for infinite scroll and deep pages. Returns
    # a ProductPage so the client gets the `next_cursor` to continue with.
    if cursor is not None:
        # An empty cursor is the "start of collection" sentinel, so a client can
        # bootstrap a keyset walk (get the first page + a next_cursor) without
        # already holding one; a non-empty cursor decodes to the last-seen id.
        after_id = _decode_cursor(cursor) or None
        products = await svc.list_keyset(limit=limit, after_id=after_id)
        items = [ProductOut.model_validate(p) for p in products]
        # A full page (== limit) means there may be more, so hand back a cursor
        # pointing at the last row. A short page means we reached the end, so
        # signal exhaustion with null. (A full final page is discovered as empty
        # on the following request, which then returns null.)
        next_cursor = _encode_cursor(products[-1].id) if len(products) == limit else None
        return ProductPage(items=items, next_cursor=next_cursor)

    # Offset mode (unchanged default): simple and supports random page access,
    # but OFFSET scans and discards preceding rows, so it degrades on deep pages.
    products = await svc.list(limit=limit, offset=offset)
    return [ProductOut.model_validate(p) for p in products]


@router.post("/{product_id}/reserve", response_model=ProductOut)
async def reserve_stock(
    product_id: str,
    payload: StockReservation,
    svc: ProductService = Depends(_service),
) -> ProductOut:
    try:
        product = await svc.reserve_stock(product_id, payload.quantity)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    except InsufficientStock:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="insufficient stock")
    return ProductOut.model_validate(product)


@router.post("/{product_id}/release", response_model=ProductOut)
async def release_stock(
    product_id: str,
    payload: StockReservation,
    svc: ProductService = Depends(_service),
) -> ProductOut:
    """Return previously-reserved units to stock (saga compensation).

    Called by the Orders service when a checkout fails after reserving. Unlike
    reserve there is no 409 path — adding stock back can never be "insufficient".
    """
    try:
        product = await svc.release_stock(product_id, payload.quantity)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="product not found")
    return ProductOut.model_validate(product)
