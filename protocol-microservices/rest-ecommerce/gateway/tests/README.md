# `gateway/tests/` — test suite

The gateway has **no database** — it only makes outbound HTTP calls. So the test
harness is different from the services: instead of an in-memory DB, it installs
an in-memory **fleet of the three downstream services** and routes the gateway's
outbound calls to them by port.

```mermaid
flowchart LR
    T[test_gateway.py] -->|ASGITransport| GW[app.main:app]
    GW -->|outbound httpx| MT["MockTransport fleet"]
    MT -->|port 8001| U[Users data]
    MT -->|port 8002| P[Products data]
    MT -->|port 8003| O[Orders data]
```

---

## 1. `conftest.py` — two transports, one trick

The subtlety: the client that calls the **gateway** must use the real ASGI
transport, while every client the **gateway itself** creates must use the mock
fleet. This is solved by monkeypatching `httpx.AsyncClient.__init__`:

```python
def patched_init(self, *args, **kwargs):
    kwargs.setdefault("transport", httpx.MockTransport(_handler))  # default only
    original_init(self, *args, **kwargs)
```

```mermaid
flowchart TD
    A["client fixture"] -->|explicit ASGITransport| GW[gateway app]
    B["gateway makes outbound call"] -->|no transport given → setdefault| MF["MockTransport(_handler)"]
```

- `setdefault` means an **explicit** transport (the test's `ASGITransport`) is
  respected, while the gateway's own `AsyncClient()` calls fall through to the
  mock fleet.
- `_handler(request)` routes by `request.url.port`: **8001**→USERS, **8002**→
  PRODUCTS, **8003**→ORDERS, and `/health/ready` always returns `ready`.
- The seed data (`USERS`, `PRODUCTS`, `ORDERS` dicts) makes assertions predictable.

---

## 2. `test_gateway.py` — what each test proves

```mermaid
flowchart TD
    A[test_live] --> A1["alive"]
    B[test_ready_fans_out] --> B1["all three ready → ready"]
    C[test_proxy_users_passthrough] --> C1["/api/users/user-1 → 200 Ada"]
    D[test_proxy_unknown_user_forwards_404] --> D1["ghost → 404 mirrored"]
    E[test_proxy_products_passthrough] --> E1["/api/products/prod-1 → Widget"]
    F[test_aggregate_order_summary] --> F1["order enriched: buyer_name + item name"]
```

| Test | Asserts | Guards |
|------|---------|--------|
| `test_live` | `{status: alive}` | liveness |
| `test_ready_fans_out` | overall `ready`, all three `ready` | parallel fan-out health |
| `test_proxy_users_passthrough` | `/api/users/user-1` → 200, full name | proxy forwarding |
| `test_proxy_unknown_user_forwards_404` | ghost → **404** | upstream status is mirrored, not swallowed |
| `test_proxy_products_passthrough` | `/api/products/prod-1` → `Widget` | second proxy family |
| `test_aggregate_order_summary` | `buyer_name == Ada`, `items[0].name == Widget`, total | the fan-out + merge |

---

## How to run

```powershell
cd gateway
..\.venv\Scripts\python.exe -m pytest -q
```
