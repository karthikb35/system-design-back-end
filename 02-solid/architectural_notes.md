# SOLID — Architectural Notes

## SOLID is a coupling-control toolkit, not a style guide

Junior engineers treat SOLID as five rules to recite. Architects treat it as
**five levers for managing coupling and cohesion** so that a change in one
requirement touches one place in the code. Every principle answers the same
meta-question: *"When this requirement changes, how much code has to change with
it?"* Good design keeps that blast radius small.

| Principle | The coupling it attacks | The smell it removes |
| --- | --- | --- |
| **S**ingle Responsibility | A class serving multiple actors | "God" classes; unrelated changes collide in one file |
| **O**pen/Closed | Change requires editing tested code | Growing `if/elif` type ladders |
| **L**iskov Substitution | Subclasses that surprise callers | `isinstance` checks; overridden methods that throw |
| **I**nterface Segregation | Clients coupled to unused methods | Fat interfaces; `raise NotImplementedError` stubs |
| **D**ependency Inversion | Policy coupled to concrete detail | High-level modules importing low-level ones |

## The principles interlock (they are not independent)

A subtle senior insight: violating one often forces violating another.

- A **fat interface (ISP violation)** forces implementers to stub methods they
  can't support, typically by raising — which is an **LSP violation**.
- **DIP** is only achievable if you have abstractions to depend on, which is
  what **ISP** (small interfaces) and **OCP** (stable abstractions) provide.
- **SRP** is the foundation: classes with one responsibility naturally have
  small, cohesive interfaces, making the other four easier.

## Dependency Inversion is the load-bearing one

If you learn only one, learn DIP. The `PaymentService` in the reference code
never imports `StripeGateway`. It receives a `Chargeable` through its
constructor. This single move buys you:

1. **Testability** — inject a fake gateway in a unit test; no network, no mocks
   of concrete classes.
2. **Swappability** — change payment providers by changing one line at the
   *composition root*, not scattered through the codebase.
3. **A clean boundary** — the "what" (charge an order) is separated from the
   "how" (talk to Stripe's API). Boundaries are where change is absorbed.

The **composition root** — the single place (often `main` or the DI container /
FastAPI dependency graph) where abstractions are bound to concretions — is an
architectural pattern in its own right. Keep it at the edge of your system.

## When SOLID becomes over-engineering

SOLID has a cost: indirection. Every abstraction you introduce is a layer a
reader must hold in their head. The failure mode of a *mid*-level engineer is
applying SOLID *everywhere*, producing a maze of one-implementation interfaces.

> **Rule of thumb:** Introduce an abstraction when you have (or clearly foresee)
> a *second* implementation, or when you need a *seam for testing*. Abstracting
> for a single, stable implementation is speculative generality — it pays a cost
> now for a benefit that may never arrive (YAGNI).

## How this connects to the rest of the repo

- **Design Patterns (03)** are named, reusable applications of these principles.
  Strategy *is* OCP + DIP; Adapter *is* how you honour LSP across a boundary.
- **FastAPI (05)** dependency injection is DIP made into a framework feature.
- **Event-Driven (08)** systems push DIP to the network: services depend on an
  event *contract*, not on each other's implementations.
