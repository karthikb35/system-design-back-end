# Python Foundations — Architectural Notes

## Language fluency is architectural leverage

Junior engineers treat the language as syntax to memorize. Architects treat it
as a set of **protocols and constraints that shape the systems they can build**.
The abstractions you reach for — a generator instead of a list, a `Protocol`
instead of a base class, a context manager instead of a `try/finally` — decide
whether a design stays cheap to change and cheap to run under load. Every topic
below answers the same meta-question SOLID asks: *when a requirement (or the data
volume) changes, how much has to change with it, and what fails first?*

## The data model is Python's real interface system

Python has almost no *nominal* interfaces built into the runtime. Instead, the
**data model** — the dunder protocols (`__iter__`, `__len__`, `__eq__`,
`__enter__`, `__call__`, …) — is the interface layer. Duck typing means "an
interface" is *any object that implements the required methods*, checked at the
call site, not declared by inheritance. This is enormously flexible, but the
failure mode is **implicit contracts**: nothing forces `__eq__` and `__hash__`
to stay consistent, or an iterator to actually terminate. The protocol is real;
the enforcement is on you.

| Protocol | Dunders | The capability it grants | Failure mode if done wrong |
| --- | --- | --- | --- |
| Value object | `__eq__` / `__hash__` | Safe as dict/set keys | Mutable key or mismatched pair → silent lookup loss |
| Iterable | `__iter__` / `__next__` | Works in every `for`, lazy | Never raising `StopIteration` → infinite loop |
| Container | `__len__` / `__getitem__` | Feels built-in; slicing | `__len__` disagreeing with contents |
| Resource | `__enter__` / `__exit__` | Deterministic cleanup | Swallowing exceptions in `__exit__` |
| Callable | `__call__` | Stateful "function" objects | Hidden state that surprises callers |

## The object/reference model, and its two classic traps

Python names are **references to objects**; assignment binds a name, it never
copies. Two traps follow directly. **Aliasing**: `b = a` where `a` is a list
means a mutation through `b` is visible through `a` — the source of "spooky
action at a distance" bugs. **Mutable default arguments**: `def f(x, acc=[])`
evaluates `[]` *once* at function-definition time, so the same list is shared
across every call and accumulates state between them. Both stem from the same
fact — mutability plus shared references — and both are why immutability at
boundaries (tuples, frozen dataclasses, returning copies) is a design choice,
not a style preference.

## Iterators and generators are memory control

A list materializes every element; a generator yields one at a time and
suspends its stack frame in between. That difference *is* an architectural
lever: it turns an O(n)-memory operation into O(1), enables **infinite streams**
(a Fibonacci generator has no list equivalent), and gives you natural
**back-pressure** — a consumer that reads slowly automatically throttles a
producer, because nothing is computed until `next()` is called. The trade-off:
generators are single-pass and their laziness can hide *when* work (and errors)
actually happen, which surprises people debugging a pipeline.

## Decorators and context managers absorb cross-cutting concerns

Both exist to keep a concern out of the code it wraps. **Decorators** add
behavior — timing, retry, memoization, auth — without editing the wrapped
function; the discipline is `functools.wraps` so the wrapper doesn't erase the
callee's identity. **Context managers** guarantee teardown pairs with setup even
on exceptions, which is the only reliable way to manage resources (files,
locks, connections, transactions). Reaching for `try/finally` by hand is the
smell they remove; the failure mode is a context manager that suppresses the
exception it should propagate.

## Descriptors and `__slots__` pay off at scale

**Descriptors** (`__get__`/`__set__`) are the machinery behind `@property`,
methods, and ORM fields — one reusable object that governs attribute access
across every field it manages (DRY validation). **`__slots__`** trades the
per-instance `__dict__` for a fixed field set: less memory and faster access at
high instance counts, plus typo protection. Neither is a default — both are
optimizations you apply where the profile or the invariant justifies them.
Slotting a class you rarely instantiate is pure cost and lost flexibility.

## The CPython memory model

CPython frees objects by **reference counting** — deterministic, immediate at
count zero — backed by a **cyclic garbage collector** that reclaims reference
*cycles* refcounting can never see. The senior consequence: caches and
back-references can leak by keeping objects alive, and the right tool is
**`weakref`** (e.g. `WeakValueDictionary`) — reference an object without
extending its lifetime, so a leak-free cache empties itself when the last real
owner goes away.

## Typing and Protocols enable DIP without inheritance

Type hints don't change runtime behavior; they power tooling, document intent,
and — via `Protocol` — provide **structural interfaces**. A function that takes
`SupportsArea` accepts any object with `.area()`, no shared base class. This is
Dependency Inversion achieved by *shape*, letting you depend on an abstraction
without an inheritance tree, and letting tests supply a plain fake.

## How this connects to the rest of the repo

- **SOLID (02)** — `Protocol` is how DIP is realized idiomatically in Python:
  policy depends on a structural interface, concretions are injected at the edge.
- **Design Patterns (03)** — dunder methods *are* patterns in disguise:
  `__call__` gives Strategy, `__enter__`/`__exit__` gives a resource Guard,
  `__iter__` gives Iterator, and metaclasses/`__init_subclass__` give a Registry.
- **Concurrency (09)** — `async`/`await` and coroutines build directly on the
  iterator/generator protocol; understanding suspension explains the event loop.
- **protocol-microservices** — the same primitives run the services: `async`
  handlers, context-manager `lifespan` for startup/shutdown, factory
  `classmethod`s for construction, and Pydantic validating at the boundary so
  inner layers assume clean data.
