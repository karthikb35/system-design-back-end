# ELK / Observability in FastAPI — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. Why is `print(f"user {id} failed")` a production anti-pattern, and what replaces it?

**Deep dive.** Free-text logs are a dead end at scale. Elasticsearch indexes
*fields*, so structured JSON logs become a queryable, aggregatable dataset — you
can run `status:500 AND latency_ms:>1000 AND path:"/checkout"` and build
dashboards and alerts from it. `print`/f-string logs can only be grep'd line by
line, can't be aggregated (avg latency, error rate), and can't drive alerts. The
replacement is a JSON formatter emitting one object per line to stdout, with
consistent field names across all services, shipped to ELK by a forwarder. Also,
`print` bypasses log levels and handlers entirely — use the `logging` module.

---

### Q2. A request fails somewhere across five services. Walk me through finding where, and what makes it possible.

**Deep dive.** You need a **correlation (trace) ID**. Generate it at the edge — or
accept an inbound `X-Request-ID` from the gateway/upstream — propagate it through
every downstream call via headers, and stamp it on every log line and trace span.
In FastAPI, a middleware sets the ID into a `contextvar` at request start, and the
JSON formatter reads that contextvar so *every* line for the request carries it,
even across `await` points. Then you filter Kibana (or APM) by that single ID to
reconstruct the whole request timeline in order and pinpoint the failing hop.
Without correlation IDs, cross-service debugging in interleaved logs is guesswork.

---

### Q3. Compare logs, metrics, and traces. Which do you alert on?

**Deep dive.** They're complementary. **Metrics** are cheap numeric aggregates
(rates, latencies, counts) — they tell you *something is wrong* and are what you
**alert** on, using symptom-based golden signals (latency p99, traffic, errors,
saturation). **Traces** follow one request across services and tell you *where*
time went or which hop failed. **Logs** are detailed per-event records that tell
you *why* (the exception + context) once you've localized the problem. Alert on
metrics, not logs, for things like latency — a histogram gives percentiles
cheaply; then pivot to traces to localize and logs (by correlation ID) to
root-cause. Alerting on causes ("CPU 80%") creates noise; alert on user-facing
symptoms tied to runbooks.

---

### Q4. Your Elasticsearch cluster filled its disk overnight. What went wrong and how do you prevent recurrence?

**Deep dive.** Logs are unbounded time-series data; without lifecycle management,
indices grow until the disk is full — a predictable outage. Prevention is **Index
Lifecycle Management (ILM)**: roll indices over by age/size, transition older data
through hot → warm → cold tiers on cheaper storage, and delete beyond the
retention period. Also guard against **mapping explosions** — logging dynamic or
unbounded field names (e.g., serializing a whole object with arbitrary keys) bloats
the index mapping and can destabilize the cluster — and consider **sampling**
high-volume success logs while never sampling errors. Add capacity planning and a
disk-saturation alert so you catch it before it recurs.

---

### Q5. What are the security and PII considerations of logging, and how do you enforce them?

**Deep dive.** Logs are widely readable (whole org + tooling) and long-lived, so
they're a prime data-leak vector. Never log secrets (passwords, tokens, API keys,
full card numbers) or unnecessary PII. Enforcement is layered: a code-review
policy and lint rules; a structured-logging helper that only accepts an explicit
allow-list of fields (so you can't accidentally dump a whole request/user object);
redaction/masking filters in the logging pipeline (e.g., mask anything matching
token/password patterns) as a safety net; and retention limits via ILM so leaked
data doesn't live forever. Logging a password (as the junior endpoint does) is a
reportable security incident, not a style nit.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. Structured JSON logging beats f-string logging in ELK primarily because:**
- A) it's shorter
- B) Elasticsearch can index fields, enabling search/aggregation/alerts
- C) it uses less disk
- D) it's required by Python

**2. To trace one request across many services you use a:**
- A) bigger log level
- B) correlation / trace ID propagated via headers and context
- C) separate log file per request
- D) database transaction

**3. You should alert primarily on:**
- A) raw CPU usage
- B) user-facing symptoms (latency, errors, saturation, traffic)
- C) log line count
- D) disk reads

**4. An Elasticsearch cluster running out of disk from logs is prevented by:**
- A) bigger log messages
- B) Index Lifecycle Management (rollover + tiering + deletion)
- C) disabling logging
- D) more Kibana dashboards

**5. Logging a user's password is:**
- A) fine if the log is internal
- B) a security incident — never log secrets/PII
- C) required for auditing
- D) acceptable at DEBUG level

### Answer Key
1. **B** — indexed fields make logs queryable and alertable.
2. **B** — a propagated correlation/trace ID stitches the request.
3. **B** — alert on symptoms (golden signals), not raw causes.
4. **B** — ILM caps unbounded time-series growth.
5. **B** — never log secrets; it's an incident.

---

## Part 3 — Gotchas Checklist

- **No `print` in production.** Use the `logging` module with a JSON formatter to
  stdout (12-factor); let the platform ship logs to ELK.
- **One JSON object per line** with **consistent field names** across services, or
  you can't aggregate across them.
- **Always attach a correlation ID** (set in middleware via a `contextvar` so it
  survives `await`); return it in a response header for client-side correlation.
- **Never log secrets or PII.** Use an allow-list logging helper + pipeline
  redaction as a safety net; logging a password is an incident.
- **Beware mapping explosions** — don't log unbounded/dynamic field names; keep
  fields bounded and typed.
- **Configure ILM** (rollover, hot/warm/cold, retention) or the cluster *will*
  fill its disk.
- **Alert on symptoms, not causes**, and make every alert actionable with a
  runbook — noisy alerts train people to ignore them.
- **Prefer metrics over logs for latency alerting** (histograms give cheap
  percentiles); use logs to investigate specific slow requests.
- **Exceptions belong in a field** with the stack trace, not smeared across
  multiple free-text lines.
