# Orders Service (GraphQL)

The **Orders** service owns checkout. It is the most interesting service in this
repo because it is simultaneously a GraphQL **server** (it exposes `placeOrder`,
`order`, `orders`) and a GraphQL **client** (it POSTs GraphQL documents to the
Users and Products services to fulfil an order).

---

## 1. Where it sits

```mermaid
flowchart LR
    GW["API Gateway"]
    O["Orders<br/>GraphQL @ 8003"]
    U["Users<br/>GraphQL @ 8001"]
    P["Products<br/>GraphQL @ 8002"]
    DB[("orders_db")]

    GW -- "placeOrder / order / orders" --> O
    O -- "query user" --> U
    O -- "query product / mutation reserveStock" --> P
    O --> DB
```

The service both terminates GraphQL requests (top edge) and originates GraphQL
requests (bottom edges) — over plain HTTP POSTs.

---

## 2. Layered anatomy

```mermaid
flowchart TD
    A["schema.py<br/>Strawberry types + resolvers"]
    B["service.py<br/>checkout orchestration"]
    C1["clients.py<br/>GraphQL calls to Users & Products"]
    C2["repository.py<br/>database access"]
    D["models.py<br/>Order + OrderItem tables"]

    A --> B
    B --> C1
    B --> C2
    C2 --> D
```

| File | Responsibility |
| --- | --- |
| `config.py` | Settings: port, DB URL, **downstream URLs**, timeout, retries. |
| `models.py` | `Order` header + `OrderItem` lines (price snapshot per line). |
| `repository.py` | `add` / `get` / `list_for_user`. |
| `clients.py` | `UsersGraphQLClient` + `ProductsGraphQLClient` (httpx POST, retry, headers). |
| `service.py` | `OrderService.place_order` orchestration + domain exceptions. |
| `schema.py` | GraphQL types/resolvers; reads clients from `context`; maps errors. |
| `main.py` | Owns two `httpx.AsyncClient`s; wires them into the GraphQL context. |

---

## 3. The checkout flow

```mermaid
sequenceDiagram
    participant C as Caller (Gateway)
    participant O as placeOrder resolver
    participant S as OrderService
    participant U as Users (GraphQL)
    participant P as Products (GraphQL)
    participant DB as orders_db

    C->>O: mutation placeOrder(userId, items)
    O->>S: place_order(...)
    S->>U: query user(id) { id }
    U-->>S: user / error "user not found"
    loop each line item
        S->>P: query product(id) { priceCents stock }
        P-->>S: price snapshot
        S->>P: mutation reserveStock(id, qty)
        P-->>S: ok / error "only N in stock"
    end
    S->>DB: INSERT order + items
    DB-->>S: order
    S-->>O: Order
    O-->>C: { placeOrder { totalCents items { ... } } }
```

The **unit price is snapshotted** into each `OrderItem` at purchase time.

---

## 4. Resilient downstream calls

`clients.py` wraps every outbound GraphQL POST with a timeout and retry policy.
Only *transport* failures are retried; a GraphQL `errors` array is a real answer.

```mermaid
flowchart TD
    Start["POST /graphql<br/>(timeout + x-request-id)"] --> Ok{"transport ok?"}
    Ok -- no --> Retry{"retries left?"}
    Retry -- yes --> Wait["backoff 0.1·2ⁿ s"] --> Start
    Retry -- no --> Down["raise DownstreamError"]
    Ok -- yes --> Err{"GraphQL errors[]?"}
    Err -- yes --> Biz["map to ProductUnavailable / user_exists=False"]
    Err -- no --> Done["return data"]
```

The `x-request-id` header is read from `request_id_ctx` (set by the inbound
middleware) and attached to every outbound call, tracing the whole fan-out.

---

## 5. Error → GraphQL error mapping

| Domain condition | Client sees (in `errors[]`) |
| --- | --- |
| empty items / bad quantity | `an order needs at least one item` / `quantity must be positive` |
| buyer does not exist | `buyer does not exist` |
| product missing / oversold | `product … not found` / `only N in stock` |
| dependency unreachable | `a downstream service is unavailable` |
| order id not found | `order not found` |

---

## 6. Testing strategy

The suite stands up **fake** in-process Users/Products GraphQL apps (Strawberry
schemas over in-memory data) and wires the **real** Orders clients to them via an
ASGI transport. This exercises the real client code, orchestration, and GraphQL
serialization against controllable dependencies.

```mermaid
flowchart LR
    T["test_orders.py"] --> OA["real Orders app"]
    OA --> RC["real clients.py"]
    RC --> FU["fake Users GraphQL app"]
    RC --> FP["fake Products GraphQL app"]
```

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q     # 8 tests

uvicorn app.main:app --port 8003                # GraphiQL at /graphql
```
