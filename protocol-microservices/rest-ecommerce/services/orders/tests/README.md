# `services/orders/tests/` — test suite

The Orders service is the only one that calls other services, so its tests are
the most interesting: they replace the two HTTP clients with **in-memory fakes**
via `app.dependency_overrides`, then exercise the full checkout flow with no
network and no other services running.

```mermaid
flowchart LR
    T[test_orders.py] -->|ASGITransport| App[app.main:app]
    App --> Svc[OrderService]
    Svc --> FU[FakeUsersClient]
    Svc --> FP[FakeProductsClient]
    App --> DB[(in-memory SQLite)]
```

---

## 1. `conftest.py` — fakes + overrides

```mermaid
sequenceDiagram
    participant F as client fixture
    F->>F: init_models() (schema)
    F->>F: override get_users_client → FakeUsersClient({user-1})
    F->>F: override get_products_client → FakeProductsClient(catalog)
    F-->>Test: AsyncClient over ASGITransport
    Note over F: teardown clears dependency_overrides
```

| Fake | Behaviour |
|------|-----------|
| `FakeUsersClient(known)` | `user_exists` returns `True` only for ids in the `known` set (`{"user-1"}`). |
| `FakeProductsClient(catalog)` | `get_product` returns price/stock or raises `ProductUnavailable`; `reserve` **mutates** the in-memory catalog stock or raises `ProductUnavailable` when oversold. |

The `catalog` fixture seeds `prod-1` (price 1000, stock 5) and `prod-2`
(price 2500, stock 2), so quantity math in assertions is predictable.

The fakes implement the **same method signatures** as the real clients, so the
service can't tell the difference — this is duck-typed dependency substitution.

---

## 2. `test_orders.py` — what each test proves

```mermaid
flowchart TD
    A[happy_path] --> A1["201, total = 2·1000+2500 = 4500, 2 items"]
    B[unknown_user] --> B1["ghost buyer → 422"]
    C[insufficient_stock] --> C1["qty 99 of stock 2 → 409"]
    D[unknown_product] --> D1["missing product → 409"]
    E[get_and_list] --> E1["create → GET by id → appears in user list"]
    F[unknown_order] --> F1["missing id → 404"]
    G[empty_items] --> G1["items=[] → 422 (schema min_length)"]
```

| Test | Asserts | Guards |
|------|---------|--------|
| `test_place_order_happy_path` | `201`, `total_cents == 4500`, 2 items | orchestration + price snapshot math |
| `test_place_order_unknown_user_422` | ghost buyer → **422** | buyer validation |
| `test_place_order_insufficient_stock_409` | qty 99 → **409** | oversell protection |
| `test_place_order_unknown_product_409` | missing product → **409** | `ProductUnavailable` mapping |
| `test_get_and_list_orders` | round-trip + appears in user list | read paths |
| `test_get_unknown_order_404` | missing id → **404** | `OrderNotFound` mapping |
| `test_empty_items_rejected_by_validation` | `items=[]` → **422** | boundary validation (`min_length=1`) |

---

## How to run

```powershell
cd services/orders
..\..\.venv\Scripts\python.exe -m pytest -q
```
