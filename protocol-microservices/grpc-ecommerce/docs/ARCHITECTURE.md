# Architecture — gRPC E-commerce

This repo implements the same e-commerce domain as the REST and GraphQL editions,
but every inter-service call is a **gRPC** unary RPC defined by a Protocol Buffers
contract. Reading the three editions side by side shows exactly what changes when
you swap the transport — and what stays the same.

---

## 1. System topology

```mermaid
flowchart TB
    Client["Client (HTTP/JSON)"]
    subgraph Edge
        GW["API Gateway<br/>HTTP :8000 → gRPC client"]
    end
    subgraph Services
        U["Users<br/>gRPC :50051"]
        P["Products<br/>gRPC :50052"]
        O["Orders<br/>gRPC :50053"]
    end
    subgraph Data
        DBU[("users_db")]
        DBP[("products_db")]
        DBO[("orders_db")]
    end

    Client --> GW
    GW --> U
    GW --> P
    GW --> O
    O --> U
    O --> P
    U --> DBU
    P --> DBP
    O --> DBO
```

Only the Gateway is public. Everything behind it speaks gRPC.

---

## 2. The contract is the source of truth

In gRPC the wire format is defined *once*, in `.proto` files under `protos/`, and
both sides generate code from them. Server and client can never disagree about
the message shape.

```mermaid
flowchart LR
    Proto["protos/*.proto<br/>(single source of truth)"]
    Gen["scripts/gen_protos.py<br/>protoc codegen"]
    SStub["server stubs<br/>*_pb2_grpc Servicer"]
    CStub["client stubs<br/>*_pb2_grpc Stub"]

    Proto --> Gen
    Gen --> SStub
    Gen --> CStub
    SStub -. same messages .- CStub
```

`gen_protos.py` writes the generated modules into each service's `app/pb/` (and
the gateway's). A small `pb/__init__.py` shim adds that directory to `sys.path`
so the generated flat `import users_pb2` statements resolve.

---

## 3. Per-service layering

Every service uses the same layered design; only the top (transport) layer knows
about protobuf.

```mermaid
flowchart TD
    S["servicer.py — protobuf ↔ domain, gRPC status mapping"]
    B["service.py — business logic (transport-agnostic)"]
    R["repository.py — the only DB code"]
    M["models.py — SQLAlchemy tables"]
    S --> B --> R --> M
```

Because `service.py` and below never import protobuf, the exact same business
logic could be re-exposed over REST or GraphQL — which is precisely what the
sibling repos do.

---

## 4. Cross-cutting concerns

```mermaid
flowchart LR
    subgraph Every service
        I["CorrelationInterceptor<br/>(grpc.aio.ServerInterceptor)"]
        H["grpc_health.v1 Health<br/>SERVING/NOT_SERVING"]
        L["JSON structured logs<br/>with request_id"]
    end
    I --> L
```

- **Correlation id**: the Gateway mints an `x-request-id`; every service reads it
  from inbound metadata and forwards it on outbound calls, so one id traces a
  request across the whole fan-out.
- **Health**: each service registers the standard gRPC Health service; Docker's
  `HEALTHCHECK` and the Gateway's `/health/ready` both probe it.
- **Deadlines + retries**: callers (Orders, Gateway) attach a timeout to every
  RPC and retry only transient codes (`UNAVAILABLE`, `DEADLINE_EXCEEDED`).

---

## 5. Data ownership

Database-per-service: one Postgres instance, three logical databases created by
`infra/postgres/init-databases.sql`. No service reads another's tables — the only
way to get another service's data is to call its RPC.

| Service | Database | Owns |
| --- | --- | --- |
| Users | `users_db` | user accounts, credentials |
| Products | `products_db` | catalog, stock levels |
| Orders | `orders_db` | orders + line items (with price snapshot) |
