# Event-Driven Systems in FastAPI — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. An order endpoint synchronously calls inventory, email, and analytics. What's wrong and what does publishing an event fix?

**Deep dive.** Synchronous chaining creates **temporal and logical coupling**: the
endpoint must know every downstream, the client waits for all of them, and a slow
or failing *non-critical* step (email) makes the *critical* operation (placing the
order) slow or fail. Adding a new reaction means editing the tested endpoint.
Publishing an `OrderPlaced` **event** inverts this: the endpoint does only its own
critical work and emits a fact; independent consumers react asynchronously. Now
email being down doesn't fail the order (it retries / dead-letters), you add a
fraud-check consumer without touching the producer, and the client isn't blocked
on downstream work. The trade-off is eventual consistency and more moving parts.

---

### Q2. Your broker delivers at-least-once. What must every consumer guarantee, and how?

**Deep dive.** Every consumer must be **idempotent** — processing the same message
twice has the same effect as once. At-least-once means duplicates are inevitable
(producer retries, redeliveries, rebalances), so consumers dedupe on a unique
`event_id` (persisted in a DB table or a Redis set with TTL) and no-op on repeats,
or design the operation to be naturally idempotent (`set status = shipped` rather
than `balance += 1`). Combining at-least-once delivery with idempotent consumers
yields exactly-once *effect*, which is the achievable form of "exactly-once" —
brokers can't give you true end-to-end exactly-once for free. Idempotency is the
single most important correctness property in an event system.

---

### Q3. Compare choreography and orchestration. When do you pick each?

**Deep dive.** In **choreography**, services react to each other's events with no
central coordinator — maximal decoupling, great for simple few-step flows, but the
overall business process becomes emergent and hard to see or change as steps
multiply ("who does what?"). In **orchestration**, a central orchestrator directs
each step — the workflow lives in one place, easy to reason about and modify, at
the cost of a component coupled to all participants. Rule of thumb: choreography
between loosely-coupled bounded contexts; orchestration (often a **saga
orchestrator**) inside a complex, multi-step workflow that needs explicit control
and error handling. Many systems use both at different granularities.

---

### Q4. How do you implement a transaction that spans three services (no distributed 2PC)?

**Deep dive.** Use a **saga**: a sequence of local transactions, each publishing an
event that triggers the next step. If a step fails, you run **compensating
transactions** to undo the completed steps in reverse order (reserve inventory →
charge payment fails → *release* inventory). This achieves eventual consistency
without two-phase commit, which doesn't scale and creates cross-service locking.
Sagas come in two flavors — choreographed (each service listens and reacts) or
orchestrated (a coordinator drives steps and compensations). Compensations must be
idempotent and you must design for the awkward case where the *undo* itself fails
(alerting, manual intervention, retries).

---

### Q5. A single "poison" message keeps failing and blocks your consumer. What do you do, and how do you preserve ordering?

**Deep dive.** Retry a **bounded** number of times, then route the message to a
**Dead-Letter Queue** so the rest of the stream keeps flowing, and continue. The
DLQ preserves the message for inspection, fixing, and replay, and its depth should
be an alerting signal. Blocking the whole partition on one bad record turns a
single failure into an outage. For **ordering**: global ordering across a topic is
expensive and kills throughput; brokers like Kafka guarantee order only *within a
partition*, so you choose a partition key (e.g., `order_id`) that keeps all events
for one entity on the same partition (ordered) while different entities process in
parallel across partitions — the event-stream analogue of a shard key.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. Synchronously calling every downstream service from an endpoint causes:**
- A) idempotency
- B) tight temporal/logical coupling and cascading failure
- C) eventual consistency
- D) horizontal scaling

**2. Because brokers deliver at-least-once, consumers must be:**
- A) synchronous
- B) idempotent
- C) stateless only
- D) single-threaded

**3. "Exactly-once effect" in practice is achieved by:**
- A) a magic broker setting
- B) at-least-once delivery + idempotent consumers
- C) at-most-once delivery
- D) two-phase commit

**4. A distributed transaction across services without 2PC uses the:**
- A) Outbox pattern
- B) Saga pattern with compensating transactions
- C) Singleton pattern
- D) Strategy pattern

**5. A repeatedly failing "poison" message should be:**
- A) retried forever
- B) sent to a dead-letter queue after bounded retries
- C) silently dropped
- D) logged with print()

### Answer Key
1. **B** — sync chaining couples services and cascades failure.
2. **B** — at-least-once ⇒ consumers must dedupe (idempotent).
3. **B** — at-least-once + idempotency = exactly-once effect.
4. **B** — sagas coordinate via compensations, no 2PC.
5. **B** — bounded retries then DLQ, keep the stream flowing.

---

## Part 3 — Gotchas Checklist

- **Don't chain services synchronously** for non-critical work — publish an event
  so a slow/failed consumer can't fail or slow the critical path.
- **Assume at-least-once delivery**; make every consumer **idempotent** (dedupe on
  `event_id` or use naturally idempotent operations).
- **Events are past-tense facts** (`OrderPlaced`), not commands (`PlaceOrder`) —
  facts keep consumers decoupled and independently evolvable.
- **The dual-write trap**: don't write the DB then publish in two steps — a crash
  between loses the event. Use the Transactional Outbox (see topic 07).
- **Handle poison messages** with bounded retries + a dead-letter queue, and alert
  on DLQ depth; never block the partition on one bad record.
- **Ordering is per-partition**, not global — pick a partition key (e.g.
  `order_id`) to keep an entity's events ordered while parallelizing others.
- **Compensations must be idempotent**, and you must plan for a failed undo.
- **Eventual consistency is the cost** of decoupling — make it explicit to
  stakeholders; it's not the right model for operations needing an immediate
  consistent answer.
