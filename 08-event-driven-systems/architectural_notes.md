# Event-Driven Systems — Architectural Notes

## The core value: decoupling in time and knowledge

In a synchronous (request/response) system, service A calls service B directly —
A must know B's address, B must be up *right now*, and A waits for B. Event-driven
architecture inverts this: A publishes a **fact** ("OrderPlaced") to a broker and
moves on. Any number of consumers react, later, independently. This buys:

- **Loose coupling** — the producer doesn't know or care who consumes. Add a new
  consumer (e.g. a fraud checker) without touching the producer. This is the
  Dependency Inversion Principle (pillar 02) enforced by infrastructure.
- **Resilience** — if a consumer is down, messages queue and are processed when
  it recovers; the producer isn't blocked.
- **Elasticity** — spiky work is buffered by the queue and drained at the
  consumer's pace (natural back-pressure / load leveling).

The cost is **eventual consistency** and **operational complexity** — you trade
the simplicity of a synchronous call for scalability and resilience. Name that
trade-off; event-driven is not free or universally correct.

## Events are facts, not commands (naming discipline)

- **Event** = past-tense fact: `OrderPlaced`, `PaymentCaptured`. The producer
  states what happened; it doesn't dictate a response. Multiple consumers each
  decide independently what to do.
- **Command** = imperative intent: `PlaceOrder`, sent to *one* handler expected
  to act. Commands couple sender to a specific handler; events don't.

Modeling with events (facts) is what keeps consumers decoupled and independently
evolvable.

## Choreography vs Orchestration

| | Choreography | Orchestration |
| --- | --- | --- |
| How | Services react to each other's events; no central brain | A central orchestrator directs each step |
| Coupling | Low; fully decentralized | Higher; orchestrator knows the flow |
| Visibility | Hard — the flow is emergent, spread across services | Easy — the flow lives in one place |
| Best for | Simple, few-step flows | Complex, many-step workflows needing clear control |

Choreography scales organizationally but can become "who does what?" spaghetti as
flows grow. Orchestration centralizes the workflow (easier to reason about and
change) at the cost of a component that knows about all participants. Many mature
systems use choreography between bounded contexts and orchestration (e.g. a saga
orchestrator) within a complex workflow.

## Delivery guarantees — know which one you have

- **At-most-once** — fire and forget; may lose messages. Rarely acceptable.
- **At-least-once** — retried until acknowledged; **may duplicate**. The common,
  practical default (Kafka, SQS, RabbitMQ).
- **Exactly-once** — the holy grail; genuinely hard end-to-end. In practice you
  achieve *exactly-once effect* by combining **at-least-once delivery + idempotent
  consumers**, not by magic in the broker.

> **The load-bearing rule of event systems:** assume at-least-once, therefore
> make every consumer **idempotent** — processing the same event twice must have
> the same effect as once (dedupe by `event_id`). This is the single most
> important correctness property, and it connects directly to pillar 04.

## Handling failure: retries, DLQ, and poison messages

A consumer that keeps failing on one "poison" message must not block the whole
stream. The pattern: retry a bounded number of times, then route the message to a
**Dead-Letter Queue (DLQ)** for later inspection/replay, and move on. Alert on
DLQ growth — it's a signal of a systemic problem.

## Distributed transactions: the Saga pattern

You cannot wrap a single ACID transaction around multiple services. A **saga** is
a sequence of local transactions where each step publishes an event that triggers
the next; if a step fails, previously completed steps are undone by their
**compensating actions** (reserve inventory → charge card fails → *release*
inventory). Sagas give you consistency *eventually* without two-phase commit,
which doesn't scale and creates coupling/locking. Compensation must itself be
idempotent and may need to handle the case where the "undo" also fails.

## Ordering and partitioning

Global ordering across a topic is expensive and limits throughput. Brokers like
Kafka guarantee order only *within a partition*. Choose a **partition key** (e.g.
`order_id`) so all events for one entity land on the same partition and stay
ordered, while different entities parallelize across partitions. This is the
event-stream analogue of choosing a shard key (pillar 07).

## Connections across the repo

- **Design Patterns (03)** — a broker is the Observer pattern on infrastructure.
- **System Design (04)** — idempotency keys make at-least-once delivery safe.
- **DB Scaling (07)** — the Transactional Outbox is the reliable bridge from a
  database into the event stream.
- **ELK (06)** — correlation IDs are essential to trace an async flow that hops
  across producers and consumers.
