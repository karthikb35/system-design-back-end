# Python Foundations — Interview Questions

> Format: 5 architectural deep-dive questions with answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. Why does `def f(x, cache={})` almost always misbehave, and what is actually happening?

**Deep dive.** A default argument is evaluated **once**, at function-definition
time, and that single object is reused on every call that doesn't pass the
argument. So a mutable default (`{}`, `[]`) becomes shared state that accumulates
across calls — the "cache" from one caller silently leaks into the next, and the
bug is invisible until a second call sees the first call's data. The mechanism is
the object/reference model: the default is stored on the function object
(`f.__defaults__`) and rebound to the parameter name each call, never re-created.
The fix is the sentinel idiom: default to `None` and build the fresh object
inside the body (`if cache is None: cache = {}`). The senior point is that this
isn't a quirk to memorize — it's the same mutability-plus-shared-reference fact
that causes aliasing bugs, which is why immutability at boundaries is a design
default, not a preference.

---

### Q2. Is Python pass-by-value or pass-by-reference, and what are the consequences?

**Deep dive.** Neither label fits; Python is **call-by-object-reference** (a.k.a.
call-by-sharing). The function receives a *reference* to the same object the
caller holds, but the parameter name is a new binding. Consequences follow from
mutability: if you **mutate** the argument in place (`lst.append(x)`,
`d[k] = v`), the caller sees it — the object is shared. If you **rebind** the
parameter (`lst = [...]`), the caller sees nothing — you only moved the local
name. So passing a mutable object is an implicit contract about who may mutate
it; passing an immutable one (int, str, tuple, frozen dataclass) is inherently
safe. The design lesson is to be deliberate: return new values instead of
mutating inputs when you don't own them, and prefer immutable types across module
boundaries so callers can't be surprised by aliasing.

---

### Q3. What is the `__eq__` / `__hash__` contract, and what breaks if you violate it?

**Deep dive.** The contract has two clauses. First, **objects that compare equal
must hash equal** (`a == b` ⇒ `hash(a) == hash(b)`); the reverse need not hold
(hash collisions are fine). Second, an object used as a dict key or set member
must be **hashable and effectively immutable for the fields that define
equality** — because the container places it in a bucket derived from its hash.
Violations fail *silently*, which is the danger. Override `__eq__` without
`__hash__` and Python sets `__hash__` to `None`, making instances unhashable — a
loud, early failure. Worse is defining both but inconsistently, or mutating a
key after insertion: the object lands in a bucket, its hash changes, and lookups
that "should" find it return a miss while the entry still occupies memory. That's
why value objects (see `Money` in `advanced_dunder.py`) are immutable and hash on
the same fields they compare on.

---

### Q4. Generators vs lists for a large or unbounded stream — what changes, and what is back-pressure?

**Deep dive.** A list computes and stores every element up front: O(n) memory and
all the work happens before you use the first item. A generator computes one
element per `next()` and suspends its frame in between: O(1) memory, work is
**lazy**, and it can represent an **infinite** sequence a list never could. The
architectural payoff for large streams is that memory stays flat regardless of
length, and you get natural **back-pressure** — because nothing is produced until
the consumer pulls, a slow consumer automatically throttles a fast producer
without any explicit buffer or queue management. The trade-offs are real: a
generator is single-pass (consume it twice and the second pass is empty), it
isn't indexable, and its laziness defers *when* exceptions surface, which can
confuse debugging. Choose a list when you need random access or multiple passes;
choose a generator when the data is large, streamed, or infinite.

---

### Q5. How does CPython free memory, and when is `weakref` the right tool rather than a normal reference?

**Deep dive.** CPython's primary mechanism is **reference counting**: every object
tracks how many references point at it, and it's freed *immediately* when the
count hits zero — deterministic, no pause. Refcounting has one blind spot:
**reference cycles** (A → B → A) keep each other's counts above zero forever, so a
**cyclic garbage collector** runs periodically to detect and reclaim unreachable
cycles. The consequence for design is that anything holding a strong reference
extends an object's lifetime — a cache, an observer list, a parent↔child
back-pattern can leak by keeping objects alive after their real owners are gone.
`weakref` is the right tool exactly there: it lets you *observe* or *cache* an
object **without** contributing to its refcount, so a `WeakValueDictionary`
entry disappears automatically when the last strong owner is dropped. Use it for
caches and back-references you don't want to own; use normal references
everywhere ownership is intended.

