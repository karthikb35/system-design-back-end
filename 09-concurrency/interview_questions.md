# Concurrency & Parallelism — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. What is the GIL, and does it mean threads are useless in Python?

**Deep dive.** The Global Interpreter Lock is a mutex in CPython that allows only
one thread to execute Python bytecode at a time. It exists to keep the
interpreter's own internals (notably reference counts) consistent without
fine-grained locking everywhere. Two consequences matter. First, it makes threads
**useless for CPU-bound** Python: a hot numeric loop holds the GIL, so extra
threads add scheduling overhead and give zero speedup — you need processes for
that. Second, it does **not** make your own operations atomic: `x += 1` is
read/add/write and the GIL can be released between steps, so threads still race
and still need locks. Threads remain genuinely useful for **I/O-bound** work,
because blocking calls (`socket.recv`, `time.sleep`, most C-level I/O) release the
GIL, letting other threads run while one waits. So the honest answer is: threads
overlap *waiting*, not *computing*.

---

### Q2. You have a task that's slow. How do you decide between threads, processes, and asyncio?

**Deep dive.** Classify the bottleneck first. If it's **I/O-bound** (waiting on
network, disk, or another service), the CPU is idle during the wait, so
concurrency helps: use **threads** for a modest number of blocking calls, or
**asyncio** when you need thousands of concurrent connections cheaply and can use
async-native libraries end to end. If it's **CPU-bound** (parsing, hashing,
number crunching in pure Python), threads and asyncio give *nothing* because of
the GIL — use **processes** (`ProcessPoolExecutor`) for true multi-core
parallelism, accepting the cost of pickling data across the boundary and higher
startup. The trade-off summary: threads are cheap and share memory but risk races
and don't scale CPU; processes scale CPU but don't share memory; asyncio scales
I/O fan-out enormously on one thread but poisons instantly if anything blocks the
loop. The senior answer names the workload shape, not a favorite tool.

---

### Q3. Reports say a counter is occasionally wrong under load, but it's fine in tests. How do you diagnose and fix it?

**Deep dive.** "Correct in tests, wrong under load, non-deterministic" is the
signature of a **race condition** on shared mutable state. The counter update is
almost certainly a non-atomic read-modify-write (`n += 1`): two threads read the
same value and one increment is lost, so the total can only ever *under*-count.
Tests miss it because they don't create the contended interleaving; to reproduce
deterministically, force a yield point between the read and the write (or crank up
thread count and iterations) and you'll see the drift. The fix is to make the
critical section **atomic** — wrap the read-modify-write in a `Lock` — or, better,
eliminate the shared state: have each worker accumulate locally and combine
results at the end, or route updates through a `queue.Queue`. Keep the locked
region minimal (guard the write, not any I/O) so you don't trade a race for a
contention or deadlock problem.

---

### Q4. Two threads deadlock intermittently transferring between accounts. What causes it and how do you prevent it?

**Deep dive.** Deadlock needs a **cycle in lock acquisition**: thread A locks
account 1 then waits for account 2, while thread B locks account 2 then waits for
account 1 — each holds what the other needs, forever. It's intermittent because it
only manifests when the two transfers overlap in that opposite order. The robust,
standard prevention is a **global lock ordering**: every thread acquires the two
locks in the same stable order (e.g. by the smaller account id), which makes a
cycle impossible by construction. Complementary tactics: hold locks for the
shortest possible span, never perform I/O or call out to other code while holding
a lock, use `acquire(timeout=...)` to fail loudly instead of hanging, and prefer
lock-free designs (a single queue, or an atomic conditional DB update) so there's
no second lock to order. "Just add more locks" makes deadlock *more* likely, not
less.

---

### Q5. Why is calling a blocking function inside an async coroutine catastrophic, and how do you handle unavoidable CPU or blocking work?

