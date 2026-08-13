# `docs/` — architecture documentation

System-level documentation for the REST e-commerce repo. These explain the
**whole** system; each folder's own README explains that folder's code.

```mermaid
flowchart LR
    A["ARCHITECTURE.md<br/>the static picture"] --- B["REQUEST-LIFECYCLE.md<br/>the moving picture"]
```

| Document | Answers |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | What are the pieces, how do they fit, and why database-per-service? The static structure. |
| [REQUEST-LIFECYCLE.md](REQUEST-LIFECYCLE.md) | What happens, step by step, when a request flows through the system? The dynamic behaviour. |

## Where to go next

```mermaid
flowchart TD
    Root["../README.md<br/>quick start + protocol comparison"] --> Docs["docs/ (you are here)"]
    Docs --> Svc["../services/README.md<br/>the three services"]
    Svc --> App["each services/*/app/README.md<br/>line-by-line code"]
    Root --> GW["../gateway/README.md<br/>the public entry point"]
```

- Start with [ARCHITECTURE.md](ARCHITECTURE.md) for the big picture.
- Then [REQUEST-LIFECYCLE.md](REQUEST-LIFECYCLE.md) to see a request move.
- Then drill into [../services/README.md](../services/README.md) and each
  service's `app/` README for the code itself.
