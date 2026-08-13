# Concept map → live code

Reverse index: where the **Python language features** from this folder are used
in the three protocol microservice repos. This folder is language fundamentals, so
the mappings are lighter than `02`–`10`, but the repos show these features in
production shape.

> Each repo's own `CONCEPTS.md` maps code → concept:
> [rest](../protocol-microservices/rest-ecommerce/CONCEPTS.md) ·
> [grpc](../protocol-microservices/grpc-ecommerce/CONCEPTS.md) ·
> [graphql](../protocol-microservices/graphql-ecommerce/CONCEPTS.md).

---

| Feature (this folder) | Live example |
|-----------------------|--------------|
| **async/await, coroutines** | every handler, DB call, and client call is a coroutine → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Context managers (`async with`)** | request-scoped DB sessions and HTTP clients are always closed → [graphql users app](../protocol-microservices/graphql-ecommerce/services/users/app/README.md) |
| **Decorators** | `@lru_cache`, FastAPI route decorators, `@strawberry.type/@field` → [graphql users app](../protocol-microservices/graphql-ecommerce/services/users/app/README.md) |
| **Type hints / dataclass-like models** | typed Pydantic schemas, SQLAlchemy `Mapped[...]`, Strawberry types → [rest users app](../protocol-microservices/rest-ecommerce/services/users/app/README.md) |
| **Classmethods as factories** | `User.from_model` / `Product.from_dict` map rows/JSON to wire types → [graphql gateway app](../protocol-microservices/graphql-ecommerce/gateway/app/README.md) |
| **Exceptions & custom exception types** | domain exceptions (`EmailAlreadyExists`, `InsufficientStock`) drive transport error mapping → [rest orders app](../protocol-microservices/rest-ecommerce/services/orders/app/README.md) |

Read the fundamentals in this folder's `.py` files first, then see the same
constructs carrying real weight in the services.
