# Concept map — `graphql-ecommerce`

Where the **design patterns**, **system-design** ideas, and the genuine **DSA**
touch-points from the curriculum show up in this repo. The inner layers match the
REST and gRPC editions; the differences are all at the **GraphQL edge** — a
Strawberry `schema.py` per service, and a Gateway that **stitches one graph** over
three services.

> **Honesty note.** CRUD microservices: rich in **design patterns** and **system
> design**, light on classic **DSA**. Only genuine mappings are listed. The one
> place this repo is *actually* graph-shaped is the Gateway's on-demand field
> resolution — noted below.

Curriculum references:
[02-solid](../../02-solid/architectural_notes.md) ·
[03-design-patterns](../../03-design-patterns/architectural_notes.md) ·
[04-system-design](../../04-system-design/architectural_notes.md)

---

## Design patterns

| Pattern | Where in this repo | Why it's an example |
|---------|--------------------|---------------------|
| **Adapter** | `services/*/app/schema.py` → [users app](services/users/app/README.md) | Strawberry types + resolvers adapt GraphQL operations to the transport-agnostic service. The GraphQL analogue of the REST router / gRPC servicer. |
| **Repository** | `services/*/app/repository.py` | All SQL behind a collection interface. |
| **Facade / BFF + Graph stitching** | `gateway/app/schema.py` → [gateway app](gateway/app/README.md) | The headline feature: `Order.buyer` and `OrderItem.product` are **field resolvers** that fan out to the owning service on demand — one graph over three services (a Backend-for-Frontend that composes, not just proxies). |
| **Dependency Injection** | `context_getter` injects clients into resolvers → [orders app](services/orders/app/README.md), [gateway app](gateway/app/README.md) | Downstream clients reach resolvers via the GraphQL `context`, so tests inject fakes. |
| **Strategy** | retry policy in `services/orders/app/clients.py` → [orders app](services/orders/app/README.md) | Interchangeable retry/backoff around the `httpx` GraphQL call. |
| **DTO + Mapper** | `from_model()` / `from_dict()` on every Strawberry type | Maps ORM rows (or backend JSON) to the wire type; the `User` type has no password field. |
| **Singleton (cached)** | `get_settings()` with `lru_cache` | One settings object per process. |
| **Orchestration (Saga-ish)** | `services/orders/app/service.py` → [orders app](services/orders/app/README.md) | Coordinates validate-buyer → reserve-stock → persist. |

See [03-design-patterns/architectural_notes.md](../../03-design-patterns/architectural_notes.md).

## SOLID

| Principle | Where | Why |
|-----------|-------|-----|
| **SRP** | schema / service / repository / models split | one reason to change per layer. |
| **DIP** | resolvers depend on injected client abstractions + repository | policy independent of transport. |
| **OCP** | same service layer reused behind a third protocol | new adapter (`schema.py`), no rule edits. |
| **ISP** | the client asks for exactly the fields it needs | GraphQL's defining trait — no over-fetching of unused fields. |

See [02-solid/architectural_notes.md](../../02-solid/architectural_notes.md).

## System design

| Concept | Where | Why |
|---------|-------|-----|
| **Schema / SDL contract** | every `schema.py` | a typed, introspectable graph is the contract (vs. OpenAPI / `.proto`). |
| **API composition / graph stitching** | [gateway app](gateway/app/README.md) | replaces the REST/gRPC `/aggregate` endpoint; the *client* decides how much to join. |
| **N+1 query problem** | `OrderItem.product` field resolver → [gateway app](gateway/app/README.md) | resolving each item's product with a separate call is the classic GraphQL N+1 — the reason DataLoader/batching exists. Called out honestly as a known trade-off. |
| **Database-per-service** | [infra/postgres](infra/postgres/README.md) | independent schemas. |
| **Error model** | `errors[]` in a 200 response → [users app](services/users/app/README.md) | GraphQL surfaces failure in the body, not the HTTP status. |
| **Retries + backoff** | `services/orders/app/clients.py` → [orders app](services/orders/app/README.md) | tolerates transient downstream failures. |
| **Price-snapshot immutability** | `OrderItem.unit_price_cents` → [orders app](services/orders/app/README.md) | order records price at purchase time. |
| **Correlation-ID tracing** | `CorrelationMiddleware` forwards `x-request-id` | one id across the fan-out. |
| **Money as integer cents** | [products app](services/products/app/README.md) | no float rounding. |

See [04-system-design/architectural_notes.md](../../04-system-design/architectural_notes.md).

## DSA (genuine touch-points only)

| Concept | Where | Why |
|---------|-------|-----|
| **Graph / tree traversal** | Gateway field resolution → [gateway app](gateway/app/README.md) | a GraphQL query *is* a tree the server walks, resolving child nodes (buyer, product) on demand — the one genuinely graph-shaped part of the system. |
| **Hashing** | bcrypt in `services/users/app/security.py` → [users app](services/users/app/README.md) | salted one-way hash; JWT = keyed hash. |
| **Hash-map / set lookup** | unique-key lookups (email, sku) | O(1)-ish uniqueness checks. |
| **Pagination (offset/limit)** | `list(limit, offset)` resolvers | bounded slices over an ordered collection. |

> Sorting, DP, and advanced graph algorithms are **not** exercised here — study
> those in [01-dsa](../../01-dsa/). This repo is where **patterns** + **system
> design** (and GraphQL's compose-on-demand model) live in real code.

---

## Advanced patterns not yet applied here

This repo is a deliberate **baseline** (synchronous, orchestrated, one DB per
service). The production patterns it does **not** yet demonstrate — Circuit
Breaker, Saga with compensation, idempotency keys, cache-aside, event-driven
messaging, transactional outbox, read replicas, sharding, CQRS, TLS/mTLS, and
wiring the ELK platform — are documented as reference (where each would slot into
*this* system, with sketches and links to the runnable curriculum versions) in:

> **[../ADVANCED-PATTERNS.md](../ADVANCED-PATTERNS.md)**
