# Request Lifecycle — a checkout, end to end

This traces a single **"place an order"** request through every layer and every
service, so you can see exactly what happens and where things can fail.

---

## 1. The full journey

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant GW as Gateway :8000
    participant O as Orders :8003
    participant U as Users :8001
    participant P as Products :8002
    participant ODB as orders_db

    C->>GW: POST /api/orders {user_id, items[]}
    Note over GW: assign X-Request-ID (rid)
    GW->>O: POST /orders (forwards body + rid)

    Note over O: router -> service.place_order()
    O->>U: GET /users/{user_id}  (rid)
    U-->>O: 200 (buyer exists)

    loop each item
        O->>P: GET /products/{id}  (rid)
        P-->>O: 200 {price_cents, stock}
        O->>P: POST /products/{id}/reserve {quantity}  (rid)
        P-->>O: 200 (stock decremented)
    end

    O->>ODB: INSERT order + items (price snapshot)
    ODB-->>O: order row
    O-->>GW: 201 {order}
    GW-->>C: 201 {order}
```

Every arrow carries the **same `X-Request-ID`**, so searching your logs for that
one id reconstructs this entire diagram.

---

## 2. What each numbered step does

1. Client hits the **gateway** — the only public endpoint.
2. Gateway assigns a correlation id and **forwards** to Orders (it does not
   understand orders; it just routes `/api/orders/*`).
3–4. Orders asks **Users** "does this buyer exist?" A `404` here becomes an
   `HTTP 422` back to the client (bad request — unknown buyer).
5–8. For each line item, Orders asks **Products** for the price, then **reserves**
   the stock. Insufficient stock → `HTTP 409`.
9. Orders writes the order **with a price snapshot** to its own database.
10–11. The confirmed order flows back up through the gateway to the client.

---

## 3. Failure paths

```mermaid
flowchart TD
    A[place order] --> B{buyer exists?}
    B -->|no| E1[HTTP 422 unknown buyer]
    B -->|yes| C{product exists<br/>& enough stock?}
    C -->|no| E2[HTTP 409 unavailable]
    C -->|yes| D{downstream<br/>reachable?}
    D -->|"no (timeout/5xx<br/>after retries)"| E3[HTTP 502 bad gateway]
    D -->|yes| F[persist order] --> G[HTTP 201 confirmed]
```

- **Timeouts + retries** live in each caller's HTTP client. Transient failures
  are retried with exponential backoff; a `4xx` is never retried.
- **Partial-failure gotcha:** if stock is reserved but the final INSERT fails,
  that stock is orphaned. The production fix is a **Saga** (compensating
  "release stock" action) or an **outbox** so reserve+persist commit atomically.
  This repo keeps the happy path clear and calls out the gap explicitly.

---

## 4. Observability

Each service logs one structured JSON line per request, including the request id:

```json
{"ts":"...","level":"INFO","logger":"orders","request_id":"7f3a...","message":"POST /orders -> handled in 12.4ms"}
```

Because the id is generated at the gateway and forwarded on every hop, a single
`grep 7f3a` across all four services' logs shows the request's complete path and
timing — the practical payoff of the correlation-id middleware.
