# Concurrency & Parallelism — Architectural Notes

## Concurrency is a coupling problem in disguise

Junior engineers treat concurrency as a speed knob: add threads, go faster.
Architects treat it as a **correctness and coupling problem** — the moment two
flows of control touch the same mutable state or the same finite resource, you
have introduced an ordering dependency that the code no longer makes visible.
The meta-question every primitive answers is: *"What must NOT happen at the same
time, and how do I make that impossible rather than merely unlikely?"* Bugs here
pass every test on your laptop and corrupt data under production load, because
the failure lives in an interleaving you never scheduled.

## Concurrency is not parallelism

**Concurrency** is *dealing with* many things at once — structuring a program as
independent tasks that may be interleaved. **Parallelism** is *doing* many things
at once — literally executing on multiple cores. asyncio is concurrent but not
parallel (one thread). A process pool is both. You choose a model by the shape of
the work, not by which sounds fastest.

| Model | Best for | What it costs | Classic failure mode |
| --- | --- | --- | --- |
| **Threads** | I/O-bound work (network, disk) that mostly *waits* | Shared mutable state ⇒ races; locks ⇒ deadlock risk | Lost updates; deadlock from bad lock ordering |
| **Processes** | CPU-bound work (crunching, parsing) that *computes* | No shared memory (pickling); high startup/RAM | Serialization overhead dwarfs the win on small tasks |
| **asyncio** | High-fan-out I/O: thousands of concurrent connections | Whole ecosystem must be non-blocking; one thread | One blocking call freezes *every* task on the loop |

## The GIL: what it does and does not protect

CPython's Global Interpreter Lock lets only **one thread execute Python bytecode
at a time**. Consequences that trip people up:

- It **does** keep the interpreter's own internals consistent (object refcounts,
  built-in container internals) — a single `list.append` won't corrupt the heap.
- It **does not** make *your* multi-step operations atomic. `counter += 1` is a
  read, an add, and a write; the GIL can be released between any of those, so two
  threads can read the same value and one increment vanishes. This is why threads
  still need locks despite the GIL.
- It **prevents** threads from parallelizing CPU-bound Python. Extra threads on a
  hot loop add scheduling overhead and give zero speedup — reach for processes.

> **Rule of thumb:** Threads for **waiting**, processes for **computing**, asyncio
> for **massive I/O fan-out**. Choosing the model wrong is the root cause of most
> "why isn't my concurrency faster?" tickets.

## Races, locks, and the discipline that avoids deadlock

A **race condition** is a bug whose outcome depends on timing. The fix is to make
the read-modify-write **atomic** by serializing it inside a critical section: a
`Lock` (one holder) or a `Semaphore` (up to N holders — a connection pool is just
a semaphore). But locks introduce their own hazard: **deadlock**, where thread A
holds lock 1 and waits for lock 2 while thread B holds lock 2 and waits for lock
1. The canonical prevention is a **global lock ordering** — every thread acquires
locks in the same, stable order (e.g. by a sortable id), so a cycle can never
form. Keep critical sections *small* (hold the lock for the write, not the I/O)
and never do blocking or network work while holding a lock.

The senior move is to **avoid shared mutable state entirely** where you can. A
`queue.Queue` is internally synchronized, so producer/consumer handoff needs no
manual locks: the queue *is* the synchronization boundary, and it converts a
locking problem into a data-flow problem, which is far easier to reason about.

## The asyncio golden rule and structured concurrency

asyncio is **cooperative**: a coroutine keeps the single thread until it `await`s.
The golden rule follows directly — **never block the event loop.** A synchronous
`time.sleep`, a CPU-heavy loop, or a blocking DB driver inside a coroutine stalls
*every* other task, tanking tail latency for the whole process. Offload blocking
work with `asyncio.to_thread` (I/O) or a process pool (CPU), and use async-native
libraries end to end.

**Structured concurrency** (task groups, `asyncio.wait_for`, cancellation) makes
lifetimes and failures explicit: a timeout *cancels* the overrunning task rather
than leaking it, and a failing child propagates instead of silently vanishing.
Timeouts and cancellation are not optional — an unbounded `await` is a latent
hang. Pair them with **back-pressure**: a bounded queue (`maxsize`) forces a fast
producer to slow to the consumer's rate instead of exhausting memory. Unbounded
buffering is the quiet way concurrent systems fall over under load.

## How this connects to the rest of the repo

- **FastAPI (05)** runs your handlers on an event loop — the golden rule is a
  production concern there: one blocking call in an `async def` route degrades
  every concurrent request, so offload CPU/blocking work off the loop.
- **Event-Driven Systems (08)** are back-pressure and queues at the network
  scale: the bounded-queue and producer/consumer ideas here reappear as broker
  partitions, consumer lag, and flow control.
- **System Design (04)** trades throughput against latency; the model you pick
  (threads/processes/async) sets the ceiling on both and defines your failure
  modes under saturation.
- **protocol-microservices** contains the real-world version of a race: the
  Orders service `reserve_stock` path is **check-then-act** (read stock, then
  decrement). Two concurrent orders can both pass the check and oversell — the
  exact `counter += 1` hazard, moved to a distributed boundary, where the fix is
  an atomic conditional update or row lock rather than an in-process `Lock`.
