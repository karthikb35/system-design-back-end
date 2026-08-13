# Request Lifecycle — placing an order

This walks a single "place an order" request from the client's HTTP call all the
way down to three databases and back, showing exactly where the protocol switches
between HTTP and gRPC.

---

## 1. End-to-end sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant GW as Gateway (HTTP)
    participant O as Orders (gRPC)
    participant U as Users (gRPC)
    participant P as Products (gRPC)
    participant DB as orders_db

    C->>GW: POST /orders {user_id, items[]}
    Note over GW: mint/read x-request-id
    GW->>O: PlaceOrder(PlaceOrderRequest)  [gRPC + metadata]
    O->>U: GetUser(user_id)
    U-->>O: UserReply / NOT_FOUND
    loop each line item
        O->>P: GetProduct(id)
        P-->>O: price snapshot
        O->>P: ReserveStock(id, qty)
        P-->>O: OK / FAILED_PRECONDITION
    end
    O->>DB: INSERT order + items (price snapshot)
    DB-->>O: order row
    O-->>GW: OrderReply
    GW-->>C: 200 JSON {id, total_cents, items[]}
```

Step 1–2 is **HTTP**; every arrow after that is **gRPC**. The Gateway is the
translation boundary.

---

## 2. Where the id lives

```mermaid
flowchart LR
    H["HTTP header<br/>x-request-id"] --> MW["Gateway middleware<br/>→ context var"]
    MW --> MD["gRPC metadata<br/>x-request-id"]
    MD --> IC["Orders interceptor<br/>→ context var"]
    IC --> MD2["gRPC metadata<br/>(outbound to Users/Products)"]
```

The same id is a header at the edge and metadata on every hop — logs from all
four services can be joined on it.

---

## 3. Failure translation

Each servicer maps domain errors to gRPC status; the Gateway maps gRPC status
back to HTTP. A failure therefore surfaces to the client as a sensible HTTP code.

```mermaid
flowchart TD
    E["domain error"] --> G["gRPC status"]
    G --> H["HTTP status (at Gateway)"]

    subgraph examples
        e1["buyer missing"] --> g1["FAILED_PRECONDITION"] --> h1["409"]
        e2["out of stock"] --> g2["FAILED_PRECONDITION"] --> h2["409"]
        e3["bad input"] --> g3["INVALID_ARGUMENT"] --> h3["422"]
        e4["dependency down"] --> g4["UNAVAILABLE"] --> h4["502"]
        e5["order not found"] --> g5["NOT_FOUND"] --> h5["404"]
    end
```

---

## 4. Retry behaviour on a flaky dependency

```mermaid
flowchart TD
    Call["Orders → Products RPC<br/>(timeout attached)"] --> R{"result?"}
    R -- OK --> Done["continue checkout"]
    R -- "UNAVAILABLE / DEADLINE" --> Retry{"retries left?"}
    R -- "business error" --> Surface["surface immediately"]
    Retry -- yes --> Backoff["wait 0.1·2ⁿ s"] --> Call
    Retry -- no --> Fail["DownstreamError → UNAVAILABLE → 502"]
```

Only transient codes are retried; a `NOT_FOUND` or `FAILED_PRECONDITION` is a
real answer and is surfaced without retrying.
