"""GraphQL clients the Gateway uses to talk to the three backend services.

Each backend is itself a GraphQL server, so the Gateway forwards GraphQL
documents to them over HTTP. Every method returns the relevant slice of ``data``
or re-raises the backend's error message as a ``GraphQLError`` so it surfaces to
the original caller unchanged.

The three ``httpx.AsyncClient``s are injected, so tests can point them at fake
in-process apps via an ASGI transport.
"""
from __future__ import annotations

import httpx
from graphql import GraphQLError

from .config import get_settings
from .observability import outbound_headers


class BackendClients:
    def __init__(
        self,
        users_http: httpx.AsyncClient,
        products_http: httpx.AsyncClient,
        orders_http: httpx.AsyncClient,
    ) -> None:
        self._users = users_http
        self._products = products_http
        self._orders = orders_http
        self._timeout = get_settings().http_timeout_seconds

    async def _post(self, client: httpx.AsyncClient, query: str, variables: dict) -> dict:
        try:
            resp = await client.post(
                "/graphql",
                json={"query": query, "variables": variables},
                headers=outbound_headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GraphQLError(f"backend unavailable: {exc}")
        body = resp.json()
        if body.get("errors"):
            # Re-raise the backend's message so the client sees the real cause.
            raise GraphQLError(body["errors"][0]["message"])
        return body["data"]

    # --- Users ---------------------------------------------------------------
    async def get_user(self, user_id: str) -> dict | None:
        q = "query ($id: ID!) { user(id: $id) { id email fullName isActive } }"
        try:
            data = await self._post(self._users, q, {"id": user_id})
        except GraphQLError:
            return None
        return data["user"]

    async def list_users(self, limit: int, offset: int) -> list[dict]:
        q = "query ($l: Int!, $o: Int!) { users(limit: $l, offset: $o) { id email fullName isActive } }"
        data = await self._post(self._users, q, {"l": limit, "o": offset})
        return data["users"]

    async def create_user(self, email: str, password: str, full_name: str) -> dict:
        q = """mutation ($e: String!, $p: String!, $n: String!) {
          createUser(email: $e, password: $p, fullName: $n) { id email fullName isActive }
        }"""
        data = await self._post(self._users, q, {"e": email, "p": password, "n": full_name})
        return data["createUser"]

    async def login(self, email: str, password: str) -> dict:
        q = "mutation ($e: String!, $p: String!) { login(email: $e, password: $p) { accessToken tokenType } }"
        data = await self._post(self._users, q, {"e": email, "p": password})
        return data["login"]

    # --- Products ------------------------------------------------------------
    async def get_product(self, product_id: str) -> dict | None:
        q = "query ($id: ID!) { product(id: $id) { id sku name description priceCents stock } }"
        try:
            data = await self._post(self._products, q, {"id": product_id})
        except GraphQLError:
            return None
        return data["product"]

    async def list_products(self, limit: int, offset: int) -> list[dict]:
        q = """query ($l: Int!, $o: Int!) {
          products(limit: $l, offset: $o) { id sku name description priceCents stock }
        }"""
        data = await self._post(self._products, q, {"l": limit, "o": offset})
        return data["products"]

    async def create_product(self, sku: str, name: str, price_cents: int, description: str, stock: int) -> dict:
        q = """mutation ($sku: String!, $n: String!, $p: Int!, $d: String!, $s: Int!) {
          createProduct(sku: $sku, name: $n, priceCents: $p, description: $d, stock: $s) {
            id sku name description priceCents stock
          }
        }"""
        data = await self._post(
            self._products, q, {"sku": sku, "n": name, "p": price_cents, "d": description, "s": stock}
        )
        return data["createProduct"]

    # --- Orders --------------------------------------------------------------
    _ORDER_FIELDS = "id userId status totalCents items { productId quantity unitPriceCents }"

    async def get_order(self, order_id: str) -> dict:
        q = f"query ($id: ID!) {{ order(id: $id) {{ {self._ORDER_FIELDS} }} }}"
        data = await self._post(self._orders, q, {"id": order_id})
        return data["order"]

    async def list_orders(self, user_id: str, limit: int, offset: int) -> list[dict]:
        q = f"query ($u: ID!, $l: Int!, $o: Int!) {{ orders(userId: $u, limit: $l, offset: $o) {{ {self._ORDER_FIELDS} }} }}"
        data = await self._post(self._orders, q, {"u": user_id, "l": limit, "o": offset})
        return data["orders"]

    async def place_order(self, user_id: str, items: list[dict]) -> dict:
        q = f"""mutation ($u: ID!, $items: [OrderItemInput!]!) {{
          placeOrder(userId: $u, items: $items) {{ {self._ORDER_FIELDS} }}
        }}"""
        data = await self._post(self._orders, q, {"u": user_id, "items": items})
        return data["placeOrder"]
