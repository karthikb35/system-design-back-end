# Design Patterns in FastAPI — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. A notification endpoint has a growing `if channel == ...` ladder. Which pattern fixes it and what exactly does it buy?

**Deep dive.** The Strategy pattern: define a `NotificationChannel` interface and
one implementation per channel, then select at runtime via a Factory (a dict
mapping name → strategy). What it buys is Open/Closed compliance — adding a
channel is a new class plus a registry entry, editing no tested branching logic —
and testability, since each channel is an isolated unit and the route no longer
contains behavior. It also removes the risk that a change to the SMS branch
accidentally breaks the email branch, because they no longer share a function.
The trade-off is a little indirection, justified once the set of channels is
expected to grow.

---

### Q2. Explain the circuit breaker's three states and how it prevents a cascading failure.

**Deep dive.** **CLOSED** — calls pass through and failures are counted. After N
consecutive failures the breaker trips to **OPEN** — calls fail *immediately* for
a cooldown window, without touching the dead dependency. After the cooldown it
moves to **HALF-OPEN** and allows one probe: success closes it, failure reopens
it. It prevents cascading failure by converting slow timeouts into fast
rejections: when a downstream provider is down, threads/connections aren't held
waiting on doomed calls, so the calling service doesn't exhaust its own resources
and take *itself* down. The breaker trades a brief period of shedding load for
overall system survival, and gives the dependency room to recover.

---

### Q3. How do retries, timeouts, and circuit breakers combine, and what's the danger of using retries alone?

**Deep dive.** They form a layered resilience strategy. **Timeouts** bound how
long any single call can hang (mandatory on every network call). **Retries with
exponential backoff + jitter** recover from *transient* blips. **Circuit
breakers** handle *sustained* outages by stopping retries entirely. Retries alone
are dangerous: during a real outage, aggressive retries multiply load on an
already-failing dependency (a "retry storm"), and synchronized retries create a
thundering herd. Backoff + jitter de-synchronizes them, and the breaker caps the
damage by short-circuiting once failures are clearly not transient. The senior
design uses all three together.

---

### Q4. Someone submits a PR adding a `FactoryFactory` and five interfaces to send an email. How do you respond?

**Deep dive.** Push back with the cost/benefit lens. A pattern earns its place
only when it removes more complexity (coupling, duplication, rigidity) than the
indirection it adds. If there's one implementation, no test seam, and no
foreseeable second variant, that's speculative generality (YAGNI) — it makes the
code harder to read now for a benefit that may never arrive. I'd suggest
collapsing it to a plain function or a single Strategy interface and
re-introducing abstraction when a real second channel appears. Recognizing
*over*-patterning is as much a senior skill as knowing the patterns.

---

### Q5. Where does the Adapter pattern belong in a service that integrates a third-party SDK?

**Deep dive.** At the boundary. Wrap the vendor SDK in an Adapter that conforms to
*your* interface (e.g., a `NotificationChannel`/`Notifier` you define), so your
application code depends on your abstraction rather than the vendor's signatures.
The payoff: when you switch vendors or the SDK changes, you write/modify one
adapter and nothing else changes; and in tests you substitute a fake implementing
your interface without mocking the vendor's concrete classes. This is Dependency
Inversion at an integration point, and it keeps third-party churn from rippling
through your codebase. Pair it with a circuit breaker for the network call.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. Replacing a growing `if channel == ...` ladder with interchangeable classes is the:**
- A) Singleton pattern
- B) Strategy pattern
- C) Decorator pattern
- D) Visitor pattern

**2. A circuit breaker in the OPEN state will:**
- A) retry the call indefinitely
- B) fail fast without calling the dependency
- C) cache the last successful response
- D) increase the timeout

**3. Using retries WITHOUT backoff during an outage tends to cause:**
- A) a retry storm that worsens the outage
- B) a memory leak
- C) a SQL injection
- D) nothing — it's best practice

**4. Wrapping a third-party SDK behind your own interface is the:**
- A) Facade pattern
- B) Adapter pattern
- C) Observer pattern
- D) Factory pattern

**5. A `FactoryFactory` with five interfaces to construct one stable object is:**
- A) required by the Gang of Four
- B) over-engineering (YAGNI)
- C) the Strategy pattern
- D) a circuit breaker

### Answer Key
1. **B** — interchangeable algorithms behind one interface = Strategy.
2. **B** — OPEN means fail fast, no call to the dependency.
3. **A** — retries without backoff amplify load (retry storm).
4. **B** — conforming a foreign interface to yours = Adapter.
5. **B** — abstraction with no second impl/test seam = over-engineering.

---

## Part 3 — Gotchas Checklist

- **Every remote call needs a timeout.** No timeout = a hung thread waiting on a
  dead dependency; enough of them and the service dies.
- **Retries need backoff + jitter.** Naive retries synchronize into a thundering
  herd and turn a blip into an outage (retry storm).
- **A breaker without a HALF-OPEN probe never recovers** — or recovers by
  slamming the dependency with full traffic. Probe with one call.
- **Tune breaker thresholds to the dependency.** Too sensitive = false trips; too
  lax = no protection. Base it on real error-rate/latency SLOs.
- **Strategy/Factory registries can hide typos** — an unknown key must fail
  loudly (400/validation), not silently no-op.
- **Don't confuse Adapter and Facade.** Adapter changes an incompatible shape;
  Facade simplifies a complex subsystem. Using the wrong word signals confusion.
- **Over-patterning is a real anti-pattern.** Indirection you can't justify with a
  concrete need is cost, not craftsmanship.
- **Singletons for shared state** hide coupling and break tests — prefer DI.
