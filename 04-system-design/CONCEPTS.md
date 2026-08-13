# Concept map → live code

Reverse index: where the **system-design** ideas from this folder show up as
running code in the three protocol microservice repos.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

## Ideas you can see running

| Concept | Live example |
|---------|--------------|
| **Database-per-service** | [rest infra/postgres](../protocol-microservices/rest-ecommerce/infra/postgres/README.md) — one Postgres, three isolated DBs |
| **API Gateway** | [rest gateway](../protocol-microservices/rest-ecommerce/gateway/app/README.md) (proxy + aggregate); [grpc gateway](../protocol-microservices/grpc-ecommerce/gateway/app/README.md) (protocol translation); [graphql gateway](../protocol-microservices/graphql-ecommerce/gateway/app/README.md) (graph stitching) |
| **Statelessness & load balancing** | JWT-carried identity, no server session → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md); stateless gateway → [rest gateway](../protocol-microservices/rest-ecommerce/gateway/app/README.md) |
| **Idempotency & immutability** | order price *snapshot* (`unit_price_cents`) → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) |
| **Resilience: retries + deadlines** | [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) (5xx/network only); [grpc orders app](../protocol-microservices/grpc-ecommerce/services/orders/app/README.md) (retry only `UNAVAILABLE`/`DEADLINE_EXCEEDED`) |
| **API composition vs N+1** | GraphQL field resolvers replace the aggregate endpoint but introduce the N+1 problem → [graphql gateway app](../protocol-microservices/graphql-ecommerce/gateway/app/README.md) |
| **Contract-first (IDL)** | `.proto` files + codegen → [grpc protos](../protocol-microservices/grpc-ecommerce/protos/README.md) |
| **Observability / correlation-id** | `x-request-id` threaded through every hop → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Money as integer cents** | [rest products app](../protocol-microservices/rest-ecommerce/services/products/app/README.md) |
| **Health checks** | `/health` + gateway fan-out; gRPC standard Health service → [grpc gateway](../protocol-microservices/grpc-ecommerce/gateway/app/README.md) |

## Honest gaps (in your notes, not yet in the repos)

- **CAP/PACELC, consistent hashing, caching layers** — discussed in
  [architectural_notes.md](architectural_notes.md) but not needed at this scale
  (single Postgres, no cache tier). The database-per-service split is where
  consistency trade-offs would first appear.
- **Idempotency keys** — the repos show immutable *snapshots* but not client-supplied
  idempotency keys on `placeOrder`; that's the natural next step from the
  "Idempotency" section of your notes.
