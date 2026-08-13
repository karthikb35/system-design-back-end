"""Service layer — the checkout orchestration (transport-agnostic).

Placing an order:
  1. Validate the buyer exists (Users).
  2. For each line: price it and reserve stock (Products).
  3. Persist the order locally with a price snapshot.

The clients are injected, so tests can point them at fake in-process GraphQL apps.
"""
from __future__ import annotations

import logging

from .clients import ProductsGraphQLClient, ProductUnavailable, UsersGraphQLClient
from .models import Order, OrderItem
from .repository import OrderRepository

log = logging.getLogger("orders.service")


class UserNotFound(Exception):
    """The buyer's user id does not exist."""


class OrderNotFound(Exception):
    """The requested order id does not exist."""


class ValidationError(Exception):
    """Input failed a business validation rule."""


class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        users: UsersGraphQLClient,
        products: ProductsGraphQLClient,
    ) -> None:
        self._repo = repo
        self._users = users
        self._products = products

    async def place_order(self, user_id: str, items: list[tuple[str, int]]) -> Order:
        if not user_id:
            raise ValidationError("user_id is required")
        if not items:
            raise ValidationError("an order needs at least one item")
        for _, qty in items:
            if qty <= 0:
                raise ValidationError("quantity must be positive")

        if not await self._users.user_exists(user_id):
            raise UserNotFound(user_id)

        # Reserving stock is a remote mutation on the Products service, so this
        # loop is a mini distributed transaction. If a later line is oversold, or
        # persisting the order fails, the units we already reserved would leak. We
        # track every reservation and, on ANY failure, compensate by releasing
        # them — the Saga pattern with compensating actions.
        order_items: list[OrderItem] = []
        total = 0
        reserved: list[tuple[str, int]] = []  # (product_id, quantity) already reserved
        try:
            for product_id, qty in items:
                product = await self._products.get_product(product_id)
                await self._products.reserve(product_id, qty)
                reserved.append((product_id, qty))
                unit_price = int(product["priceCents"])
                total += unit_price * qty
                order_items.append(
                    OrderItem(product_id=product_id, quantity=qty, unit_price_cents=unit_price)
                )

            order = Order(user_id=user_id, status="confirmed", total_cents=total, items=order_items)
            return await self._repo.add(order)
        except Exception:
            # Roll the inventory back so a failed checkout does not silently
            # consume stock, then re-raise so the original error still surfaces.
            await self._compensate(reserved)
            raise

    async def _compensate(self, reserved: list[tuple[str, int]]) -> None:
        """Best-effort release of every reservation made during a failed checkout.

        Compensation is itself a network call and can fail; we log and continue
        rather than mask the original error. Releases run in reverse order.
        """
        for product_id, quantity in reversed(reserved):
            try:
                await self._products.release(product_id, quantity)
            except Exception:  # noqa: BLE001 - compensation must not raise
                log.warning(
                    "compensation failed: could not release %d unit(s) of %s",
                    quantity,
                    product_id,
                )

    async def get(self, order_id: str) -> Order:
        order = await self._repo.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    async def list_for_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Order]:
        return await self._repo.list_for_user(user_id, limit=limit, offset=offset)


__all__ = [
    "OrderService",
    "UserNotFound",
    "OrderNotFound",
    "ValidationError",
    "ProductUnavailable",
]
