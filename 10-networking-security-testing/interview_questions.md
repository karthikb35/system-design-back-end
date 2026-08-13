# Networking, Security & Testing — Interview Questions

> Format: 5 architectural questions with deep-dive answers, a multiple-choice
> knowledge check with an answer key, and a consolidated gotchas list.

---

## Part 1 — Architectural Deep-Dive Questions

### Q1. Why must you never store plaintext passwords, and why is a salted, slow KDF (bcrypt/PBKDF2/argon2) required rather than SHA-256?

**Deep dive.** A credential store *will* eventually leak, so the design goal is
to make a leaked table useless. Plaintext is game over. A **fast** hash like
SHA-256 is barely better: it's built for speed, so a GPU tries billions of
guesses per second, and without salting an attacker uses precomputed **rainbow
tables** and instantly sees which users share a password. Two properties fix
this. A per-user random **salt** makes identical passwords hash differently and
defeats precomputation — every table must be attacked from scratch. A
deliberately **slow** key-derivation function (PBKDF2 with many rounds, or
memory-hard bcrypt/scrypt/argon2) makes *each individual guess* expensive, so
brute force becomes economically infeasible. Complete it with a **constant-time
compare** on verify (`hmac.compare_digest`) so response timing can't leak the
stored hash byte by byte. This is OWASP A02 (Cryptographic Failures).

---

### Q2. Explain JWT integrity vs confidentiality, and the trade-off between stateless tokens and server-side sessions.

**Deep dive.** A JWT is `header.payload.signature`, where the signature is an
HMAC (or asymmetric signature) over the first two parts under a server secret.
It provides **integrity** — you can detect that nobody altered the claims — but
**not confidentiality**: the payload is base64url-*encoded*, readable by anyone
holding the token, so it must never contain secrets. The verifier must
**recompute and compare the signature (in constant time) before trusting any
claim**; an unverified payload is attacker input. The stateless trade-off:
a JWT needs no session-store lookup per request (cheap horizontal scaling,
easy cross-service trust), but it **can't be revoked** before `exp`. So you keep
access tokens short-lived and add a rotating **refresh token**. A server-side
**session** is the opposite: instantly revocable and small on the wire, but every
request pays a store lookup and you must share/replicate that store across nodes.
Tokens favor scale and statelessness; sessions favor control and revocation.

---

### Q3. Precisely how does a parameterized query stop SQL injection, and what should back it up?

**Deep dive.** Injection happens because untrusted input is concatenated into a
query *string*, so the input can change the query's *structure* — `' OR '1'='1`
turns `WHERE name = '<input>'` into a tautology that returns every row (an auth
bypass), and `'; DROP TABLE ...` smuggles a second statement. A **parameterized
(prepared) query** sends the SQL text and the parameter values to the driver on
**separate channels**: the database parses the SQL *first* with placeholders, then
binds the values as opaque data that is *never re-parsed as SQL*. So `' OR '1'='1`
becomes a literal (non-existent) username, not code. This is structural, not
sanitization — you are not trying to escape dangerous characters, you are making
data and code physically distinct. Back it with **least privilege** (the app's DB
role can't `DROP` or read tables it doesn't need) so any missed query isn't
catastrophic, and with input validation at the boundary for defense in depth.

---

### Q4. Authentication vs authorization: what's the difference, and where do you enforce each in a microservice mesh?

