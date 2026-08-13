# `services/orders/tests/` — test suite (gRPC)

The Orders service is a gRPC **client** of Users and Products, so its tests stand
up **two fake in-process gRPC servers** that implement the generated
`UserServiceServicer` / `ProductServiceServicer` interfaces. The **real** Orders
client, orchestration, and protobuf serialization run end-to-end against them.

```mermaid
flowchart LR
    T[test_orders.py] -->|OrderServiceStub| OS["real Orders server"]
    OS -->|UsersGrpcClient| FU["fake Users server<br/>(in-memory dict)"]
    OS -->|ProductsGrpcClient| FP["fake Products server<br/>(in-memory dict)"]
    OS --> DB[(in-memory SQLite)]
```

---

## 1. `conftest.py` — three real servers, two of them fake logic

```mermaid
sequenceDiagram
    participant F as stub fixture
    F->>F: _reset_schema (drop+create)
    F->>F: start _FakeUserService on 127.0.0.1:0
    F->>F: start _FakeProductService on 127.0.0.1:0
    F->>F: wrap channels in real UsersGrpcClient / ProductsGrpcClient
    F->>F: build_server(orders, users_client, products_client)
    F-->>Test: OrderServiceStub
    Note over F: teardown closes channels + stops all 3 servers
```

| Fake | Seed data | Behaviour |
|------|-----------|-----------|
| `_FakeUserService` | `{"user-1": ...}` | `GetUser` → reply or `NOT_FOUND` |
| `_FakeProductService` | `prod-1` (4999, stock 10), `prod-2` (2500, stock 1) | `GetProduct` / `ReserveStock`; **mutates stock**; `FAILED_PRECONDITION` when oversold |

The fakes are **real gRPC servers** (not mocks) — so the actual client retry
logic, deadlines, metadata forwarding, and serialization are all exercised.

---

## 2. `test_orders.py` — what each test proves

```mermaid
flowchart TD
    A[computes_total_from_snapshot] --> A1["2·4999 + 2500 = 12498, item price snapshot"]
    B[unknown_user] --> B1["FAILED_PRECONDITION"]
    C[unknown_product] --> C1["FAILED_PRECONDITION"]
    D[insufficient_stock] --> D1["FAILED_PRECONDITION"]
    E[empty_items] --> E1["INVALID_ARGUMENT"]
    F[get_roundtrips] --> F1["place → GetOrder same id/total"]
    G[unknown_order] --> G1["NOT_FOUND"]
    H[list_for_user] --> H1["2 placed → 2 returned"]
```

| Test | Expected `StatusCode` |
|------|-----------------------|
| `test_place_order_computes_total_from_snapshot` | OK (`total == 12498`) |
| `test_unknown_user_is_failed_precondition` | `FAILED_PRECONDITION` |
| `test_unknown_product_is_failed_precondition` | `FAILED_PRECONDITION` |
| `test_insufficient_stock_is_failed_precondition` | `FAILED_PRECONDITION` |
| `test_empty_items_is_invalid_argument` | `INVALID_ARGUMENT` |
| `test_get_order_roundtrips` | OK |
| `test_get_unknown_order_is_not_found` | `NOT_FOUND` |
| `test_list_orders_for_user` | OK (count == 2) |

---

## How to run

```powershell
cd services/orders
$env:GRPC_VERBOSITY="NONE"
..\..\.venv\Scripts\python.exe -m pytest -q
```
