# `services/orders/tests/` — test suite (GraphQL)

Orders is a GraphQL **client** of Users and Products, so the suite builds two
tiny **fake Strawberry apps** (in-memory data) and wires the **real** Orders
clients to them over an in-process ASGI transport. The real client code,
orchestration, and GraphQL serialization are all exercised for real.

```mermaid
flowchart LR
    T[test_orders.py] -->|"gql placeOrder"| App[real Orders app]
    App --> RealClients["real Users/Products GraphQL clients"]
    RealClients -->|ASGI| FUsers[fake Users Strawberry app]
    RealClients -->|ASGI| FProducts[fake Products Strawberry app]
```

---

## 1. `conftest.py` — fake downstream graphs

```mermaid
sequenceDiagram
    participant F as client fixture
    F->>F: _reset_fakes() (restore stock)
    F->>F: drop_all + init_models (Orders DB)
    F->>F: build fake Users + Products Strawberry apps
    F->>F: wrap them in httpx ASGITransport clients
    F->>F: create_app(users_client, products_client) [inject]
    F-->>Test: httpx AsyncClient over the real Orders app
```

- **`_UsersQuery`** — a fake `user(id)` resolver; unknown id raises
  `GraphQLError("user not found")` (matching the real Users service's error).
- **`_ProductsQuery` / `_ProductsMutation`** — fake `product(id)` and
  `reserveStock(id, quantity)`; oversell raises `GraphQLError("only N in stock")`
  and successful reserves **mutate the in-memory `_PRODUCTS` stock** so a second
  reserve sees the decremented value.
- `_reset_fakes()` restores stock (`prod-1`=10, `prod-2`=1) before each test so
  cases don't leak state.
- The fixture injects the real clients via `create_app(users_client=...,
  products_client=...)` and drives the app through its real
  `lifespan_context` — so `init_models` runs but no real `httpx` clients are
  built.

**Why fakes are Strawberry apps, not mocks:** this exercises the *actual* GraphQL
serialization (camelCase `priceCents`), the `_post_graphql` retry/error handling,
and the `errors[]` inspection end-to-end.

---

## 2. `test_orders.py`

```mermaid
flowchart TD
    A[place_order_happy_path] --> A1["total = Σ priceCents·qty, status confirmed"]
    B[unknown_buyer] --> B1["errors: buyer does not exist"]
    C[insufficient_stock] --> C1["errors: only 1 in stock (prod-2)"]
    D[unknown_product] --> D1["errors: product not found"]
    E[get_order_roundtrips] --> E1["place then query same id"]
    F[list_orders_for_user] --> F1["paginated by user"]
```

Failure cases follow the GraphQL convention: **HTTP 200**, `data: null`, message
in `errors[0]`. The happy path asserts the order total equals the sum of the
snapshotted `priceCents × quantity`, and that reserving stock actually decrements
the fake Products inventory.

---

## How to run

```powershell
cd services/orders
..\..\.venv\Scripts\python.exe -m pytest -q
```
