# `infra/` — infrastructure assets

Supporting files for the environment. No application code — just the database
bootstrap.

```mermaid
flowchart LR
    Compose["docker-compose.yml"] -->|mounts| Init["infra/postgres/init-databases.sql"]
    Init -->|on first start| PG[("Postgres<br/>users_db · products_db · orders_db")]
```

| Path | Purpose |
|------|---------|
| [postgres/](postgres/README.md) | creates the three per-service databases on first Postgres startup |

See [postgres/README.md](postgres/README.md) for details.
