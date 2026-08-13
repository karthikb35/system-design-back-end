# FastAPI Advanced Architecture — Architectural Notes

## The core idea: layers with inward-pointing dependencies

A FastAPI app that a team can own for years is not "routes with logic in them."
It is layered, and the dependencies point **inward** (Dependency Inversion
applied to a web service):

```
HTTP Router  →  Service (business logic)  →  Repository  →  Datastore
  (thin)          (pure Python, no HTTP)      (abstraction)
```

- **Router** — translates HTTP to domain calls and domain errors to HTTP status
  codes. It should be *thin*: no business rules, no SQL.
- **Service** — the business logic. Crucially it **imports no FastAPI**. This is
  what makes rules unit-testable without a server and reusable from a worker,
  CLI, or gRPC handler.
- **Repository** — an *abstraction* over persistence. The service depends on the
  interface; you inject an in-memory repo in tests and a Postgres repo in prod.

The reference `_self_test()` proves the payoff: the entire business logic is
tested with **no HTTP and no database**. That speed and isolation is the whole
point.

## Dependency Injection is a first-class FastAPI feature

`Depends()` is DI built into the framework. Benefits:

- **Testability** — override a dependency in tests with `app.dependency_overrides`.
- **Composability** — dependencies can depend on other dependencies (auth →
  current user → permission check), forming a graph FastAPI resolves per request.
- **Lifecycle** — `yield` dependencies run setup before and teardown after the
  request (open/close a DB session per request).

Keep the **composition root** — where concrete repos/clients are bound — at the
edge (the `lifespan` handler and the `get_*` providers). That single seam is
where "in-memory vs Postgres" is decided; everything else stays ignorant.

## `lifespan` over the old startup/shutdown events

Use the `lifespan` async context manager to acquire resources on startup (DB
connection pool, cache client, message-broker producer) and release them on
shutdown. Doing this once at boot — not per request — is what lets the app
handle high concurrency: connection *pools* are shared, not recreated.

## async correctness: the number-one FastAPI footgun

FastAPI runs `async def` routes on a single event loop. **A blocking call inside
an `async` route blocks the entire event loop**, stalling *all* concurrent
requests — a self-inflicted outage.

- Use `async` libraries for I/O (`asyncpg`, `httpx`, async SQLAlchemy).
- If you must call blocking/CPU-bound code, offload it (`run_in_threadpool`, a
  process pool, or a background worker). Or define the route as plain `def` —
  FastAPI runs `def` routes in a threadpool automatically.
- CPU-bound work does not belong on the event loop at all; push it to a queue
  (see Event-Driven, pillar 08).

## Pydantic: validation and the contract boundary

Pydantic models are your **trust boundary**. Everything crossing into the system
is validated and coerced at the edge, so inner layers can assume clean data
(this is "validate at the boundary," not everywhere). Separate the wire schemas
(`UserCreate`, `UserOut`) from internal/DB models so the public contract and the
storage schema can evolve independently — and so you never accidentally leak an
internal field (password hash!) by returning a DB model directly.

## Cross-cutting concerns via middleware & dependencies

- **Middleware** — request logging, correlation-ID injection, timing, GZip.
  (Correlation IDs are the hook into ELK, pillar 06.)
- **Dependencies** — auth, rate limiting, feature flags, DB session per request.
- **Exception handlers** — map domain exceptions to consistent error responses in
  one place, so routers stay thin.

## Production checklist (the operability that separates senior work)

- Health/readiness endpoints (`/healthz`) for orchestrators and load balancers.
- Structured JSON logging with correlation IDs (pillar 06).
- Timeouts on every outbound call + circuit breakers (pillar 03).
- Graceful shutdown draining in-flight requests via `lifespan`.
- Config from environment (12-factor), secrets never in code.
- Pagination and payload-size limits on list endpoints (unbounded N is an
  outage waiting to happen — see pillar 01).
