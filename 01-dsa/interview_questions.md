# DSA in Production APIs — Interview Questions

> Format: 5 architectural questions with deep-dive answers, then a multiple-choice
> knowledge check with an answer key, then a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. An endpoint that was fast in staging times out in production. It does `if item in collection` in a loop. What happened and how do you fix it?

**Deep dive.** In staging the collection was small, so the O(n) linear scan of a
`list` was invisible. In production the collection grew (say 50k rows), and
because the loop runs the scan once per requested item (m of them), the endpoint
is O(n·m). At 50k × 500 that's 25M comparisons *per request*, executed
synchronously — it saturates CPU and, in an async app, blocks the event loop so
*all* concurrent requests stall.

The fix is choosing the right structure: a `set`/`frozenset` gives O(1) average
membership, dropping the endpoint to O(n + m). The index (set) should be built
**once** (at startup or cached), not rebuilt per request. The deeper lesson is
that algorithmic complexity is a *production latency budget*: always ask "what is
n at scale, and what bounds it?" A structure that's fine at n=100 can be an
outage at n=10⁶.

---

### Q2. How does an unbounded request body become a denial-of-service vector, even without malicious intent?

**Deep dive.** If the endpoint accepts `list[str]` with no cap, the client
controls `m`. Combine that with an O(n) operation per element and the server-side
cost scales as O(n·m) under client control — an **algorithmic complexity attack**
(amplification). Even a well-meaning client running a large batch can trigger it.
The defense is to bound N at the trust boundary (Pydantic `max_length`), so the
worst-case cost is provably capped. Bounds on input size, page size, and nesting
depth are architectural decisions, not afterthoughts. Related: unbounded response
sizes (returning all rows) are the mirror problem — always paginate.

---

### Q3. When is an O(n²) algorithm inside an endpoint acceptable?

**Deep dive.** When N is small *and provably bounded*. If the input is a config
list capped at 50 items, an O(n²) nested loop is ~2,500 operations — negligible,
and often more readable than a cleverer structure. Premature optimization adds
risk (bugs, complexity) for no measurable gain. The senior signal is refusing to
optimize *or* to leave it slow without first establishing the bound on N and the
latency budget. "It depends on what bounds N" is the correct opening, not a
reflexive "always use a hash map."

---

### Q4. You need an autocomplete endpoint. Compare scanning a list, a SQL `LIKE`, and a trie.

**Deep dive.** *List scan / `startswith` over all rows* is O(n) per keystroke —
fine for thousands, hopeless for millions and it repeats every keystroke.
*SQL `LIKE 'prefix%'`* can use a B-tree index (prefix matches are
range scans) and is a reasonable default that offloads work to the database.
*Trie* gives O(k) prefix lookup independent of the number of keys (k = prefix
length), ideal for very high-QPS autocomplete, at the cost of memory and having
to keep the trie in sync with the source of truth. The choice is a trade-off of
QPS, dataset size, memory, and operational simplicity — for most apps a
DB-indexed `LIKE` or a search engine (Elasticsearch) beats hand-rolling a trie.

---

### Q5. Why is caching a computed result in a `dict` both a performance win and a correctness risk?

**Deep dive.** A `dict` (or Redis) cache converts an O(n) or O(log n) lookup into
O(1), which is a large win for read-heavy endpoints. But a cache is a **second
source of truth**, so it introduces invalidation — the hard problem. Risks: stale
entries when the source changes, unbounded memory growth without an eviction
policy (use an LRU/TTL), and the **thundering herd / cache stampede** when a hot
key expires and many requests recompute it at once. Senior caching always
specifies capacity, eviction, TTL, and a stampede mitigation (single-flight lock
or probabilistic early expiry) — not just "add a dict."

---

## Part 2 — Multiple-Choice Knowledge Check

**1. What is the time complexity of `x in my_list` for a Python `list`?**
- A) O(1)
- B) O(log n)
- C) O(n)
- D) O(n log n)

**2. Doing a list-membership test for `m` items against a list of `n` items is:**
- A) O(n + m)
- B) O(n · m)
- C) O(m log n)
- D) O(1)

**3. The best fix to make repeated membership tests O(1) average is to use a:**
- A) sorted list + linear scan
- B) `set` / `frozenset`
- C) tuple
- D) generator

**4. Accepting an unbounded `list` in a request body primarily risks:**
- A) a SQL injection
- B) an algorithmic-complexity denial of service
- C) a CSRF attack
- D) a memory leak in the client

**5. An O(n²) algorithm inside an endpoint is acceptable when:**
- A) never — always optimize
- B) the input size N is small and provably bounded
- C) only in staging
- D) the endpoint is a GET

### Answer Key
1. **C** — list membership is a linear scan.
2. **B** — m scans × O(n) each = O(n·m).
3. **B** — a set gives O(1) average membership.
4. **B** — unbounded N + per-element cost = algorithmic DoS.
5. **B** — a small, bounded N makes O(n²) negligible and often clearer.

---

## Part 3 — Gotchas Checklist

- **`in` on a list is O(n).** Use a `set`/`dict` for membership and keyed lookup.
- **Build the index once.** Rebuilding a set/dict per request throws away the win.
- **Bound every input.** `max_length` on lists, page-size caps, nesting limits —
  answer "what bounds N?" at the boundary.
- **Bound every output.** Returning all rows is the mirror DoS; paginate.
- **Hash-map worst case is O(n).** "O(1)" is *amortized/average*; pathological
  collisions (or untrusted keys) degrade it — usually fine, but know it exists.
- **Recursion depth ∝ input** is a crash vector (Python ~1000-frame limit); use
  iterative traversal on untrusted/deep data.
- **CPU-bound loops block the event loop** in `async` routes — offload or bound.
- **A cache is a second source of truth**: set capacity, eviction, TTL, and a
  stampede guard, or you trade a speed bug for a correctness bug.
