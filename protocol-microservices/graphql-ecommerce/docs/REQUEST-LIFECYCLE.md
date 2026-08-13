# Request Lifecycle — placing and reading an order

This traces two requests: placing an order (a write that fans out) and reading it
back with a single nested query (the GraphQL composition superpower).

---

## 1. Placing an order

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant GW as Gateway
    participant O as Orders
    participant U as Users
    participant P as Products
    participant DB as orders_db

    C->>GW: mutation placeOrder(userId, items)
    Note over GW: mint/read x-request-id
    GW->>O: mutation placeOrder(...)  [GraphQL POST]
    O->>U: query user(id) { id }
    U-->>O: user / error "user not found"
    loop each line item
        O->>P: query product(id) { priceCents stock }
        P-->>O: price snapshot
        O->>P: mutation reserveStock(id, qty)
        P-->>O: ok / error "only N in stock"
    end
    O->>DB: INSERT order + items (price snapshot)
    DB-->>O: order row
    O-->>GW: { placeOrder { ... } }
    GW-->>C: { data: { placeOrder { ... } } }
```

Every hop is a GraphQL document POSTed over HTTP; the Gateway forwards the
mutation and the Orders service acts as a GraphQL client of Users and Products.

---

## 2. Reading it back — one query, three services

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant GW as Gateway
    participant O as Orders
    participant U as Users
    participant P as Products

    C->>GW: order { totalCents buyer{fullName} items{ product{name} } }
    GW->>O: query order(id)
    O-->>GW: order + line items (ids only)
    Note over GW: resolve only the requested sub-fields
    par lazy field resolution
        GW->>U: query user(userId)
        GW->>P: query product(productId) ×N
    end
    U-->>GW: buyer
    P-->>GW: products
    GW-->>C: one composed JSON tree
```

If the client omits `buyer`, the Gateway never queries Users. This demand-driven
resolution is what replaces the REST/gRPC hand-written aggregation endpoint.

---

## 3. Where the id lives

```mermaid
flowchart LR
    H["HTTP header<br/>x-request-id"] --> MW["Gateway middleware<br/>→ context var"]
    MW --> OH["outbound header<br/>x-request-id"]
    OH --> SM["Orders middleware<br/>→ context var"]
    SM --> OH2["outbound header<br/>(to Users/Products)"]
```

The same id is a header on every hop — logs from all four services can be joined
on it.

---

## 4. Failures are data, not status codes

In GraphQL a business failure is HTTP 200 with an `errors` array. Each service's
resolver raises a `GraphQLError`; the Gateway re-raises the backend's message so
the client sees the real cause.

```mermaid
flowchart TD
    E["domain exception<br/>(service layer)"] --> G["GraphQLError<br/>(resolver)"]
    G --> R["{ data: null, errors: [{message}] }"]
    R --> GW["Gateway re-raises message"]
    GW --> C["client sees original cause"]

    subgraph examples
        e1["buyer missing"] --> m1["'buyer does not exist'"]
        e2["out of stock"] --> m2["'only N in stock'"]
        e3["bad input"] --> m3["'quantity must be positive'"]
    end
```

---

## 5. Retry behaviour on a flaky dependency

```mermaid
flowchart TD
    Call["Orders → Products POST /graphql<br/>(timeout attached)"] --> R{"transport ok?"}
    R -- yes --> Err{"GraphQL errors[]?"}
    Err -- no --> Done["continue checkout"]
    Err -- yes --> Surface["surface business error"]
    R -- no --> Retry{"retries left?"}
    Retry -- yes --> Backoff["wait 0.1·2ⁿ s"] --> Call
    Retry -- no --> Fail["DownstreamError → 'service unavailable'"]
```

Only transport failures are retried; a GraphQL `errors` array is a real answer
and is surfaced without retrying.