**Deep dive.** asyncio is **cooperative single-threaded** concurrency: one thread
runs all coroutines, and a coroutine only yields control when it `await`s. A
synchronous blocking call — `time.sleep`, a sync DB driver, a heavy CPU loop —
never yields, so it **freezes the entire event loop**: every other task, every
in-flight request, every timer stalls until it returns. In a service this shows up
as catastrophic tail-latency and dropped throughput under concurrency, even though
a single request looks fine. The fix is to keep the loop free: offload blocking
**I/O** with `asyncio.to_thread(...)` (or a thread pool) and offload **CPU-bound**
work to a `ProcessPoolExecutor` via `loop.run_in_executor`, then `await` the
result — the loop stays responsive while the work runs elsewhere. The deeper
discipline is to use async-native libraries throughout so blocking calls never
sneak onto the loop in the first place, and to bound every await with a timeout so
a slow dependency degrades gracefully instead of hanging.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. The GIL guarantees that:**
- A) `counter += 1` is atomic across threads
- B) only one thread runs Python bytecode at a time
- C) threads speed up CPU-bound Python
- D) locks are never needed

**2. For CPU-bound pure-Python work, the right tool is:**
- A) more threads
- B) asyncio
- C) processes (a process pool)
- D) a bigger GIL

**3. `x += 1` across threads without a lock can lose updates because it is:**
- A) atomic
- B) a read-modify-write that can interleave
- C) protected by the GIL
- D) a syntax error

**4. The standard way to prevent deadlock between two locks is:**
- A) acquire them in a consistent global order
- B) add a third lock
- C) use more threads
- D) ignore it; it's rare

**5. Calling `time.sleep(5)` inside an `async def` coroutine will:**
- A) sleep only that coroutine
- B) block the entire event loop for 5 seconds
- C) raise an exception
- D) run on another core

**6. A bounded `queue.Queue(maxsize=N)` provides:**
- A) parallel CPU execution
- B) back-pressure so a fast producer can't exhaust memory
- C) deadlock immunity
- D) a way to bypass the GIL

### Answer Key
1. **B** — the GIL serializes bytecode; it does not make your operations atomic.
2. **C** — only processes achieve true multi-core parallelism for Python code.
3. **B** — read/add/write can interleave, so an increment is lost.
4. **A** — a stable global acquisition order makes a lock cycle impossible.
5. **B** — a sync sleep never yields, freezing every task on the loop.
6. **B** — `maxsize` blocks the producer, matching it to the consumer's rate.

---

## Part 3 — Gotchas Checklist

- **The GIL is not a lock for *your* data.** It protects interpreter internals,
  not your read-modify-write — `+=`, `list[i] = ...`, check-then-act all still race.
- **Threads don't speed up CPU work.** If a hot loop is the bottleneck, threads add
  overhead and no speedup; move to processes.
- **Never block the event loop.** No `time.sleep`, sync DB drivers, or CPU loops in
  a coroutine — offload with `to_thread` / a process pool and `await` the result.
- **Keep critical sections tiny.** Guard the write, not the network call; a lock
  held across I/O is a throughput cliff and a deadlock invitation.
- **Order your locks.** Always acquire multiple locks in the same global order to
  make deadlock structurally impossible.
- **Prefer a queue to shared state.** `queue.Queue` is internally synchronized;
  producer/consumer handoff needs no manual locks.
- **Always bound your waits.** An `await` (or a blocking call) with no timeout is a
  latent hang; use `asyncio.wait_for` / socket timeouts.
- **Bound your buffers for back-pressure.** An unbounded queue turns a slow
  consumer into an out-of-memory crash under load.
- **Process-pool workers must be picklable, top-level functions** (Windows uses
  `spawn`); closures and lambdas won't serialize across the boundary.
- **Distributed check-then-act is the same race, scaled up.** "Read stock, then
  decrement" oversells under concurrency — fix it with an atomic conditional
  update or a row lock, not an in-process `Lock`.
