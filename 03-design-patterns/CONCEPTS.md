# Concept map → live code

Reverse index: where the **design patterns** from this folder show up as running
code in the three protocol microservice repos.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

## Patterns you can see running

| Pattern | Live example | Note |
|---------|--------------|------|
| **Repository** | every `services/*/app/repository.py` → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) | all SQL behind a collection interface. |
| **Adapter** | REST routers · gRPC [servicer](../protocol-microservices/grpc-ecommerce/services/users/app/README.md) · GraphQL [schema](../protocol-microservices/graphql-ecommerce/services/users/app/README.md) | three adapters over one service layer — the clearest Adapter demo in the whole workspace. |
| **Facade / API Gateway** | [rest gateway](../protocol-microservices/rest-ecommerce/gateway/app/README.md) · [grpc gateway](../protocol-microservices/grpc-ecommerce/gateway/app/README.md) · [graphql gateway](../protocol-microservices/graphql-ecommerce/gateway/app/README.md) | one edge hides three services; GraphQL's version *stitches a graph*. |
| **Proxy (remote)** | gRPC generated stubs → [grpc protos](../protocol-microservices/grpc-ecommerce/protos/README.md) | a local stub whose calls run on a remote server. |
| **Strategy** | retry/backoff policy → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) | interchangeable policy wrapped around the network call. |
| **Interceptor / Chain of Responsibility** | gRPC `CorrelationInterceptor`; FastAPI middleware → [grpc users app](../protocol-microservices/grpc-ecommerce/services/users/app/README.md) | cross-cutting logic wraps every request/RPC. |
| **DTO + Mapper** | Pydantic schemas / `_to_reply` / `from_model` → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) | wire shape decoupled from ORM; password never mapped out. |
| **Singleton (cached factory)** | `@lru_cache get_settings()` → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) | one config object per process. |
| **Orchestration** | Orders checkout flow → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) | coordinates a multi-service transaction. |

## Honest gaps (patterns your notes cover but the repos don't implement)

- **Circuit Breaker** — the "pattern GoF forgot" in
  [architectural_notes.md](architectural_notes.md). The repos implement **retries
  with backoff** but stop short of a full breaker (open/half-open state). The
  Orders `clients.py` retry is where you'd add one.
- **Saga (with compensation)** — the Orders flow is a synchronous *orchestrator*;
  it does **not** yet compensate a partial failure. That known simplification is
  called out in the orders app README and is the natural place to add a Saga.
