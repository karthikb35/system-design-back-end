# Networking, Security & Testing — Architectural Notes

## These three topics share one question: *whom do you trust, and how do you prove it?*

Junior engineers treat networking, security, and testing as three unrelated
chores. Architects see one continuous concern: a request arrives from an
untrusted network, and every layer must decide how much to trust it and
*prove* that trust — cryptographically, not by assumption. The reference
`production_code.py` walks the whole path (hash → token → query → authorize) so
the layers are visible in one file.

## The transport: HTTP/1.1, HTTP/2, and where gRPC/GraphQL fit

HTTP/1.1 is text, one in-flight request per connection (head-of-line blocking
worked around with 6+ parallel sockets). HTTP/2 is binary and **multiplexed**:
many concurrent streams over one long-lived connection, with header compression.
That single change is why long-lived connections matter for latency.

| Transport | Wire format | Concurrency model | Best when |
| --- | --- | --- | --- |
| HTTP/1.1 + JSON (REST) | text | one request per connection | public APIs, cacheability, simplicity |
| HTTP/2 + Protobuf (gRPC) | binary | multiplexed streams | internal service-to-service, low latency |
| HTTP + SDL (GraphQL) | text (typed query) | one POST, client-shaped response | aggregation / avoiding over-fetch |

The [`protocol-microservices`](../protocol-microservices) repos implement the
*same* e-commerce domain three ways so you can compare these transports directly;
the gRPC gateway opens its HTTP/2 channels once at startup precisely to reuse
that expensive connection.

## Authentication vs authorization — different questions

**Authentication** answers *who are you?* (credentials → identity).
**Authorization** answers *what may you do?* (identity → permission). They are
independent checks: a genuine, unexpired token from a `user` account must still
be refused an `admin` action. Collapsing them ("valid token ⇒ allowed") is
OWASP **A01: Broken Access Control**, the most common serious flaw. Enforce
authorization on the server, per action, from a *signed* claim — never from a
role the client asserts.

## Password storage — never plaintext, never a fast hash

A leaked credential table is a *when*, not an *if*. Defense in depth means the
leak is useless:

- **Never plaintext.** Store a hash, and never log or return it.
- **Never a fast/unsalted hash** (md5, sha256). A per-user random **salt**
  defeats rainbow tables and hides that two users share a password; a
  deliberately **slow KDF** (argon2/scrypt/bcrypt; PBKDF2 in the stdlib demo)
  makes each brute-force guess expensive.
- **Constant-time compare** on verify (`hmac.compare_digest`) so response timing
  can't leak the hash byte by byte.

This is OWASP **A02: Cryptographic Failures**. The demo uses PBKDF2 only because
it ships in `hashlib`; the microservice repos use **bcrypt** (truncating input to
72 bytes) for the same reasons.

## JWT — integrity, not secrecy; and lifetime is everything

A JWT is three base64url parts — `header.payload.signature` — where the
signature is an HMAC of `header.payload` under a server-only secret. Two facts a
senior never confuses:

- **Integrity, not confidentiality.** The payload is *encoded*, not encrypted;
  anyone holding the token can read the claims. Put no secrets in it.
- **Verify before you trust.** Recompute and compare the signature (constant
  time) *before* reading any claim; an unverified payload is attacker input.

The `exp` claim bounds the blast radius of a stolen token. Because a stateless
JWT can't be revoked mid-life, you keep access tokens **short-lived** and pair
them with a rotating **refresh token** — the trade-off for skipping a
session-store lookup on every request.

## The OWASP mindset, with SQL injection as the worked example

Injection (OWASP **A03**) is always the same shape: untrusted input concatenated
into a query *string*, so the input can change the query's *structure*
(`' OR '1'='1` turns a login lookup into "return every row"). The fix is
structural, not sanitization: **parameterized queries** send SQL and data on
separate channels, so input is *always* data and can never be parsed as code.
Pair it with **least privilege** — the app's DB role can't `DROP` or read tables
it doesn't need — so a missed query is not catastrophic.

## TLS and mTLS (conceptual — documented, not implemented here)

TLS gives you three things on the wire: **confidentiality** (eavesdroppers see
ciphertext), **integrity** (tampering is detected), and **server authentication**
(the certificate proves you reached the real host). Plain TLS authenticates only
the server. **Mutual TLS (mTLS)** adds a client certificate so *both* ends prove
identity — which is why service meshes use mTLS for east-west traffic: every
service call is mutually authenticated and encrypted without the app code
knowing. The cost is certificate issuance and rotation (a mesh/CA automates it).

## The testing pyramid and why fakes beat mocks

Push most coverage to the base: **many fast unit tests**, **some integration**
tests across a real boundary, **few end-to-end** tests. A test **double** stands
in for a collaborator: a **stub** returns canned data, a **fake** is a working
lightweight implementation (in-memory repo), and a **mock** records calls so you
can assert *how* it was called. Prefer **fakes over mocks**: mocks assert on
interactions, so they break when you refactor internals even if behavior is
unchanged; a fake lets you assert on *observable state* and survives refactors.

## How this connects to the rest of the repo

- **[05-fastapi-advanced](../05-fastapi-advanced)** — dependency injection is the
  seam that lets you swap real gateways for fakes; that's what makes the pipeline
  above unit-testable without a network.
- **[06-elk-monitoring](../06-elk-monitoring)** — security needs an audit trail.
  Log auth decisions, but **redact** secrets: never log passwords, tokens, or the
  full `Authorization` header (structured logging + field redaction).
- **[protocol-microservices](../protocol-microservices)** — the repos **bcrypt**
  passwords and **mint** a JWT at login, and their tests use in-process
  `ASGITransport` doubles (no sockets). Honest gap the reader should notice: those
  repos currently **mint** a token but **do not verify** it on protected routes —
  authentication is only half-wired, exactly the authn-vs-authz split above.
