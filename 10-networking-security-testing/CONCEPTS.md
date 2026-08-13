# Concept map → live code

This folder is otherwise a placeholder, but the three protocol microservice repos
are a ready-made lab for **networking, security, and testing**. (Several inline
callouts in those repos link back here.)

> Each repo's own `CONCEPTS.md` maps code → concept:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

## Networking

| Concept | Live example |
|---------|--------------|
| **HTTP/1.1 + JSON vs HTTP/2 + Protobuf vs SDL** | same domain, three transports — compare directly across [rest](../protocol-microservices/rest-ecommerce/README.md), [grpc](../protocol-microservices/grpc-ecommerce/README.md), [graphql](../protocol-microservices/graphql-ecommerce/README.md) |
| **Connection reuse / multiplexing** | long-lived gRPC HTTP/2 channels opened once at startup → [grpc gateway app](../protocol-microservices/grpc-ecommerce/gateway/app/README.md) |
| **Protocol translation at the edge** | gateway speaks REST/JSON outward, gRPC inward → [grpc gateway app](../protocol-microservices/grpc-ecommerce/gateway/app/README.md) |

## Security

| Concept | Live example |
|---------|--------------|
| **Password hashing (bcrypt, salted, slow)** | never store plaintext; truncate to 72 bytes → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **JWT (signed token, stateless auth)** | signature proves integrity so peers trust the claims → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Not leaking secrets** | the user output type has no password field by construction → [graphql users app](../protocol-microservices/graphql-ecommerce/services/users/app/README.md) |

> Note: the demos use `insecure_channel` / plain HTTP for local simplicity — **TLS
> termination and mTLS** are the obvious hardening step this folder would add.

## Testing

| Concept | Live example |
|---------|--------------|
| **In-process testing without a network** | ASGI transport + in-memory SQLite → [rest orders tests](../protocol-microservices/rest-ecommerce/services/orders/tests/README.md) |
| **Test doubles / fakes** | fake downstream services injected in place of real ones → [graphql gateway tests](../protocol-microservices/graphql-ecommerce/gateway/tests/README.md) |
| **Fake in-process servers** | real gRPC clients wired to fake in-process gRPC servers → [grpc orders tests](../protocol-microservices/grpc-ecommerce/services/orders/tests/README.md) |
| **Deterministic schema per test** | `drop_all`/`create_all` between tests → [rest users tests](../protocol-microservices/rest-ecommerce/services/users/tests/README.md) |

Across all three repos that's 84 passing tests (REST 26 · gRPC 29 · GraphQL 29),
each exercising the real code path with the network faked out.
