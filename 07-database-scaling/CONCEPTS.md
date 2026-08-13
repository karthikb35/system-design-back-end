# Concept map → live code

Reverse index: where the **database-scaling** ideas from this folder show up (and,
just as importantly, where they *don't yet*) in the three protocol microservice
repos.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

| Concept (this folder) | Live example |
|-----------------------|--------------|
| **Database-per-service (functional partitioning)** | one Postgres, three isolated DBs, each service scoped to its own URL → [rest infra/postgres](../protocol-microservices/rest-ecommerce/infra/postgres/README.md) |
| **Indexing for lookups** | unique/indexed `email` and `sku` columns → [rest products app](../protocol-microservices/rest-ecommerce/services/products/app/README.md) |
| **Pagination** | `ORDER BY ... LIMIT ... OFFSET ...` in every repository → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Connection pooling** | async engine pool per process (StaticPool only for in-memory tests) → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |

## Honest gaps (your notes go much further than the repos)

The repos sit on the **first rung** of the scaling ladder from
[architectural_notes.md](architectural_notes.md). Not yet implemented:

- **Read replicas / replication lag** — single primary per service.
- **Sharding** — no horizontal partitioning; UUID string PKs would make hash-based
  sharding straightforward later.
- **Transactional Outbox / dual-write** — the Orders service writes locally and
  calls peers synchronously; an outbox is the fix if those become events (see
  [08-event-driven-systems](../08-event-driven-systems/CONCEPTS.md)).
- **CQRS** — one model serves reads and writes.

The database-per-service boundary is the seam along which every one of these would
later be introduced.
