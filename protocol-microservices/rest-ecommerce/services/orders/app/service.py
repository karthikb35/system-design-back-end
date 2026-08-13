"""Service layer — the checkout orchestration.

Placing an order is a distributed use-case that touches two other services:

1. Validate the buyer exists (Users service).
2. For each line item: fetch the product's price and reserve its stock
   (Products service).
3. Persist the order locally with a *snapshot* of the prices.

The clients are injected so tests can substitute fakes and run with no network.
"""
from __future__ import annotations

import logging

from .clients import ProductsClient, ProductUnavailable, UsersClient
from .models import Order, OrderItem
from .repository import OrderRepository
from .schemas import OrderCreate

log = logging.getLogger("orders.service")


class UserNotFound(Exception):
    """The buyer's user id does not exist."""


class OrderNotFound(Exception):
    """The requested order id does not exist."""


class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        users: UsersClient,
        products: ProductsClient,
    ) -> None:
        self._repo = repo
        self._users = users
        self._products = products

    async def place_order(self, data: OrderCreate) -> Order:
        # 1) Validate the buyer against the Users service.
        if not await self._users.user_exists(data.user_id):
            raise UserNotFound(data.user_id)

        # 2) For each item, reserve stock and snapshot the price.
        #
        # Reserving stock is a *remote mutation* on the Products service, so this
        # loop is a mini distributed transaction. If a later step fails (a
        # subsequent item is oversold, or persisting the order dies), the units
        # we already reserved would leak forever. We therefore track every
        # successful reservation and, on ANY failure, compensate by releasing
        # them — the Saga pattern with compensating actions.
        items: list[OrderItem] = []
        total = 0
        reserved: list[tuple[str, int]] = []  # (product_id, quantity) already reserved
        try:
            for line in data.items:
                product = await self._products.get_product(line.product_id)
                # reserve() raises ProductUnavailable (mapped to 409) if oversold.
                await self._products.reserve(line.product_id, line.quantity)
                reserved.append((line.product_id, line.quantity))
                unit_price = int(product["price_cents"])
                total += unit_price * line.quantity
                items.append(
                    OrderItem(
                        product_id=line.product_id,
                        quantity=line.quantity,
                        unit_price_cents=unit_price,
                    )
                )

            # 3) Persist the confirmed order.
            order = Order(user_id=data.user_id, status="confirmed", total_cents=total, items=items)
            return await self._repo.add(order)
        except Exception:
            # Something failed after one or more reservations succeeded. Roll the
            # inventory back so a failed checkout does not silently consume stock,
            # then re-raise so the original error still reaches the caller (e.g.
            # ProductUnavailable -> 409, DownstreamError -> 502).
            await self._compensate(reserved)
            raise

    async def _compensate(self, reserved: list[tuple[str, int]]) -> None:
        """Best-effort release of every reservation made during a failed checkout.

        Compensation is itself a network operation and can fail; we log and
        continue rather than mask the original error. Releases run in reverse
        order (last reserved is released first), which keeps behaviour intuitive
        when the same product appears more than once.
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


# Re-export so routers can catch it without importing clients directly.
__all__ = ["OrderService", "UserNotFound", "OrderNotFound", "ProductUnavailable"]
