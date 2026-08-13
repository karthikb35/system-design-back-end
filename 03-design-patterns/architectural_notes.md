# Design Patterns — Architectural Notes

## Patterns are shared vocabulary, not clever tricks

The primary value of a design pattern is **communication**. When you say "put a
circuit breaker on that call" or "wrap the SDK in an adapter," a whole design is
transmitted in three words. Patterns compress experience into a name. That is
why an architect memorizes their *intent and trade-offs*, not their UML.

The secondary value is that patterns are *tested solutions to recurring problem
shapes*. You are unlikely to invent a better Observer than the one thousands of
systems already use.

## The five that matter most in backend Python

| Pattern | Problem shape | Backend example | Underlying SOLID |
| --- | --- | --- | --- |
| **Strategy** | Multiple interchangeable algorithms, chosen at runtime | Pricing rules, retry/backoff policies, compression codecs | OCP + DIP |
| **Factory** | Creation depends on config/context; hide the concrete type | Choosing S3 vs local storage per environment | DIP |
| **Observer** | Decouple "it happened" from "who reacts" | In-process domain events; UI update fan-out | OCP |
| **Adapter** | A third-party interface doesn't match yours | Wrapping a vendor SDK behind your own interface | LSP + DIP |
| **Circuit Breaker** | Stop cascading failure from a sick dependency | Any remote call in a distributed system | Resilience |

## The pattern GoF forgot: Circuit Breaker

The Gang of Four book predates the microservice era, so its 23 patterns say
nothing about *network failure*. In distributed systems, the resilience patterns
matter more than half the GoF catalog:

- **Circuit Breaker** — fail fast when a dependency is down; stop wasting threads
  and latency on calls that will time out anyway. Three states: CLOSED (normal),
  OPEN (reject immediately), HALF-OPEN (probe for recovery).
- **Retry with exponential backoff + jitter** — recover from *transient* faults
  without synchronizing a thundering herd of retries.
- **Bulkhead** — isolate resource pools so one slow dependency can't consume all
  your threads and sink the whole service.

These pair: retry handles blips, the breaker handles sustained outages, and the
bulkhead contains the blast radius. Know when each applies.

## The over-patterning trap (the mid-level failure mode)

A dangerous phase in an engineer's growth is *pattern euphoria* — reaching for a
`FactoryFactory` and five interfaces to instantiate one object. Symptoms:

- Abstractions with exactly one implementation and no test seam.
- Indirection that forces a reader to open six files to follow one call.
- "Enterprise FizzBuzz" — ceremony wildly out of proportion to the problem.

> **Heuristic:** A pattern earns its place when it *removes* more complexity
> (coupling, duplication, rigidity) than the indirection it *adds*. If it doesn't,
> a plain function or `if` statement is the senior choice. Patterns are a cost you
> pay for flexibility you can name a concrete need for.

## Anti-patterns worth naming (recognizing bad patterns is also senior work)

- **God Object** — one class that knows/does everything (violates SRP).
- **Singleton abuse** — global mutable state disguised as a pattern; wrecks
  testability and hides coupling. Prefer dependency injection.
- **Anemic Domain Model** — data classes with all logic pushed into "service"
  classes, so objects are just bags of getters/setters.

## Connections across the repo

- **Strategy/Factory/Observer** are SOLID (02) principles crystallized into named
  shapes.
- **Observer** is the single-process seed of **Event-Driven Systems (08)** —
  replace the in-memory subscriber list with a message broker and you have
  pub/sub across services.
- **Circuit Breaker + Adapter** are the front line of resilient integration in
  **System Design (04)** and **FastAPI (05)**.
