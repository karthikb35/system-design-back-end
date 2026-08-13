# Concept map → live code

Reverse index: where the ideas in this folder show up as **running code** in the
three protocol microservice repos. Studying a concept here? Jump straight to a
real example.

> Each repo also has its own `CONCEPTS.md` mapping the other direction (code →
> concept): [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

## Where DSA shows up

Honest scope: these are CRUD microservices, so they exercise **applied** DSA, not
algorithm-puzzle DSA. The genuine touch-points:

| Concept (this folder) | Live example |
|-----------------------|--------------|
| **Hashing** (one-way, salted) | bcrypt password hashing + JWT (keyed hash) → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Binary encoding / varint** | Protobuf wire format vs. JSON text → [grpc protos](../protocol-microservices/grpc-ecommerce/protos/README.md) |
| **Graph / tree traversal** | a GraphQL query is a tree the server walks, resolving child nodes on demand → [graphql gateway app](../protocol-microservices/graphql-ecommerce/gateway/app/README.md) |
| **Hash-map / set membership** | unique-key lookups (email, sku) backed by indexed columns → [rest products app](../protocol-microservices/rest-ecommerce/services/products/app/README.md) |
| **Pagination (bounded slice)** | `list(limit, offset)` in every repository → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |

## What these repos do **not** demonstrate

Trees, balanced BSTs, heaps, sorting, dynamic programming, and graph algorithms
(BFS/DFS/Dijkstra) are **not** exercised by an e-commerce CRUD domain. Keep those
in [production_code.py](production_code.py) and
[interview_questions.md](interview_questions.md) here — the repos are the place to
see *applied* hashing/indexing/pagination in production shape.
