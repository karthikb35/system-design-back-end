# Concept map → live code

This folder is otherwise a placeholder, but the three protocol microservice repos
already contain concrete **concurrency** examples worth studying. (Several inline
callouts in those repos link back here.)

> Each repo's own `CONCEPTS.md` maps code → concept:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

| Concurrency concept | Live example |
|---------------------|--------------|
| **Check-then-act race (read-modify-write)** | `reserve_stock` reads stock, checks, then decrements — the textbook oversell hazard; fix is an atomic conditional `UPDATE ... WHERE stock >= :qty` or a row lock → [rest products app](../protocol-microservices/rest-ecommerce/services/products/app/README.md) |
| **async/await event loop (no blocking calls)** | every DB call, HTTP call, and RPC is `await`-ed on an async driver so one thread serves many concurrent requests → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Deadlines / timeouts** | per-call timeout on downstream calls so a slow dependency can't hang checkout → [grpc orders app](../protocol-microservices/grpc-ecommerce/services/orders/app/README.md) |
| **`contextvar` for per-request state** | correlation id lives in a `ContextVar`, correct under concurrent `await`-interleaved requests → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Shared-connection gotcha** | in-memory SQLite uses a `StaticPool` (one shared connection) so concurrent test sessions see the same schema → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Retry backoff under contention** | exponential backoff avoids thundering-herd retries against a struggling downstream → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) |

The single most interview-relevant example is the **oversell race** in
`reserve_stock`: a correct-looking sequential read-modify-write that breaks under
two simultaneous checkouts.
