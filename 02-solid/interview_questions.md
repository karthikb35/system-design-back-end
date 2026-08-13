# SOLID in FastAPI — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. A route function does validation, business logic, DB access, a payment call, and email. Which SOLID principles does it violate and why does it matter?

**Deep dive.** It violates at least three. **SRP** — the function has five reasons
to change (validation rules, pricing, schema, payment API, notification), so a
change to any one risks breaking the others; changes *collide* in one place.
**OCP** — provider selection via `if/elif` means adding PayPal edits tested code.
**DIP** — it hard-codes concrete details (the DB, the gateway), so the business
logic is welded to the web framework and can only be tested by spinning up HTTP
and patching globals. Why it matters: the code becomes slow to change, risky to
modify, and nearly impossible to unit-test — the three properties that most
determine a codebase's cost over time.

---

### Q2. Explain how Dependency Inversion turns an untestable route into a fast unit test.

**Deep dive.** DIP says high-level policy depends on abstractions, not concrete
details. By extracting a `RegistrationService` that receives a `UserRepository`,
`Notifier`, and `PaymentGateway` (all Protocols) via its constructor, the service
never imports FastAPI and never constructs its own dependencies. In a test you
instantiate it with in-memory fakes and call `register()` directly — no server,
no database, milliseconds per test. In production, FastAPI's `Depends` wires the
real implementations at the composition root. The abstraction is the *seam* that
makes both substitution (swap Stripe for PayPal) and isolation (fake in tests)
possible.

---

### Q3. Where exactly should the "composition root" live in a FastAPI app, and why does it matter?

**Deep dive.** The composition root is the single place where abstractions are
bound to concrete implementations — in FastAPI, the `Depends` provider functions
(`get_service`, `get_gateway`) and the `lifespan` handler. It must sit at the
*edge* of the system so the inner layers (service, domain) stay ignorant of which
concrete DB or gateway is used. This matters because it localizes the "which
implementation?" decision: swapping in-memory for Postgres, or Stripe for a mock,
is a one-line change there and nowhere else. Scattering `new StripeGateway()`
through the code destroys that property and re-couples everything.

---

### Q4. Your teammate replaces the `if/elif` provider ladder with a dict of gateways. Is that enough to satisfy OCP?

**Deep dive.** It's a big step, but "enough" depends on the *registration*
mechanism. A dict lookup replaces the conditional, and adding a provider means
adding a class + a dict entry rather than editing branching logic — that's the
spirit of OCP. It's fully realized when new providers can be *registered* without
editing the dict's definition either (e.g., a plugin registry or entry-points), so
the core module is truly closed to modification. For most apps the dict is the
pragmatic sweet spot; over-engineering a plugin system for two providers is
YAGNI. The senior answer names the trade-off rather than claiming a single right
answer.

---

### Q5. When does applying SOLID become over-engineering in a FastAPI service?

**Deep dive.** When you introduce abstractions with a single implementation and no
test seam — e.g., a `Protocol` and a factory for a value that is stable and only
ever built one way. Every abstraction is indirection a reader must hold in their
head, and FastAPI already gives you DI cheaply, which tempts over-layering. The
heuristic: introduce an interface when there's a genuine second implementation, a
volatile external boundary (payment, email, storage), or a testing seam you
actually use. A CRUD endpoint over one table doesn't need three layers and four
Protocols. SOLID controls coupling; if there's no coupling worth controlling, the
abstraction is pure cost.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. A route function that validates, saves to DB, charges a card, and sends email violates primarily:**
- A) Liskov Substitution
- B) Single Responsibility
- C) Interface Segregation
- D) none — it's fine

**2. Selecting a payment provider with `if provider == 'stripe' elif ...` violates:**
- A) Open/Closed Principle
- B) Liskov Substitution
- C) DRY only
- D) nothing

**3. In FastAPI, the mechanism that provides Dependency Inversion is:**
- A) middleware
- B) `Depends()`
- C) `BackgroundTasks`
- D) `response_model`

**4. The main testability benefit of extracting a framework-free service layer is:**
- A) it runs faster in production
- B) business logic can be unit-tested without HTTP or a database
- C) it reduces the number of files
- D) it removes the need for Pydantic

**5. Introducing a Protocol with exactly one implementation and no test seam is usually:**
- A) required by SOLID
- B) speculative generality / over-engineering
- C) a Liskov violation
- D) necessary for OCP

### Answer Key
1. **B** — five reasons to change = SRP violation.
2. **A** — a type-switch that grows requires editing tested code (OCP).
3. **B** — `Depends()` is dependency injection built into FastAPI.
4. **B** — a framework-free service is testable in isolation.
5. **B** — abstraction without a second impl or a test seam is YAGNI.

---

## Part 3 — Gotchas Checklist

- **"God routes" fuse five concerns.** Keep routers thin: translate HTTP ⇄ domain
  and map errors to status codes; push logic to a service.
- **`if/elif` on a type code** is an OCP smell — replace with polymorphism or a
  registry/dict of strategies.
- **Business logic importing FastAPI** is the tell that it can't be unit-tested;
  the service layer must be framework-free.
- **Hidden global state** (a module-level dict, a singleton) makes tests leak into
  each other — inject dependencies instead.
- **Validate at the boundary, not everywhere.** Pydantic at the edge means inner
  layers assume clean data (don't re-validate in every function).
- **Return DTOs, not DB/domain models**, or you leak internal fields (a password
  hash) and couple your wire format to your schema.
- **Composition root at the edge only.** Constructing concretes deep in the code
  re-couples layers and defeats DIP.
- **Over-layering is also a smell.** One implementation + no test seam = delete
  the abstraction. SOLID is coupling control, not a checklist to maximize.
