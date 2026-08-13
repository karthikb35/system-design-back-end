# Concept map → live code

Reverse index: the Orders checkout flow in the protocol repos is a deliberate
**orchestration** counter-example to this folder's event-driven material — which
makes it a useful "before" picture for the patterns you study here.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

| Concept (this folder) | Live example / relationship |
|-----------------------|-----------------------------|
| **Choreography vs Orchestration** | Orders is a synchronous **orchestrator** (it commands Users + Products) → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md). Your notes' *choreography* alternative would replace those calls with events. |
| **Retries & transient-failure handling** | bounded retries + backoff on downstream calls → [grpc orders app](../protocol-microservices/grpc-ecommerce/services/orders/app/README.md) |
| **Saga (distributed transaction)** | the flow validates → reserves → persists but does **not** compensate a partial failure — the exact gap a Saga fills, called out in [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) |

## Honest scope — this is the *synchronous* baseline

The protocol repos are intentionally **request/response**, not event-driven. None
of the following from [architectural_notes.md](architectural_notes.md) are present
yet — and seeing their absence is instructive:

- **Message broker, events-as-facts, delivery guarantees** — calls are synchronous
  RPC/HTTP, not published events.
- **DLQ / poison-message handling, ordering/partitioning** — no queue involved.
- **Saga with compensation** — the orchestrator's missing "release stock" step is
  the concrete thing to build to turn this baseline into a real Saga.

Use these repos to feel *why* teams move to event-driven designs: the synchronous
orchestrator couples Orders to the availability of Users and Products at request
time — precisely the coupling your notes' "decoupling in time and knowledge" fixes.
