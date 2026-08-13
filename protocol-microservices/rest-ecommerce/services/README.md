# `services/` — the microservices

This folder holds the three independent backend services. Each is a **separately
deployable unit** with its own code, its own database, its own Dockerfile, and
its own tests. They never share a database or import each other's code — they
communicate only over HTTP.

```mermaid
flowchart TD
    subgraph services/
      U["users/<br/>accounts + auth"]
      P["products/<br/>catalog + stock"]
      O["orders/<br/>checkout orchestration"]
    end
    O -->|"HTTP: is buyer real?"| U
    O -->|"HTTP: price + reserve"| P
    U --> UDB[(users_db)]
    P --> PDB[(products_db)]
    O --> ODB[(orders_db)]
```

| Service | Owns | Talks to | README |
|---------|------|----------|--------|
| `users/` | accounts, login/JWT | — (leaf) | [users/README.md](users/README.md) · [app](users/app/README.md) |
| `products/` | catalog, stock reservation | — (leaf) | [products/README.md](products/README.md) · [app](products/app/README.md) |
| `orders/` | orders, checkout flow | Users + Products | [orders/README.md](orders/README.md) · [app](orders/app/README.md) |

---

## The pattern every service follows

```mermaid
flowchart TD
    R["app/routers/*<br/>HTTP boundary"] --> S["app/service.py<br/>business rules"]
    S --> Repo["app/repository.py<br/>SQL only"]
    Repo --> M["app/models.py<br/>ORM tables"]
    M --> DB[(its own database)]
```

- **Database-per-service:** decoupled schemas; a change in one never breaks another.
- **Layered:** each layer has one job and only depends inward — that's what makes
  the services independently testable (each `tests/` folder runs with no network).
- **Same shape, different domain:** learning one service teaches you all three.

Drill into any service's `app/` README for the line-by-line walkthrough.
