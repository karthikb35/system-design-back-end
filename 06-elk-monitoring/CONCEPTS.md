# Concept map → live code

Reverse index: where the **centralized-logging / observability** ideas from this
folder show up as running code in the three protocol microservice repos.

> Code → concept (the other direction) lives in each repo's `CONCEPTS.md`:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

The app-side half of ELK — the part that produces well-formed, correlated logs —
is implemented in every service's `observability.py`.

| Concept (this folder) | Live example |
|-----------------------|--------------|
| **Structured (JSON) logging** | JSON formatter replacing the default handler → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) (§ observability) |
| **Correlation IDs in a `contextvar`** | id survives across `await`, reachable by the formatter without threading → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Correlation across microservices** | `x-request-id` forwarded on every outbound call/RPC → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md); gRPC via interceptor metadata → [grpc users app](../protocol-microservices/grpc-ecommerce/services/users/app/README.md) |
| **Request timing / access logs** | each request logged with method → status + duration → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |

## Honest scope

The **platform** half of this folder — Elasticsearch, Kibana, retention,
backpressure ([docker-compose.yml](docker-compose.yml),
[architectural_notes.md](architectural_notes.md)) — is **not** wired into the
protocol repos; they emit the structured, correlated logs an ELK/OpenSearch stack
would ingest, but shipping those logs (Filebeat/Logstash) is left to this folder.
That boundary is exactly the "App-Side vs Deployment" split in your notes.
