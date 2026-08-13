# Database Scaling — Architectural Notes

## The ladder: scale in the cheapest order first

Don't reach for sharding when an index will do. Climb the ladder, and stop as
soon as the bottleneck is solved — every rung adds operational complexity.

1. **Optimize first** — indexes, query tuning, `N+1` elimination, connection
   pooling. The cheapest capacity is the capacity you already have.
2. **Vertical scaling** — a bigger box. Simple, no code change, but finite and
   eventually expensive with a hard ceiling and no fault tolerance.
3. **Caching** — put Redis in front for read-heavy hot data (see pillar 04).
4. **Read replicas** — scale *reads* horizontally.
5. **Sharding / partitioning** — scale *writes* and *storage* horizontally. The
   heaviest hammer; use last.

## Read replicas — scaling reads, and the lag you inherit

Most systems are read-heavy, so routing reads to asynchronously-replicated
replicas offloads the primary cheaply. The cost is **replication lag**: a replica
is eventually consistent, so a read immediately after a write may return stale
data — the **read-your-writes** problem. Mitigations:

- Route reads that *must* see the latest write to the **primary** (as the
  reference router does with `needs_fresh`).
- **Sticky/consistent reads** for a short window after a user's write.
- Accept staleness where the domain tolerates it (a slightly old view count).

Replicas also give you **failover** (promote a replica if the primary dies), so
they buy availability, not just read throughput.

## Sharding — scaling writes and storage, and the choices that bite

When one primary can't hold the data or absorb the write rate, partition it. The
**shard key is the most consequential decision** you'll make:

| Strategy | Pro | Con |
| --- | --- | --- |
| **Hash-based** | Even distribution, no hotspots | Range queries must fan out to all shards |
| **Range-based** | Efficient range scans | Hotspots (e.g. newest data on one shard) |
| **Directory/lookup** | Flexible, re-mappable | The lookup table is a bottleneck/SPOF |

Two things a good shard key avoids:
- **Hotspots** — a key like "country" sends all US traffic to one shard.
- **Cross-shard queries** — joins/queries spanning shards are slow and complex;
  choose a key aligned with your dominant access pattern (e.g. shard by
  `customer_id` if queries are per-customer).

**Rebalancing** when you add a shard is painful — this is exactly why
*consistent hashing* (pillar 04) is used, to bound how much data moves.

## The dual-write problem and the Transactional Outbox

A subtle, extremely common distributed-systems bug: you need to **update the DB
and publish an event** (e.g., save an order *and* emit `OrderCreated`). These are
two different systems. If you write to the DB, then the process crashes before
publishing, the event is lost — your services are now inconsistent. Publishing
first and then writing has the mirror problem.

The **Transactional Outbox** solves it: within a *single DB transaction*, write
the business row **and** an `outbox` row. Because they share one transaction, they
commit or roll back together — no divergence. A separate **relay/CDC process**
reads unpublished outbox rows and pushes them to the broker, marking them sent.
Because the relay can crash and re-send, delivery is **at-least-once**, which is
why downstream consumers must be **idempotent** (pillars 04 and 08).

## SQL vs NoSQL — an access-pattern decision, not a fashion one

- **SQL** — strong consistency, ACID transactions, flexible ad-hoc queries and
  joins. Default choice; you need a *reason* to leave it. Scales reads via
  replicas and writes via sharding (with effort).
- **NoSQL** — chosen for a specific shape: massive horizontal write scale
  (Cassandra), flexible/denormalized documents (MongoDB), key-value speed
  (DynamoDB/Redis). You typically trade joins and multi-key transactions for
  scale, and design the schema *around your queries*.

> **Rule:** Pick storage by your access patterns and consistency needs, then
> denormalize/shard to fit — not by which database is trending.

## CQRS — when reads and writes want different models

**Command Query Responsibility Segregation** separates the write model
(normalized, transactional) from one or more read models (denormalized,
query-optimized), kept in sync via events. It shines when read and write
workloads have very different shapes/scales, but it adds eventual consistency and
operational complexity — apply it to a bounded context that needs it, not
system-wide by default.

## Connections across the repo

- **System Design (04)** — sharding uses consistent hashing; idempotency makes
  the outbox's at-least-once delivery safe.
- **Event-Driven (08)** — the outbox is the reliable *bridge* from your database
  into an event stream.
- **ELK (06)** — replica lag, slow-query rate, and shard balance are metrics you
  monitor to know when to climb the next rung.
