# Concept map — `rest-ecommerce`

Where the **design patterns**, **system-design** ideas, and the handful of
genuine **DSA** touch-points from the curriculum actually show up in this repo's
code. Use it to jump from theory (the `02`/`03`/`04` folders) to a real example.

> **Honesty note.** These are CRUD-style e-commerce microservices. They are rich
> in **design patterns** and **system design**, but light on classic **DSA** —
> there are no trees, graphs, sorting, or dynamic programming here. The DSA rows
> below are the *genuine* ones only; nothing is force-fitted.

Curriculum references:
[02-solid](../../02-solid/architectural_notes.md) ·
[03-design-patterns](../../03-design-patterns/architectural_notes.md) ·
[04-system-design](../../04-system-design/architectural_notes.md)

---

## Design patterns

| Pattern | Where in this repo | Why it's an example |
|---------|--------------------|---------------------|
| **Repository** | `services/*/app/repository.py` → [users app](services/users/app/README.md), [products app](services/products/app/README.md) | Isolates all SQL behind a collection-like interface; the service layer never sees SQLAlchemy. |
| **Adapter** | `services/*/app/routers/` → [users routers](services/users/app/routers/README.md) | Adapts HTTP requests to transport-agnostic service calls. Swapping REST→gRPC→GraphQL only changes this layer. |
| **Facade / API Gateway** | `gateway/app/` → [gateway app](gateway/app/README.md) | One entry point hides three services behind a simpler surface (proxy + aggregate). |
| **Dependency Injection** | FastAPI `Depends`, `dependency_overrides` in tests → [orders tests](services/orders/tests/README.md) | Service/DB/clients are injected, not constructed inline — enables fakes in tests. |
| **Strategy** | retry policy in `services/orders/app/clients.py` → [orders app](services/orders/app/README.md) | The retry/backoff behaviour is an interchangeable policy around the HTTP call. |
| **DTO + Mapper** | Pydantic schemas + `from_attributes`/response models → [users app](services/users/app/README.md) | Wire shape (schema) is decoupled from the ORM model; a mapper converts between them. |
| **Singleton (cached)** | `get_settings()` with `lru_cache` → [users app](services/users/app/README.md) | One settings object per process. |
| **Orchestration (Saga-ish)** | `services/orders/app/service.py` place-order flow → [orders app](services/orders/app/README.md) | Coordinates validate-buyer → reserve-stock → persist across services. |

See [03-design-patterns/architectural_notes.md](../../03-design-patterns/architectural_notes.md).

## SOLID

| Principle | Where | Why |
|-----------|-------|-----|
| **SRP** | the layered split router / service / repository / models | each layer has exactly one reason to change. |
| **DIP** | service depends on a repository *abstraction*, injected clients | high-level policy doesn't depend on low-level detail. |
| **OCP** | adding a protocol edition doesn't modify the service layer | open for extension (new adapter), closed for modification. |
| **ISP** | narrow per-concern schemas (create vs. read models) | clients aren't forced to depend on fields they don't use. |

See [02-solid/architectural_notes.md](../../02-solid/architectural_notes.md).

## System design

| Concept | Where | Why |
|---------|-------|-----|
| **Database-per-service** | [infra/postgres](infra/postgres/README.md), each service's own DB URL | independent schemas; no cross-service table reads. |
| **API Gateway** | [gateway app](gateway/app/README.md) + [routers](gateway/app/routers/README.md) | proxy, aggregate, and fan-out health in one edge. |
| **Service orchestration** | [orders app](services/orders/app/README.md) | Orders coordinates Users + Products at checkout. |
| **Retries + exponential backoff** | `services/orders/app/clients.py` → [orders app](services/orders/app/README.md) | tolerates transient downstream failures. |
| **Idempotency / immutability (price snapshot)** | `OrderItem.unit_price_cents` → [orders app](services/orders/app/README.md) | the order records the price *at purchase time*, not a live lookup. |
| **Correlation-ID tracing** | `observability.py` middleware in every service | one `x-request-id` threads through the whole call chain. |
| **Stateless services** | no session state; JWT carries identity → [users app](services/users/app/README.md) | any instance can serve any request (horizontal scale). |
| **Health checks** | `/health` + gateway fan-out → [gateway routers](gateway/app/routers/README.md) | liveness for orchestrators/load balancers. |
| **Money as integer cents** | `price_cents` in [products app](services/products/app/README.md) | avoids floating-point rounding in financial data. |
| **Error→status mapping** | [orders routers](services/orders/app/routers/README.md) | domain failures map to precise HTTP codes (404/409/422/503). |

See [04-system-design/architectural_notes.md](../../04-system-design/architectural_notes.md).

## DSA (genuine touch-points only)

| Concept | Where | Why |
|---------|-------|-----|
| **Hashing** | bcrypt password hashing in `services/users/app/security.py` → [users app](services/users/app/README.md) | one-way hash + salt; the classic hashing use-case. |
| **Hash-map / set lookup** | primary-key/unique lookups (email, sku) via indexed columns | O(1)-ish membership/uniqueness checks. |
| **Pagination (offset/limit)** | `list(limit, offset)` in every repository | bounded slices over an ordered collection. |

> Trees, graphs, sorting, DP, and similar are **not** exercised by this domain —
> study those in [01-dsa](../../01-dsa/). This repo is the place to see
> **patterns** and **system design** in production-shaped code.

---

## Advanced patterns not yet applied here

This repo is a deliberate **baseline** (synchronous, orchestrated, one DB per
service). The production patterns it does **not** yet demonstrate — Circuit
Breaker, Saga with compensation, idempotency keys, cache-aside, event-driven
messaging, transactional outbox, read replicas, sharding, CQRS, TLS/mTLS, and
wiring the ELK platform — are documented as reference (where each would slot into
*this* system, with sketches and links to the runnable curriculum versions) in:

> **[../ADVANCED-PATTERNS.md](../ADVANCED-PATTERNS.md)**
