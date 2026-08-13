# System Design in FastAPI — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. A "charge card" endpoint sometimes double-charges customers. What's the root cause and the fix?

**Deep dive.** The network guarantees *at-least-once* delivery: clients, load
balancers, and proxies all retry on timeout, and a request can succeed on the
server while the *response* is lost — the client then retries a charge that
already happened. With nothing to deduplicate on, the retry charges again. The
fix is an **idempotency key**: the client sends a unique key per logical
operation; the server performs the charge the first time and stores the response
keyed by it, then *replays* that stored response on any retry with the same key,
without re-charging. This converts at-least-once delivery into exactly-once
*effect*. Critically, persist the result *before* acknowledging, so a
crash-then-retry is still safe.

---

### Q2. Why is doing slow work synchronously on the request path an architectural problem, and what are the options for moving it off?

**Deep dive.** Slow inline work (PDF render, email, third-party call) inflates p99
latency, holds the worker/connection for its full duration (reducing throughput),
and couples the client's success to the slow task's success. Options, in
increasing robustness: **FastAPI `BackgroundTasks`** (simple, in-process — runs
after the response, but is lost if the process dies and doesn't survive restarts);
a **task queue** (Celery/RQ/Arq — durable, retryable, scalable across workers); or
**publishing an event** to a broker for a separate consumer (fully decoupled,
event-driven). The right choice depends on durability needs: `BackgroundTasks` for
best-effort fire-and-forget, a queue/broker when the work *must* eventually happen.

---

### Q3. Apply CAP to this payment service. During a network partition, what do you choose?

**Deep dive.** Payments demand correctness, so you choose **CP** (consistency over
availability): during a partition, it's better to reject or hold a transaction
than to risk a double-spend or a divergent ledger that must later be reconciled by
hand. That means the write path depends on a strongly-consistent store and will
return errors rather than accept ambiguous writes when it can't guarantee
correctness. The complement is PACELC: even without a partition, you're trading
latency for consistency — synchronous strong consistency costs p99 latency on
every charge, which you accept for money-handling. Contrast with a product-view
counter, where you'd pick AP and tolerate staleness.

---

### Q4. Where should the idempotency store live, what's its lifecycle, and what are the failure modes?

**Deep dive.** It should be a fast, shared, durable store — typically Redis or a
DB table — *shared across all instances*, because a per-process dict doesn't
deduplicate across a fleet (a retry hitting a different instance would re-charge).
Entries carry a **TTL** matched to the retry window (hours, not forever) to bound
memory. Failure modes: (a) storing the response *after* acking, so a crash between
charge and store loses the dedupe record — persist before returning; (b) racing
concurrent retries with the same key — use an atomic set-if-absent (`SET NX`) or a
DB unique constraint so only one wins; (c) storing a *failed* attempt as success —
be deliberate about whether errors are cached.

---

### Q5. Do a back-of-the-envelope estimate for this service (5M charges/day) and identify the bottleneck.

**Deep dive.** 5M / 86,400 ≈ 58 charges/sec average; design for peak at 3–5×, so
~200–300 writes/sec. That's a modest write rate a single well-tuned primary
handles, so the bottleneck is unlikely to be raw DB write throughput — it's more
likely the **synchronous downstream work** (payment provider latency, receipt
generation) inflating latency and tying up workers, plus correctness under retry.
The math tells you the design priorities here are *idempotency and offloading slow
work*, not sharding. The point of the estimate is to reveal that the scaling
problem is latency/correctness, not volume — so you don't over-engineer storage.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. Networks provide which delivery guarantee by default, forcing idempotency?**
- A) exactly-once
- B) at-most-once
- C) at-least-once
- D) ordered-once

**2. An idempotency key makes a retried charge safe by:**
- A) encrypting the request
- B) replaying the stored response without re-executing the side effect
- C) rejecting all retries
- D) charging a smaller amount

**3. You must persist the idempotency result:**
- A) after returning the response
- B) before acknowledging the response
- C) only on failure
- D) never — keep it in memory

**4. A per-process in-memory idempotency dict fails in production because:**
- A) it's too slow
- B) it doesn't deduplicate across multiple server instances
- C) it violates SOLID
- D) dicts can't store responses

**5. For a payment service during a network partition, you choose:**
- A) AP — availability over consistency
- B) CP — consistency over availability
- C) neither — CAP doesn't apply
- D) both simultaneously

### Answer Key
1. **C** — at-least-once delivery is why retries duplicate.
2. **B** — replay the stored result; run the side effect once.
3. **B** — persist before acking so crash-then-retry is safe.
4. **B** — a local dict can't dedupe across a fleet; use a shared store.
5. **B** — payments favor correctness (CP).

---

## Part 3 — Gotchas Checklist

- **Assume at-least-once delivery.** Any endpoint with a side effect (charge,
  ship, post) needs an idempotency key or naturally-idempotent operation.
- **Persist the idempotency record BEFORE responding**, or a crash between the
  effect and the store re-runs the effect on retry.
- **Use a shared, TTL'd idempotency store** (Redis/DB), not a per-process dict —
  otherwise retries to other instances duplicate.
- **Guard concurrent retries** with an atomic set-if-absent / unique constraint,
  or two in-flight retries both execute.
- **`BackgroundTasks` are best-effort** and in-process: they run after the
  response but are lost on crash/restart. Use a durable queue when the work must
  happen.
- **Don't do slow/CPU-bound work on the request path** — it inflates p99 and
  starves workers.
- **Do the capacity math first** — it tells you whether the problem is volume
  (shard) or latency/correctness (idempotency + offload), preventing
  over-engineering.
- **Decide error caching explicitly** — caching a transient failure as the
  permanent result under an idempotency key is a nasty, subtle bug.