---

### Q6. When would you choose a `Protocol` over an ABC to define an interface?

**Deep dive.** Both express "this is the shape a collaborator must have," but they
differ in *how membership is decided*. An **ABC** is **nominal**: a type belongs
only if it explicitly subclasses (or is registered with) the ABC, and it can
provide shared implementation and enforce the contract at instantiation. A
**`Protocol`** is **structural**: any object with the right methods satisfies it,
with no inheritance and no import coupling — the implementer doesn't even need to
know the protocol exists. Prefer a `Protocol` when you're defining a dependency
your code *consumes*, especially across a boundary or when adapting third-party
types you can't subclass — it's how you get Dependency Inversion by shape and keep
tests trivial (pass a plain fake). Prefer an ABC when you own the hierarchy and
want to **share code** in the base or force subclasses to implement methods with a
runtime error. The senior answer names the axis — nominal-with-shared-code vs
structural-and-decoupled — instead of claiming one is universally better.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. `def add(x, items=[]): items.append(x); return items` — calling it three times with only `x` gives:**
- A) three separate one-element lists
- B) a growing shared list because the default is created once
- C) a `TypeError`
- D) an empty list each time

**2. Python's argument passing is best described as:**
- A) pass-by-value (arguments are copied)
- B) pass-by-reference (assigning the parameter changes the caller)
- C) call-by-object-reference (shared object; rebinding is local, mutation is visible)
- D) pass-by-name

**3. If you override `__eq__` on a class but not `__hash__`, instances are:**
- A) still hashable with the default hash
- B) unhashable (`__hash__` set to `None`)
- C) automatically frozen
- D) equal to everything

**4. The main advantage of a generator over a list for a 10-million-row stream is:**
- A) it can be indexed faster
- B) it uses ~constant memory and produces lazily (with back-pressure)
- C) it can be iterated many times
- D) it validates the data

**5. A reference *cycle* between two objects is reclaimed by:**
- A) reference counting alone
- B) the cyclic garbage collector
- C) `weakref`
- D) never — it always leaks

**6. `weakref.WeakValueDictionary` is the right choice when you want to:**
- A) keep cached values alive as long as the cache exists
- B) cache values without preventing them from being garbage-collected
- C) make dictionary access faster
- D) store unhashable keys

### Answer Key
1. **B** — the default list is created once at definition time and shared.
2. **C** — call-by-object-reference: mutation is visible, rebinding is local.
3. **B** — defining `__eq__` without `__hash__` sets `__hash__` to `None`.
4. **B** — constant memory, lazy production, natural back-pressure.
5. **B** — refcounting can't see cycles; the cyclic GC reclaims them.
6. **B** — weak values let entries vanish when the last strong owner is dropped.

---

## Part 3 — Gotchas Checklist

- **Mutable default arguments** (`=[]`, `={}`) are evaluated once and shared —
  default to `None` and build inside the function.
- **Aliasing** — `b = a` on a mutable object shares it; mutate through one and the
  other sees it. Copy or use immutables at boundaries.
- **`__eq__` without `__hash__`** makes instances unhashable; defining both
  inconsistently (or mutating a key) breaks dict/set lookups *silently*.
- **Generators are single-pass and not indexable** — consuming one twice yields
  nothing the second time; materialize to a list only when you truly need reuse.
- **Laziness defers errors** — an exception in a generator surfaces when it's
  pulled, not when it's created; account for this when debugging pipelines.
- **`functools.wraps`** — omit it and your decorator erases the wrapped
  function's name, docstring, and signature, breaking introspection and tooling.
- **Context managers that swallow exceptions** — returning truthy from `__exit__`
  suppresses errors; do it by accident and failures disappear.
- **Reference cycles + strong caches leak** — reach for `weakref` for caches and
  back-references you don't intend to own.
- **`__slots__` and descriptors are optimizations, not defaults** — apply them
  where the memory profile or the invariant justifies the lost flexibility.
- **Type hints don't enforce at runtime** — they power tooling and `Protocol`
  structural typing; validate real data at the boundary (Pydantic), not with hints.
