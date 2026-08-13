# `services/users/tests/` — test suite

These are **end-to-end HTTP tests** that exercise the real FastAPI app in-process
against an in-memory SQLite database. No Postgres, no network, no mocks of the
internal layers — a request goes in the front door and the assertions check the
JSON that comes out.

```mermaid
flowchart LR
    Test[test_users.py] -->|httpx ASGITransport| App[app.main:app]
    App --> Layers["routers → service → repository"]
    Layers --> DB[(in-memory SQLite)]
```

| File | Role |
|------|------|
| [conftest.py](conftest.py) | provides the `client` fixture |
| [test_users.py](test_users.py) | the actual test cases |
| `__init__.py` | marks the folder a package |

---

## 1. `conftest.py` — the `client` fixture

```mermaid
sequenceDiagram
    participant F as client fixture
    participant DB as init_models()
    participant T as ASGITransport
    F->>DB: create tables (fresh schema)
    F->>T: wrap app.main:app (in-process)
    F-->>Test: AsyncClient(base_url=http://test)
    Note over F: teardown closes the client
```

```python
@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await init_models()                       # create schema
    transport = ASGITransport(app=app)        # talk to the app with no socket
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

- `ASGITransport` routes httpx requests **straight into the ASGI app** — fast and
  hermetic, no TCP port.
- The app already defaults to `sqlite+aiosqlite:///:memory:`, so the fixture only
  needs to create the schema.
- `asyncio_mode=auto` (in [`../pytest.ini`](../pytest.ini)) lets the tests be
  `async def` without a decorator.

---

## 2. `test_users.py` — what each test proves

```mermaid
flowchart TD
    A[test_health_live] --> A1["liveness returns alive"]
    B[test_create_and_get_user] --> B1["201, password NOT leaked, round-trip GET"]
    C[test_duplicate_email_conflicts] --> C1["second create → 409"]
    D[test_login_returns_token] --> D1["valid → bearer token; wrong pw → 401"]
    E[test_invalid_email_is_rejected] --> E1["bad email → 422 at boundary"]
```

| Test | Asserts | Guards against |
|------|---------|----------------|
| `test_health_live` | `200 {status: alive}` | broken probe wiring |
| `test_create_and_get_user` | `201`, then `GET` returns same id; **`password`/`hashed_password` absent** | leaking secrets in responses |
| `test_duplicate_email_conflicts` | second identical create → **409** | broken uniqueness rule |
| `test_login_returns_token` | valid creds → `bearer` token; wrong password → **401** | auth regressions |
| `test_invalid_email_is_rejected_by_validation` | malformed email → **422** | validation bypass at the boundary |

The `test_create_and_get_user` assertion `assert "password" not in body` is the
security regression test — it fails loudly if a future change ever serializes the
hash.

---

## How to run

```powershell
cd services/users
..\..\.venv\Scripts\python.exe -m pytest -q
```
