# FastAPI Advanced — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. A developer puts `time.sleep(2)` (or a blocking `requests.get`) inside an `async def` route. Describe exactly what happens under load.

**Deep dive.** FastAPI serves `async def` routes on a single event loop per
worker. A blocking call doesn't yield control back to the loop, so for its entire
duration the loop can process *no other requests* — including a trivial
`/health`. Under concurrency this serializes everything: 100 clients hitting a
2-second blocking route experience up to ~200 seconds of tail latency, and the
service appears "hung" even though CPU may be idle. It passes local testing
because a single sequential request never reveals the contention. The tell is that
throughput doesn't scale with concurrency and unrelated endpoints slow down when
one endpoint is busy.

---

### Q2. Give three correct ways to fix a blocking call in a FastAPI app and when to use each.

**Deep dive.** (1) **Use an async library and `await` it** — the ideal fix for
I/O: `httpx.AsyncClient`, `asyncpg`, async SQLAlchemy. The call yields to the loop
while waiting. (2) **Offload to a threadpool** with `run_in_threadpool` (or
`asyncio.to_thread`) when you're stuck with a synchronous library — the blocking
work runs on a worker thread, freeing the loop. (3) **Define the route as plain
`def`** — FastAPI automatically runs sync routes in its threadpool, so legacy
blocking handlers don't block the loop; simplest fix when the whole handler is
synchronous. For **CPU-bound** work, threads don't help much (the GIL) — use a
process pool or, better, push it to a background worker/queue.

---

### Q3. Why is the layered architecture (router → service → repository) worth the extra files in FastAPI?

**Deep dive.** It maps directly to testability and change isolation. The
**service** layer holds business logic and imports no framework, so it's
unit-testable in milliseconds without HTTP or a database, and reusable from a CLI
or worker. The **repository** is an abstraction over storage, so tests inject an
in-memory implementation and production injects Postgres — swapping either is a
one-line change at the composition root (DIP). The **router** stays thin:
translate HTTP to domain calls and domain errors to status codes. Fat routes fuse
HTTP, business, and persistence concerns, so every change is risky and every test
needs a live server. The extra files buy speed of change and speed of testing.

---

### Q4. Explain the role of `lifespan` and dependency injection in resource management.

**Deep dive.** Expensive resources — DB connection pools, HTTP clients, broker
producers — must be created **once** and shared, not per request, or you exhaust
the database's connection limit and add latency. The `lifespan` async context
manager acquires them at startup and releases them at shutdown (enabling graceful
drain). `Depends` then injects those shared resources (or a per-request DB session
derived from the pool) into routes, and lets you override them in tests via
`app.dependency_overrides`. Together they give correct lifecycle management and a
testing seam. The old per-request `create_engine()`/new-connection pattern is a
classic scaling bug.

---

### Q5. Why separate Pydantic input, output, and DB models, and how does this relate to security?

**Deep dive.** Separate models decouple the public API contract from internal
storage and control exposure. The **input** model is the validation/trust boundary
— data is validated and coerced at the edge so inner layers assume clean input.
The **output** (response) model determines exactly what's serialized, preventing
accidental leakage of sensitive fields (password hashes, internal flags, admin
booleans) that returning a DB object directly would expose. And keeping them
separate lets storage evolve (migrations) without breaking clients, and vice
versa. It's decoupling *and* a security control (explicit allow-list of exposed
fields via `response_model`), not mere duplication.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. A blocking `time.sleep()` inside an `async def` route:**
- A) only slows that one request
- B) blocks the entire event loop, stalling all concurrent requests
- C) is automatically offloaded by FastAPI
- D) raises an exception

**2. The idiomatic way to run a synchronous library call from an async route is:**
- A) call it directly
- B) `await run_in_threadpool(fn)` / `asyncio.to_thread`
- C) wrap it in a try/except
- D) add more workers only

**3. A plain `def` route in FastAPI is:**
- A) rejected at startup
- B) run in a threadpool so it doesn't block the loop
- C) run on the event loop like async
- D) slower than async always

**4. Expensive resources like DB pools should be created:**
- A) per request
- B) once, in `lifespan`, and shared via DI
- C) in every dependency
- D) at import time in a global with no cleanup

**5. A separate response_model prevents:**
- A) SQL injection
- B) leaking sensitive internal fields in the response
- C) event-loop blocking
- D) replication lag

### Answer Key
1. **B** — one event loop; blocking it stalls everything.
2. **B** — offload blocking work to a threadpool.
3. **B** — FastAPI runs sync routes in its threadpool.
4. **B** — create once in `lifespan`, inject via `Depends`.
5. **B** — response_model is an explicit output allow-list.

---

## Part 3 — Gotchas Checklist

- **Never block the event loop.** No `time.sleep`, `requests`, sync DB drivers, or
  heavy CPU directly inside `async def`. Use async libs, `run_in_threadpool`, or a
  `def` route.
- **CPU-bound work isn't fixed by threads** (GIL) — use a process pool or a
  background worker/queue.
- **`async def` + a sync DB driver is a trap** — either use an async driver or
  make the route `def`. Mixing them silently blocks the loop.
- **Create pools/clients once in `lifespan`**, not per request; close them on
  shutdown for graceful drain.
- **Don't return ORM/DB models directly** — use a `response_model` to avoid
  leaking sensitive fields and to decouple wire format from schema.
- **Validate at the boundary** with Pydantic; don't re-validate everywhere.
- **`BackgroundTasks` run in-process** and are lost on crash — use a durable queue
  when the work must complete.
- **Blocking bugs hide in local testing** — always load-test with concurrency, and
  watch whether unrelated endpoints slow down together.
