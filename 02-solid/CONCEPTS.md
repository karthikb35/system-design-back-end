# Concept map → live code

Reverse index: where the **SOLID** principles from this folder show up as running
code in the three protocol microservice repos.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

The three repos are a **single, controlled experiment for SOLID**: the *same*
service/repository/model layers are reused unchanged behind three different
transport adapters (REST routers, gRPC servicer, GraphQL schema). That reuse *is*
the proof of the principles.

| Principle | Live example | Why it demonstrates the principle |
|-----------|--------------|-----------------------------------|
| **SRP** | layered split → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) | router/service/repository/models each have exactly one reason to change. |
| **OCP** | same service layer, new adapter per protocol → all three repos' `services/*/app/service.py` | open for extension (add a protocol), closed for modification (rules untouched). |
| **LSP** | fakes substitute for real clients/servers in tests → [grpc orders tests](../protocol-microservices/grpc-ecommerce/services/orders/tests/README.md) | a stand-in honours the same contract as the real collaborator. |
| **ISP** | narrow per-concern schemas; GraphQL clients request only needed fields → [graphql users app](../protocol-microservices/graphql-ecommerce/services/users/app/README.md) | callers don't depend on fields they don't use. |
| **DIP** (the load-bearing one) | service depends on the repository *abstraction* + injected clients → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) | high-level policy never imports low-level transport/DB detail. |

**Tie-in to your notes:** the "Dependency Inversion is the load-bearing one"
section of [architectural_notes.md](architectural_notes.md) is exactly what lets
the business logic stay identical across REST/gRPC/GraphQL — swapping the outer
adapter never touches the inner core.
