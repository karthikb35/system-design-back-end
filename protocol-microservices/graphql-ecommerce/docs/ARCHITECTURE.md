# Architecture — GraphQL E-commerce

This repo implements the same e-commerce domain as the REST and gRPC editions,
but every service speaks **GraphQL** and the Gateway composes them into a single
unified graph. Reading the three editions side by side shows what the transport
choice changes — and what stays identical.

---

## 1. System topology

```mermaid
flowchart TB
    Client["Client"]
    subgraph Edge
        GW["API Gateway<br/>unified GraphQL :8000"]
    end
    subgraph Services
        U["Users<br/>GraphQL :8001"]
        P["Products<br/>GraphQL :8002"]
        O["Orders<br/>GraphQL :8003"]
    end
    subgraph Data
        DBU[("users_db")]
        DBP[("products_db")]
        DBO[("orders_db")]
    end

    Client --> GW
    GW --> U & P & O
    O --> U & P
    U --> DBU
    P --> DBP
    O --> DBO
```

Only the Gateway is public. Every service — including the Gateway — exposes a
single `/graphql` endpoint.

---

## 2. One endpoint, client-selected fields

The defining GraphQL trait: there is one endpoint per service and the client
chooses which fields to fetch. There are no per-resource URLs and no HTTP status
codes for business outcomes — errors are returned in the response's `errors`
array while the HTTP status stays 200.

```mermaid
flowchart LR
    Q["POST /graphql<br/>{ query, variables }"] --> R["resolvers"]
    R --> S["service layer"]
    S --> DB[("database")]
    R -->|success| D["{ data }"]
    R -->|domain error| E["{ data: null, errors[] }"]
```

---

## 3. Per-service layering

Every service uses the same layered design; only the top (schema) layer knows
about GraphQL.

```mermaid
flowchart TD
    S["schema.py — Strawberry types + resolvers"]
    B["service.py — business logic (transport-agnostic)"]
    R["repository.py — the only DB code"]
    M["models.py — SQLAlchemy tables"]
    S --> B --> R --> M
```

Because `service.py` and below never import Strawberry, the exact same business
logic is what the REST and gRPC editions expose — only the adapter differs.

---

## 4. The Gateway is a composition layer, not a proxy

In REST/gRPC the Gateway forwards calls and needs a bespoke `/aggregate` endpoint
to join data. Here the Gateway defines a **graph**: `Order.buyer` and
`OrderItem.product` are fields resolved on demand from the owning service.

```mermaid
flowchart LR
    subgraph "Gateway graph"
        O["Order"] -->|buyer| U["User (Users svc)"]
        O -->|items| I["OrderItem"]
        I -->|product| PR["Product (Products svc)"]
    end
```

A client asks for exactly the nesting it needs; unrequested fields are never
resolved, so no downstream call is made for them.

---

## 5. Cross-cutting concerns

```mermaid
flowchart LR
    subgraph "Every service"
        MW["Correlation middleware<br/>(x-request-id)"]
        HP["/health endpoint"]
        LG["JSON structured logs"]
    end
    MW --> LG
```

- **Correlation id**: the Gateway mints an `x-request-id`; every service reads it
  and forwards it on outbound GraphQL calls, so one id traces the whole fan-out.
- **Health**: each service exposes `/health` for Docker's `HEALTHCHECK`.
- **Deadlines + retries**: callers (Orders, Gateway) attach a timeout to every
  GraphQL POST and retry only transport-level failures.

---

## 6. Data ownership

Database-per-service: one Postgres instance, three logical databases created by
`infra/postgres/init-databases.sql`. No service reads another's tables — the only
way to get another service's data is to query its graph.

| Service | Database | Owns |
| --- | --- | --- |
| Users | `users_db` | user accounts, credentials |
| Products | `products_db` | catalog, stock levels |
| Orders | `orders_db` | orders + line items (with price snapshot) |
