# Concept map → live code

Reverse index: where the **FastAPI architecture** ideas from this folder show up
as running code. All three protocol repos are FastAPI apps (the gRPC one wraps its
gateway in FastAPI too), so this folder maps most directly of all.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

| Concept (this folder) | Live example |
|-----------------------|--------------|
| **Layers with inward-pointing dependencies** | the module-dependency diagram → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Dependency Injection as a first-class feature** | `Depends` + `dependency_overrides` for fakes → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md); GraphQL `context_getter` → [graphql orders app](../protocol-microservices/graphql-ecommerce/services/orders/app/README.md) |
| **`lifespan` over startup/shutdown events** | table creation + channel/client open-close → [grpc gateway app](../protocol-microservices/grpc-ecommerce/gateway/app/README.md) |
| **async correctness** | async SQLAlchemy sessions, `httpx.AsyncClient`, `grpc.aio` throughout → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Pydantic as the contract boundary** | request/response schemas validate at the edge → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Cross-cutting concerns via middleware** | correlation-id + JSON logging middleware → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Testability without infrastructure** | in-memory SQLite + ASGI transport + fakes → [rest orders tests](../protocol-microservices/rest-ecommerce/services/orders/tests/README.md) |

**Tie-in:** the "async correctness footgun" section of
[architectural_notes.md](architectural_notes.md) is why every DB call, HTTP call,
and RPC in these repos is `await`-ed on an async driver — no sync call ever blocks
the event loop.
