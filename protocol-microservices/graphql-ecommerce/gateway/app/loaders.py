"""Request-scoped DataLoaders that batch the Gateway's cross-service fan-out.

The Gateway stitches ``Order.buyer -> Users`` and ``OrderItem.product ->
Products`` as *field* resolvers. That is exactly where GraphQL's classic N+1
problem bites: a query returning N orders would naively fire N separate
``get_user`` calls (one per ``buyer`` field), and a query over N line items would
fire N ``get_product`` calls. With M orders each holding K items you pay
``1 (orders) + M (buyers) + M*K (products)`` backend round trips.

A ``DataLoader`` fixes this by deferring every ``.load(id)`` to the end of the
current event-loop tick, deduplicating the ids, and dispatching ONE batch load.
Because Strawberry/graphql-core resolves sibling list items concurrently, all the
``buyer``/``product`` loads for a single request land in the same tick and
collapse into a single batch each: ``1 + M + M*K`` becomes ``1 + 1 + 1``.

Honest limitation: the backend Users/Products services only expose a single-id
``user(id)`` / ``product(id)`` query, so our batch function still issues one HTTP
request per *distinct* id — gathered concurrently with ``asyncio.gather`` instead
of awaited one-by-one. A production backend would add a batch query
(``usersByIds(ids: [ID!]!)``) so the whole batch became a single round trip. Even
without that the DataLoader is a clear win: duplicate ids within a request are
fetched exactly once (request-scoped caching), and the concurrent gather replaces
sequential awaits. The loaders are built per-request so this cache never leaks
one caller's data into another's.
"""
from __future__ import annotations

import asyncio
from typing import Any

from strawberry.dataloader import DataLoader

from .clients import BackendClients


def build_loaders(clients: BackendClients) -> dict[str, DataLoader[str, dict[str, Any] | None]]:
    """Create a fresh set of DataLoaders bound to this request's clients.

    DataLoader contract: ``load_fn`` receives the list of distinct keys queued in
    the current tick (already de-duplicated against the loader's cache) and must
    return one result per key, positionally aligned. Returning ``None`` for a key
    is fine — that becomes the resolved value for that ``.load(id)``.
    """

    async def load_users(user_ids: list[str]) -> list[dict[str, Any] | None]:
        return await asyncio.gather(*(clients.get_user(uid) for uid in user_ids))

    async def load_products(product_ids: list[str]) -> list[dict[str, Any] | None]:
        return await asyncio.gather(*(clients.get_product(pid) for pid in product_ids))

    return {
        "users": DataLoader(load_fn=load_users),
        "products": DataLoader(load_fn=load_products),
    }
