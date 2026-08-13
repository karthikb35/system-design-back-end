# Database Scaling in FastAPI — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. What is the N+1 query problem, why is it so common with ORMs, and how do you fix it?

**Deep dive.** N+1 is: one query to fetch a list of N rows, then one *additional*
query per row to fetch a related object — N+1 round trips total. It's rampant with
ORMs because lazy-loading a relationship (`order.customer`) looks like a simple
attribute access but silently fires a query each time, hidden inside a loop. At
1,000 rows that's 1,001 round trips, each paying network + query-planning
overhead — an endpoint that's fast on 5 rows and times out on 5,000. Fixes: eager
-load the relationship in one query (SQLAlchemy `selectinload`/`joinedload`), or
collect the distinct foreign keys and issue a single `IN (...)` batch, turning
O(n) round trips into O(1). Detection: log/count queries per request and alert on
outliers.

---

### Q2. Walk me up the database scaling ladder for a read-heavy app. Where does sharding fit?

**Deep dive.** Cheapest first, stop when the bottleneck is solved. (1) **Optimize**
— add indexes, kill N+1s, tune slow queries, size the connection pool; often
enough alone. (2) **Cache** hot reads (Redis) to offload the DB. (3) **Read
replicas** — route reads off the primary to scale reads horizontally. (4)
**Shard/partition** — only when *writes* or *storage* exceed a single primary,
because it's the most operationally complex step (cross-shard queries,
rebalancing). Sharding is last, not first; jumping to it prematurely adds huge
complexity for a problem an index or a cache would have solved.

---

### Q3. You route reads to a replica and users report "I saved it but it's not there." Explain and mitigate.

**Deep dive.** Replicas replicate asynchronously, so they lag the primary by
milliseconds to seconds. A user who writes to the primary then immediately reads
from a lagging replica sees stale data — the **read-your-writes** problem.
Mitigations: route reads that *must* see the latest write back to the **primary**
(e.g., right after the user's own write, or within a short sticky window); track
the write's log position and read from a replica only once it has caught up; or
accept staleness where the domain tolerates it (a public view count). The key
skill is classifying which reads need freshness and paying the primary-routing
cost only for those, rather than treating all reads identically.

---

### Q4. You need to update the DB and publish an event. How do you avoid losing the event if the process crashes between them?

**Deep dive.** This is the **dual-write problem**: the DB and the broker are two
systems, so a crash after the DB commit but before the publish loses the event and
leaves services inconsistent (publishing first has the mirror flaw). The
**Transactional Outbox** solves it: within a *single* DB transaction, write the
business row **and** an `outbox` row; they commit atomically and can't diverge. A
separate relay (or CDC/Debezium) reads unpublished outbox rows, publishes them to
the broker, and marks them sent. Because the relay can crash and re-send, delivery
is at-least-once, so consumers must be idempotent. This is the reliable bridge
from your database into an event stream.

---

### Q5. How do you choose a shard key, and what goes wrong with a bad one?

**Deep dive.** The shard key must (a) distribute load evenly to avoid hotspots and
(b) align with the dominant access pattern to avoid cross-shard queries. Bad keys:
sharding by `country` concentrates traffic on one shard; sharding by a
monotonically increasing timestamp/ID sends all new writes to the last shard (a
hotspot). A good key like `customer_id` spreads load and co-locates a customer's
data so common per-customer queries stay single-shard. Cross-shard queries
(joins/aggregations spanning shards) are slow and complex, and **rebalancing** when
adding a shard is painful — which is why consistent hashing is used to bound how
much data moves. The shard key is a near-irreversible decision; get it right up
front.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. Fetching a list then lazily loading each row's relation in a loop causes:**
- A) a deadlock
- B) the N+1 query problem
- C) a cache stampede
- D) replication lag

**2. The fix for N+1 is to:**
- A) add more replicas
- B) eager-load / batch the related rows in one query
- C) increase the connection pool
- D) disable the ORM

**3. Reading immediately from an async replica after a write can show stale data — this is:**
- A) the dual-write problem
- B) read-your-writes / replication lag
- C) a cache miss
- D) an N+1 query

**4. Atomically saving a row and an event to publish later uses the:**
- A) Saga pattern
- B) Transactional Outbox pattern
- C) CQRS pattern
- D) Singleton pattern

**5. In the scaling ladder, sharding should be:**
- A) the first thing you try
- B) used only when writes/storage exceed a single primary
- C) applied to every table by default
- D) a replacement for indexes

### Answer Key
1. **B** — per-row lazy loads = N+1.
2. **B** — eager-load or batch into one query.
3. **B** — async replica lag causes read-your-writes staleness.
4. **B** — the outbox commits row + event in one transaction.
5. **B** — shard last, only when a single primary is exceeded.

---

## Part 3 — Gotchas Checklist

- **N+1 hides behind ORM lazy loading.** `for x in list: x.relation` silently
  fires a query per row — eager-load or batch, and count queries per request.
- **Not all reads can go to a replica.** Reads that must see a just-written value
  belong on the primary (read-your-writes); classify freshness needs.
- **Replication lag is real** — treat replicas as eventually consistent and design
  for it, don't assume instant sync.
- **Dual writes lose data on crash.** Use the Transactional Outbox to make the
  state change and its event atomic; consumers stay idempotent.
- **Shard last.** Optimize → cache → replicas → shard. Sharding adds cross-shard
  queries and rebalancing pain; don't reach for it first.
- **The shard key is near-irreversible** — pick one that avoids hotspots and keeps
  common queries single-shard.
- **Size the connection pool** — unbounded connections exhaust the DB; too few
  serialize requests. Pool once (see FastAPI `lifespan`).
- **Missing indexes** turn point lookups into full scans — the cheapest scaling
  win is usually an index, not more hardware.