**Deep dive.** **Authentication** establishes *who* the caller is (credentials →
identity, e.g. verify a token's signature and expiry). **Authorization**
establishes *what* that identity may do (identity → permission, e.g. a role or
policy check). They are separate: a genuine, unexpired `user` token must still be
refused an `admin` action — treating "valid token ⇒ allowed" is OWASP A01
(Broken Access Control). In a mesh, do **authentication at the edge** (the API
gateway validates the token once and forwards a trusted, signed identity — plus
**mTLS** so services authenticate *each other*), but keep **authorization close to
the resource**: each service enforces its own permissions on each action, because
only it knows what its data means. Never rely solely on a perimeter check — an
internal caller (or a bug) that reaches a service directly must still be
authorized. Enforce on the server, from a signed claim, per action.

---

### Q5. What does TLS provide, what does mTLS add, and what are the trade-offs?

**Deep dive.** TLS gives three guarantees on the wire: **confidentiality**
(eavesdroppers see only ciphertext), **integrity** (tampering in transit is
detected), and **server authentication** (the certificate chain proves you
reached the real host, not a man-in-the-middle). Standard TLS authenticates only
the *server*; the client stays anonymous at the transport layer (you authenticate
it separately, e.g. with a token). **Mutual TLS** adds a **client certificate**,
so *both* ends cryptographically prove identity. That's why service meshes use
mTLS for east-west traffic: every service-to-service call is mutually
authenticated and encrypted transparently, with no app code involved, giving you
zero-trust networking between services. The trade-offs: certificate **issuance,
distribution, and rotation** are real operational cost (a mesh/CA like SPIFFE or
Istio automates it), there's a modest handshake/CPU overhead, and short-lived
certs need reliable renewal or you cause outages. TLS is table stakes for any
public traffic; mTLS is the standard for internal zero-trust.

---

## Part 2 — Multiple-Choice Knowledge Check

**1. The primary reason to use bcrypt/PBKDF2/argon2 instead of a single SHA-256 for passwords is:**
- A) SHA-256 output is too short
- B) they are deliberately slow and salted, making brute force infeasible
- C) SHA-256 is not cryptographically secure
- D) they encrypt the password so it can be decrypted later

**2. The signature on a JWT proves:**
- A) the payload is encrypted and secret
- B) the claims have not been tampered with (integrity)
- C) the token cannot expire
- D) the user is authorized for admin actions

**3. Parameterized queries prevent SQL injection because:**
- A) they escape every quote character in the input
- B) they send SQL and data on separate channels so input is never parsed as code
- C) they run inside a database transaction
- D) they hash the user input first

**4. A valid, unexpired token from a `user` account requesting an admin-only action should be:**
- A) allowed — the token is valid
- B) refused — authorization is a separate check from authentication
- C) allowed if the token has a `role` field of any value
- D) refused only if the token is expired

**5. Compared with a mock, a fake (a working in-memory implementation) is usually preferred because:**
- A) it makes tests run on the network
- B) it asserts on interactions, coupling tests to implementation
- C) it lets you assert on observable state and survives refactors
- D) it removes the need for any assertions

**6. mTLS differs from ordinary TLS in that it additionally provides:**
- A) confidentiality of the payload
- B) client authentication via a client certificate
- C) faster handshakes
- D) protection against SQL injection

### Answer Key
1. **B** — salt defeats precomputation; slowness makes each guess costly.
2. **B** — HMAC/signature proves integrity, not secrecy (payload is only encoded).
3. **B** — separating SQL from data makes input structurally incapable of being code.
4. **B** — authentication ≠ authorization; enforce the role check server-side.
5. **C** — fakes verify behavior via state, so refactors don't break them.
6. **B** — mutual TLS authenticates the client too, not just the server.

---

## Part 3 — Gotchas Checklist

- **Never store plaintext or a fast/unsalted hash.** Salt per user + a slow KDF
  (bcrypt/argon2/PBKDF2) + constant-time compare (`hmac.compare_digest`).
- **A JWT payload is encoded, not encrypted.** Anyone with the token can read it;
  put no secrets in it, and **verify the signature before trusting any claim**.
- **Short token lifetimes + rotation.** A stateless JWT can't be revoked mid-life;
  bound the damage with `exp` and refresh-token rotation.
- **Injection is structural, not a sanitization problem.** Use parameterized
  queries; back them with least-privilege DB roles.
- **Authn ≠ authz.** A valid token is not permission — enforce role/policy checks
  per action, on the server, from a signed claim.
- **Enforce authorization close to the resource,** not only at the gateway; an
  internal caller must still be authorized.
- **Don't log secrets.** Redact passwords, tokens, and `Authorization` headers in
  structured logs and audit trails.
- **Prefer fakes to mocks.** Assert on observable state, not on how a collaborator
  was called, so refactors don't break green tests.
- **Shape the pyramid.** Many unit, some integration, few e2e; slow, flaky e2e
  suites hide real failures. Seed randomness/time to kill flakiness.
- **mTLS for east-west traffic.** Mutual certs authenticate both ends; budget for
  certificate rotation (let a mesh/CA automate it).
