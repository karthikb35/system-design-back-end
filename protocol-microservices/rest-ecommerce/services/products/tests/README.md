# `services/products/tests/` — test suite

End-to-end HTTP tests over an in-memory SQLite database, same harness as the
Users service ([conftest.py](conftest.py) provides the `client` fixture via
`ASGITransport` — see [`../../users/tests/README.md`](../../users/tests/README.md) §1).

```mermaid
flowchart LR
    T[test_products.py] -->|httpx ASGITransport| App[app.main:app]
    App --> DB[(in-memory SQLite)]
```

---

## What each test proves

```mermaid
flowchart TD
    A[test_create_and_get_product] --> A1["201 + round-trip GET"]
    B[test_duplicate_sku_conflicts] --> B1["dup sku → 409"]
    C[test_reserve_stock_decrements] --> C1["stock 5, reserve 3 → 200, stock 2"]
    D[test_reserve_more_than_stock] --> D1["stock 1, reserve 2 → 409"]
    E[test_reserve_unknown_product] --> E1["unknown id → 404"]
    F[test_negative_price_rejected] --> F1["price_cents -1 → 422"]
```

| Test | Asserts | Guards the rule |
|------|---------|-----------------|
| `test_health_live` | `200 {status: alive}` | probe wiring |
| `test_create_and_get_product` | `201`, then `GET` echoes id + stock | create/read path |
| `test_duplicate_sku_conflicts` | second `DUP` sku → **409** | SKU uniqueness |
| `test_reserve_stock_decrements` | reserve 3 of 5 → **200**, `stock == 2` | the core decrement |
| `test_reserve_more_than_stock_conflicts` | reserve 2 of 1 → **409** | oversell protection (`InsufficientStock`) |
| `test_reserve_unknown_product_404` | reserve missing id → **404** | `ProductNotFound` mapping |
| `test_negative_price_rejected_by_validation` | `price_cents=-1` → **422** | boundary validation |

The `_make(client, sku, stock, price)` helper at the top builds a product so each
test starts from a known catalog state.

---

## How to run

```powershell
cd services/products
..\..\.venv\Scripts\python.exe -m pytest -q
```
