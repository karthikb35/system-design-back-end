"""REST-shaped endpoints that translate to gRPC calls.

Each handler takes an HTTP request, calls the matching backend gRPC method via
``BackendClients``, and returns the resulting dict as JSON. This is where the
REST world (paths, verbs, JSON bodies) is mapped onto the gRPC world (services,
methods, protobuf messages).
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..clients import BackendClients

router = APIRouter(tags=["proxy"])


def _clients(request: Request) -> BackendClients:
    return request.app.state.clients


# --- Users -------------------------------------------------------------------
@router.post("/users")
async def create_user(request: Request):
    return await _clients(request).create_user(await request.json())


@router.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    return await _clients(request).get_user(user_id)


@router.get("/users")
async def list_users(request: Request, limit: int = 50, offset: int = 0):
    return await _clients(request).list_users(limit, offset)


@router.post("/users/login")
async def login(request: Request):
    return await _clients(request).login(await request.json())


# --- Products ----------------------------------------------------------------
@router.post("/products")
async def create_product(request: Request):
    return await _clients(request).create_product(await request.json())


@router.get("/products/{product_id}")
async def get_product(product_id: str, request: Request):
    return await _clients(request).get_product(product_id)


@router.get("/products")
async def list_products(request: Request, limit: int = 50, offset: int = 0):
    return await _clients(request).list_products(limit, offset)


# --- Orders ------------------------------------------------------------------
@router.post("/orders")
async def place_order(request: Request):
    return await _clients(request).place_order(await request.json())


@router.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request):
    return await _clients(request).get_order(order_id)


@router.get("/orders")
async def list_orders(request: Request, user_id: str, limit: int = 50, offset: int = 0):
    return await _clients(request).list_orders(user_id, limit, offset)
