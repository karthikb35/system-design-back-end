# Orders Service (gRPC)

The **Orders** service owns checkout. It is the most interesting service in this
repo because it is simultaneously a gRPC **server** (it implements
`OrderService`) and a gRPC **client** (it calls `UserService` and
`ProductService` to fulfil an order). It is the direct counterpart of the REST
edition's Orders service — same domain logic, different transport.

---

## 1. Where it sits in the system

```mermaid
flowchart LR
    GW["API Gateway<br/>(HTTP facade)"]
    O["Orders<br/>OrderService @ 50053"]
    U["Users<br/>UserService @ 50051"]
    P["Products<br/>ProductService @ 50052"]
    DB[("orders_db")]

    GW -- "PlaceOrder / GetOrder / ListOrders" --> O
    O -- "GetUser" --> U
    O -- "GetProduct / ReserveStock" --> P
    O --> DB
```

The service both terminates RPCs (top edge) and originates RPCs (bottom edges).

---

## 2. Layered anatomy

Every request flows through the same layers. Only `servicer.py` knows about
protobuf; everything below it is transport-agnostic Python.

```mermaid
flowchart TD
    A["servicer.py<br/>protobuf ↔ domain, status mapping"]
    B["service.py<br/>checkout orchestration"]
    C1["clients.py<br/>gRPC calls to Users & Products"]
    C2["repository.py<br/>database access"]
    D["models.py<br/>Order + OrderItem tables"]

    A --> B
    B --> C1
    B --> C2
    C2 --> D
```

| File | Responsibility |
| --- | --- |
| `config.py` | Settings: bind address, DB URL, **downstream addresses**, timeout, retries. |
| `database.py` | Async engine, `SessionLocal`, `init_models`. |
| `models.py` | `Order` header + `OrderItem` lines (price snapshot per line). |
| `repository.py` | `add` / `get` / `list_for_user` — the only DB code. |
| `clients.py` | `UsersGrpcClient` + `ProductsGrpcClient` with deadline, retry, metadata. |
| `service.py` | `OrderService.place_order` orchestration + domain exceptions. |
| `servicer.py` | Maps domain exceptions to gRPC status codes. |
| `observability.py` | Correlation interceptor + JSON logs; forwards `x-request-id`. |
| `server.py` | Builds the async server, opens downstream channels, wires health. |

---

## 3. The checkout sequence

```mermaid
sequenceDiagram
    participant C as Caller (Gateway)
    participant O as OrderServicer
    participant S as OrderService
    participant U as Users (gRPC)
    participant P as Products (gRPC)
    participant DB as orders_db

    C->>O: PlaceOrder(user_id, items)
    O->>S: place_order(...)
    S->>U: GetUser(user_id)
    U-->>S: UserReply / NOT_FOUND
    loop each line item
        S->>P: GetProduct(id)
        P-->>S: price snapshot
        S->>P: ReserveStock(id, qty)
        P-->>S: OK / FAILED_PRECONDITION
    end
    S->>DB: INSERT order + items
    DB-->>S: order
    S-->>O: Order
    O-->>C: OrderReply(total_cents, items[])
```

The **unit price is snapshotted** into each `OrderItem` at purchase time, so a
later price change never rewrites order history.

---

## 4. Resilient downstream calls

`clients.py` wraps every outbound RPC with a deadline and a retry policy. Only
*transient* codes are retried; business errors are surfaced immediately.

```mermaid
flowchart TD
    Start["make gRPC call<br/>(with timeout + x-request-id)"] --> Ok{"success?"}
    Ok -- yes --> Done["return reply"]
    Ok -- no --> Code{"code transient?<br/>UNAVAILABLE / DEADLINE"}
    Code -- no --> Biz["raise business error<br/>(NOT_FOUND, FAILED_PRECONDITION)"]
    Code -- yes --> Retry{"retries left?"}
    Retry -- yes --> Wait["backoff 0.1·2ⁿ s"] --> Start
    Retry -- no --> Down["raise DownstreamError"]
```

The `x-request-id` metadata is read from `request_id_ctx` (set by the inbound
interceptor) and attached to every outbound call, so one id traces the whole
Gateway → Orders → Users/Products fan-out.

---

## 5. Error → gRPC status mapping

| Domain condition | Raised as | gRPC status |
| --- | --- | --- |
| empty items / bad quantity | `ValidationError` | `INVALID_ARGUMENT` |
| buyer does not exist | `UserNotFound` | `FAILED_PRECONDITION` |
| product missing / oversold | `ProductUnavailable` | `FAILED_PRECONDITION` |
| dependency unreachable | `DownstreamError` | `UNAVAILABLE` |
| order id not found | `OrderNotFound` | `NOT_FOUND` |

---

## 6. Testing strategy

The Orders service cannot import the other services' server code, so the test
suite stands up **fake** in-process gRPC servers implementing the generated
`UserServiceServicer` / `ProductServiceServicer` on ephemeral ports. This
exercises the **real** client code, orchestration, and serialization against a
controllable dependency.

```mermaid
flowchart LR
    T["test_orders.py"] --> OS["real Orders server"]
    OS --> RC["real clients.py"]
    RC --> FU["fake Users server<br/>(in-memory dict)"]
    RC --> FP["fake Products server<br/>(in-memory dict)"]
```

Run locally:

```powershell
$env:GRPC_VERBOSITY="NONE"   # silence harmless GOAWAY noise on teardown
..\..\.venv\Scripts\python.exe -m pytest -q
```

---

## 7. Running

```powershell
python -m app.server        # starts the async gRPC server on :50053
python -m app.healthcheck   # exits 0 when SERVING (used by Docker HEALTHCHECK)
```
