# System Design — Architectural Notes

## The interview (and the job) is about trade-offs

There is no correct system design, only a design that is correct *for a stated
set of constraints*. A senior answer always: (1) clarifies requirements and
scale, (2) does back-of-the-envelope math, (3) proposes a design, and (4)
**names what it sacrifices**. Skipping step 4 is the clearest junior tell.

## A repeatable framework for any design question

1. **Clarify & scope.** Functional requirements, then non-functional: expected
   scale (DAU, QPS), latency budget (p99), consistency needs, read/write ratio.
2. **Estimate.** QPS, storage/year, bandwidth. See the calculator in the code.
   The point isn't precision; it's discovering the *bottleneck* (is this
   read-heavy? storage-bound? write-bound?).
3. **Define the API.** The contract constrains everything downstream.
4. **Data model & storage choice.** SQL vs NoSQL driven by access patterns and
   consistency, not fashion.
5. **High-level design.** Boxes and arrows: LB → stateless app tier → cache →
   DB, plus async workers for slow work.
6. **Scale the bottleneck.** Caching, replication, sharding, CDN, queues.
7. **Address failure & operability.** Redundancy, timeouts, retries, circuit
   breakers, monitoring (this is where pillars 06–08 plug in).

## CAP and PACELC — the theorem you must be able to apply, not just recite

**CAP:** during a network **P**artition you must choose **C**onsistency *or*
**A**vailability. You cannot have both while partitioned.

- **CP** (e.g., a strongly-consistent store): reject requests rather than serve
  stale/divergent data. Choose when correctness is non-negotiable (payments,
  inventory).
- **AP** (e.g., Dynamo-style stores): keep serving, reconcile later. Choose when
  availability matters more than perfect freshness (social feeds, product
  catalogs).

**PACELC** completes it: **E**lse (when there's no partition) you still trade
**L**atency vs **C**onsistency. Even in the happy path, synchronous strong
consistency costs latency. This is the more useful daily lens.

## Consistent hashing: why `hash % N` fails at scale

Naive modulo hashing remaps ~all keys when N changes by one — a mass cache-miss
storm or a full shard migration. Consistent hashing bounds the churn to ~1/N of
keys (only those between the changed node and its neighbor). **Virtual nodes**
(replicas) fix the secondary problem: without them, a few unlucky nodes get
disproportionate load. This primitive underlies Cassandra, DynamoDB, and most
distributed caches.

## Idempotency: the unglamorous key to correctness

Networks give you *at-least-once* delivery. Clients, load balancers, and queues
all retry. Without idempotency, retries double-charge, double-ship, double-post.
An **idempotency key** lets the server recognize a retry and *replay the stored
result* instead of re-running the side effect. Persist the result **before**
acknowledging, so a crash-then-retry is still safe. This turns at-least-once
*delivery* into exactly-once *effect* — the achievable form of "exactly once."

## Caching layers and their hazards

| Layer | Wins | Hazard to design for |
| --- | --- | --- |
| Client / browser | Zero server load | Hard to invalidate; stale UI |
| CDN | Offloads static/edge | Purge lag |
| Application cache (Redis) | Cuts DB load, low latency | Invalidation; **cache stampede** on cold keys |
| Database buffer pool | Transparent | Limited by RAM |

Two hard problems: **invalidation** (keeping cache and source of truth in sync)
and **stampede** (many requests recompute the same expired hot key at once — fix
with locks/single-flight or probabilistic early expiry).

## Load balancing & statelessness

Horizontal scaling requires the app tier to be **stateless** — any request can
hit any instance. Push state to shared stores (DB, Redis, object storage). The
moment a server holds session state in memory, you've broken horizontal scaling
and created a sticky-session dependency that complicates failover.

## Connections across the repo

- **DB Scaling (07)** is step 6 (scale the bottleneck) applied to the data tier.
- **Event-Driven (08)** is how you move slow/spiky work off the request path.
- **ELK (06)** is step 7 (operability) — you can't scale what you can't see.
