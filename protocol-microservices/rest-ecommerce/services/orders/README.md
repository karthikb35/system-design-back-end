# Orders Service

The **Orders service** is where the system becomes truly *distributed*. Placing
an order is not a single database write — it is an **orchestration** that calls
two other services:

1. **Users service** — confirm the buyer actually exists.
2. **Products service** — get each product's price and reserve its stock.

Only after those succeed does it write the order to its own database
(`orders_db`).

---

## 1. Where this service sits in the system

```mermaid
flowchart LR
    Client([Client / Gateway]) -->|HTTP JSON| Orders[Orders Service :8003]
    Orders --> DB[(orders_db)]
    Orders -->|"GET /users/{id}"| Users[Users Service :8001]
    Orders -->|"GET /products/{id}<br/>POST /products/{id}/reserve"| Products[Products Service :8002]
```

This is the first service that is a **client** of others. Those calls cross the
network, so they need timeouts and retries (see [clients.py](app/clients.py)).

---

## 2. Layered architecture (with an extra client layer)

```mermaid
flowchart TD
    A["Router<br/>(app/routers/orders.py)"] --> B["Service<br/>(app/service.py)"]
    B --> C["Repository<br/>(app/repository.py)"]
    C --> D["Order / OrderItem<br/>(app/models.py)"]
    B --> E["HTTP clients<br/>(app/clients.py)"]
    E -->|network| Users[Users Service]
    E -->|network| Products[Products Service]
```

The **service layer** now depends on two collaborators (the clients), which is
why they are injected — tests substitute in-memory fakes and run with no network.

---

## 3. The checkout flow — step by step

```mermaid
sequenceDiagram
    participant C as Client
    participant R as orders router
    participant S as OrderService
    participant U as UsersClient
    participant P as ProductsClient
    participant DB as orders_db

    C->>R: POST /orders {user_id, items[]}
    R->>S: place_order(data)

    S->>U: user_exists(user_id)
    U-->>S: true
    Note over S,U: if false -> UserNotFound -> HTTP 422

    loop for each line item
        S->>P: get_product(id)
        P-->>S: {price_cents, stock}
        S->>P: reserve(id, qty)
        P-->>S: ok (stock decremented)
        Note over S,P: if oversold/missing -> ProductUnavailable -> HTTP 409
    end

    S->>S: total = sum(price * qty)
    S->>DB: INSERT order + items (price snapshot)
    DB-->>S: order
    S-->>R: order
    R-->>C: 201 Created {status: confirmed, total_cents, items[]}
```

---

## 4. Resilience: timeouts + retries

Every downstream call goes through `_request_with_retry` in
[clients.py](app/clients.py):

```mermaid
flowchart TD
    Start([send request]) --> Try{network ok<br/>& status < 500?}
    Try -->|yes| Return([return response])
    Try -->|"no (timeout / 5xx)"| More{attempts left?}
    More -->|yes| Backoff["wait 0.1s, 0.2s, 0.4s ...<br/>(exponential backoff)"] --> Start
    More -->|no| Fail([raise DownstreamError -> HTTP 502])
```

Key rules:
- **Timeout** (`HTTP_TIMEOUT_SECONDS`, default 5s) — never block forever on a
  slow dependency.
- **Retry only transient failures** — network errors and `5xx`. A `4xx` is the
  caller's fault, so it is *not* retried (retrying wouldn't help and could
  duplicate work).
- **Exponential backoff** — spacing retries out avoids hammering a struggling
  service.
- **Correlation id forwarded** — the `X-Request-ID` header is passed downstream
  so one id traces the whole request across all three services.

---

## 5. File-by-file explanation

### `app/models.py` — `orders` + `order_items`
- An `Order` header row has many `OrderItem` rows (`relationship` with
  `cascade="all, delete-orphan"` and `lazy="selectin"` so items are eager-loaded
  in one extra query rather than one-per-row).
- **`unit_price_cents` is a price *snapshot*** taken at purchase time. If the
  catalog price changes tomorrow, past orders keep the price the customer
  actually paid.

### `app/schemas.py` — DTOs
- `OrderCreate` requires at least one item (`min_length=1`) and each item needs
  `quantity > 0`.
- `OrderOut` includes the nested `items` list.

### `app/clients.py` — the network boundary
- `UsersClient.user_exists` — `GET /users/{id}`; 404 → `False`, 200 → `True`.
- `ProductsClient.get_product` / `reserve` — fetch price, then decrement stock.
- Domain exceptions (`UserNotFound`, `ProductUnavailable`, `DownstreamError`)
  translate downstream HTTP outcomes into meaningful errors for the service.

### `app/service.py` — the orchestration
`place_order` runs the three steps (validate buyer → reserve each item → persist)
and raises clear domain errors. Because the clients are injected, this whole flow
is unit-testable with fakes.

### `app/dependencies.py` — injectable clients
Exposes `get_users_client` / `get_products_client` as FastAPI dependencies. Tests
override them with in-memory fakes via `app.dependency_overrides`.

### `app/routers/orders.py` — HTTP endpoints
Maps domain errors to status codes:
`UserNotFound → 422`, `ProductUnavailable → 409`, `DownstreamError → 502`,
unknown order → `404`.

### `app/routers/health.py`, `app/observability.py`, `app/config.py`, `app/database.py`, `app/main.py`
Same patterns as the other services. `config.py` additionally holds the
downstream service URLs and the HTTP timeout/retry settings.

> ⚠️ **Distributed-transaction gotcha:** if the order INSERT fails *after* stock
> was reserved, that stock is now reserved for an order that doesn't exist. A
> real system fixes this with the **Saga pattern** — emit a compensating
> "release stock" action on failure — or an **outbox** so the reserve+order
> commit atomically. This demo keeps the happy path clear; the compensation is
> the natural next step.

---

## 6. Running it

```bash
# from services/orders — needs Users(:8001) and Products(:8002) reachable
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
# open http://localhost:8003/docs
```

### Try it with curl (via docker-compose, all services up)
```bash
curl -s -X POST localhost:8003/orders \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<real-user-id>","items":[{"product_id":"<real-product-id>","quantity":2}]}'
```

### Tests
```bash
pytest -q     # downstream services are faked; no network needed
```

The suite covers: liveness, happy-path order (with correct total), unknown buyer
(422), insufficient stock (409), unknown product (409), get/list orders, unknown
order (404), and empty-items validation (422).
