# Concept map — `grpc-ecommerce`

Where the **design patterns**, **system-design** ideas, and the genuine **DSA**
touch-points from the curriculum show up in this repo. The inner layers are the
same as the REST edition; the differences are all at the **gRPC edge** (servicer,
server, interceptor, generated stubs).

> **Honesty note.** CRUD microservices: rich in **design patterns** and **system
> design**, light on classic **DSA**. Only genuine mappings are listed.

Curriculum references:
[02-solid](../../02-solid/architectural_notes.md) ·
[03-design-patterns](../../03-design-patterns/architectural_notes.md) ·
[04-system-design](../../04-system-design/architectural_notes.md)

---

## Design patterns

| Pattern | Where in this repo | Why it's an example |
|---------|--------------------|---------------------|
| **Adapter** | `services/*/app/servicer.py` → [users app](services/users/app/README.md) | Adapts protobuf messages ⇄ transport-agnostic service calls. This is the gRPC analogue of the REST router. |
| **Repository** | `services/*/app/repository.py` | All SQL behind a collection interface; the service never sees SQLAlchemy. |
| **Proxy (remote)** | generated client stubs in `pb/` → [users pb](services/users/app/pb/README.md) | A stub is a local stand-in whose method calls execute on a remote server — the textbook remote **Proxy**. |
| **Interceptor / Chain of Responsibility** | `CorrelationInterceptor` in `observability.py` → [users app](services/users/app/README.md) | Cross-cutting logic wraps every RPC — gRPC's equivalent of middleware. |
| **Facade / API Gateway** | `gateway/app/` → [gateway app](gateway/app/README.md) | One edge translates inbound HTTP to gRPC stub calls across three services. |
| **Strategy** | retry policy in `services/orders/app/clients.py` → [orders app](services/orders/app/README.md) | Interchangeable retry/backoff around the stub call (retries only `UNAVAILABLE`/`DEADLINE_EXCEEDED`). |
| **DTO + Mapper** | `_to_reply()` / `_to_pb()` in each servicer | Maps the ORM object to a protobuf reply (which has no password field). |
| **Singleton (cached)** | `get_settings()` with `lru_cache` | One settings object per process. |
| **Orchestration (Saga-ish)** | `services/orders/app/service.py` → [orders app](services/orders/app/README.md) | Coordinates validate-buyer → reserve-stock → persist across services. |

See [03-design-patterns/architectural_notes.md](../../03-design-patterns/architectural_notes.md).

## SOLID

| Principle | Where | Why |
|-----------|-------|-----|
| **SRP** | servicer / service / repository / models split | one reason to change per layer. |
| **DIP** | service depends on the repository abstraction + injected stubs | policy doesn't depend on transport detail. |
| **OCP** | the same service layer is reused unchanged behind gRPC | new transport = new adapter, no edit to rules. |
| **LSP** | fake in-process gRPC servers substitute for real ones in tests → [orders tests](services/orders/tests/README.md) | a stand-in honours the same contract. |

See [02-solid/architectural_notes.md](../../02-solid/architectural_notes.md).

## System design

| Concept | Where | Why |
|---------|-------|-----|
| **Contract-first / schema (IDL)** | [protos/](protos/README.md), [scripts/](scripts/README.md) | `.proto` files are the source of truth; stubs are code-generated — strong typing + versioned field numbers. |
| **Database-per-service** | [infra/postgres](infra/postgres/README.md) | independent schemas, no cross-service reads. |
| **API Gateway (protocol translation)** | [gateway app](gateway/app/README.md) | HTTP→gRPC translation; `_STATUS_MAP` is the inverse of the servicers'. |
| **Long-lived channels** | gateway `lifespan` holds channels open → [gateway app](gateway/app/README.md) | HTTP/2 multiplexing; avoids per-request connection setup. |
| **Health checking** | standard gRPC health service → [users app](services/users/app/README.md) | orchestrators probe `SERVING` via a well-known protocol. |
| **Retries + backoff (selective)** | `services/orders/app/clients.py` → [orders app](services/orders/app/README.md) | retry only *retriable* codes (`UNAVAILABLE`/`DEADLINE_EXCEEDED`), never business errors. |
| **Correlation-ID tracing** | `CorrelationInterceptor` forwards `x-request-id` metadata | one id threads across RPC hops. |
| **Price-snapshot immutability** | `OrderItem.unit_price_cents` → [orders app](services/orders/app/README.md) | order records the price at purchase time. |
| **Money as integer cents** | [products app](services/products/app/README.md) | no float rounding in money. |

See [04-system-design/architectural_notes.md](../../04-system-design/architectural_notes.md).

## DSA (genuine touch-points only)

| Concept | Where | Why |
|---------|-------|-----|
| **Hashing** | bcrypt in `services/users/app/security.py` → [users app](services/users/app/README.md) | salted one-way hash; JWT signing is keyed-hash (HMAC). |
| **Binary serialization / varint encoding** | Protobuf wire format ([protos](protos/README.md)) | field numbers + varint-encoded integers — a compact binary encoding scheme (vs. JSON text). |
| **Hash-map / set lookup** | unique-key lookups (email, sku) | O(1)-ish uniqueness checks. |
| **Pagination (offset/limit)** | `list(limit, offset)` in every repository | bounded slices over an ordered collection. |

> Trees, graphs, sorting, DP, etc. are **not** exercised here — study those in
> [01-dsa](../../01-dsa/). This repo is where **patterns** + **system design**
> (and gRPC's contract-first, code-generation model) live in real code.

---

## Advanced patterns not yet applied here

This repo is a deliberate **baseline** (synchronous, orchestrated, one DB per
service). The production patterns it does **not** yet demonstrate — Circuit
Breaker, Saga with compensation, idempotency keys, cache-aside, event-driven
messaging, transactional outbox, read replicas, sharding, CQRS, TLS/mTLS, and
wiring the ELK platform — are documented as reference (where each would slot into
*this* system, with sketches and links to the runnable curriculum versions) in:

> **[../ADVANCED-PATTERNS.md](../ADVANCED-PATTERNS.md)**
