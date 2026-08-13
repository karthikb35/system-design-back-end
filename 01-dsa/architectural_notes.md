# DSA — Architectural Notes

## The senior reframe: Big-O is a budget, not a badge

Junior engineers memorize complexity classes to pass interviews. Architects use
them to answer a single operational question: **"Will this operation still be
fast enough when the input is 100× larger?"**

Complexity only matters *relative to N at scale*. An `O(n²)` algorithm over a
list that is provably ≤ 50 items is not a bug — it's a non-issue, and rewriting
it to `O(n log n)` is premature optimization that adds risk. Conversely, an
`O(n)` scan is a latent outage if `n` is an unbounded user-supplied collection.

> **Rule:** Always ask "what bounds N?" before you optimize. The bound is an
> architectural decision; the algorithm is downstream of it.

## Choosing a structure — the decision table

| Need | Structure | Cost you accept |
| --- | --- | --- |
| O(1) keyed lookup | Hash map | No ordering; hash-collision worst case; memory overhead |
| Bounded cache with eviction | LRU (hash + linked list) | Eviction policy = a consistency decision |
| Ordered range queries | Balanced BST / B-tree | O(log n) vs O(1); this is why DB indexes are B-trees |
| Prefix / autocomplete | Trie | High memory; wins when key length ≪ key count |
| Shortest unweighted path | BFS + queue | O(V+E) space for the frontier |
| Cycle / dependency check | DFS + colors | Recursion depth = stack risk on deep graphs |
| Rate limiting | Token bucket | Allows bursts; sliding-window log is more accurate but heavier |

## Failure modes the toy version hides

- **LRU cache** — the eviction event is where bugs live. If the evicted entry
  was the only copy of dirty data, you've lost a write. Caches must cache
  *derivable* data, or you need a write-through/write-back strategy.
- **Recursion (DFS)** — Python's default recursion limit (~1000) means a deep
  or adversarial graph causes a `RecursionError`, i.e. a crash from user input.
  Production graph traversal on untrusted data should be iterative with an
  explicit stack.
- **Token bucket** — the lazy-refill trick assumes a monotonic clock. Using
  wall-clock time (`time.time()`) makes it vulnerable to NTP jumps. Always use
  `time.monotonic()` for elapsed-time logic.

## From single-process to distributed

Every structure here has a distributed cousin, and the jump is where senior
thinking shows:

- **LRU cache → Redis / Memcached.** Now eviction, network latency, and cache
  stampede (thundering herd on a cold key) become the design surface.
- **Rate limiter → distributed rate limiter.** A per-process token bucket does
  not limit a fleet. You need a shared counter (Redis `INCR` + TTL) and must
  reason about the race between check and decrement.
- **Graph → graph database / service mesh topology.** Traversal becomes a
  network of RPCs; "shortest path" becomes "fewest network hops," and each edge
  can fail.

## Interview-relevant heuristics

1. State the complexity of **both** time and space, unprompted.
2. Name the **worst case**, not just the average (hash maps are O(1) *amortized*).
3. Tie the structure to a **real system** you'd build with it.
4. Always mention what **bounds the input** — it reframes the whole problem.
