# DRS — Low-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | LLD-DRS-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.3 (Software Detailed Design) |
| Layer | DRS — Deployment & Runtime Substrate |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dirs | `deploy/local/`, `cipher/deploy/local/` |
| Companion | `docs/layers/DRS_HLD.md` |
| Authoritative sources | `deploy/local/docker-compose.yml`, `deploy/local/Makefile`, `deploy/local/.env.example`, `deploy/local/otel-config.yaml`, `deploy/local/policies/poc_allow_all.rego` |

---

## §1 Service Inventory

Source: `deploy/local/docker-compose.yml` (lines 13–150). All ports are
bound to `127.0.0.1` to prevent accidental external exposure.

| Service | Image | Container name | Host ports | Volume(s) | Env vars consumed |
|---|---|---|---|---|---|
| `redis` | `redis:7-alpine` | `cipher-redis` | `6379:6379` | `./data/redis:/data` | — |
| `memgraph` | `memgraph/memgraph:2.18.1` | `cipher-memgraph` | `7687:7687`, `7444:7444` | `memgraph_data:/var/lib/memgraph` (named) | — |
| `qdrant` | `qdrant/qdrant:v1.9.7` | `cipher-qdrant` | `6333:6333`, `6334:6334` | `./data/qdrant:/qdrant/storage` | `QDRANT__SERVICE__GRPC_PORT` |
| `minio` | `minio/minio:latest` | `cipher-minio` | `9000:9000`, `9001:9001` | `./data/minio:/data` | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` |
| `minio-init` | `minio/mc:latest` | `cipher-minio-init` | — (one-shot) | — | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` |
| `nats` | `nats:2.10-alpine` | `cipher-nats` | `4222:4222`, `8222:8222` | — | — |
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.96.0` | `cipher-otel-collector` | `4317:4317`, `4318:4318` | `./otel-config.yaml:/etc/otelcol-contrib/config.yaml:ro` | — |
| `opa` | `openpolicyagent/opa:0.62.1` | `cipher-opa` | `8181:8181` | `./policies:/policies:ro` | — |

### 1.1 Per-service notes

- **Redis**: `--appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru`. AOF persistence. Bounded cache semantics.
- **Memgraph**: `--also-log-to-stderr`. Healthcheck shells `mgconsole`; `start_period: 10s` gives the engine time to initialize.
- **Qdrant**: gRPC enabled via `QDRANT__SERVICE__GRPC_PORT=6334`. Healthcheck uses bash `/dev/tcp` TCP probe.
- **MinIO**: Server mode on `/data`, console on `:9001`. Healthcheck hits `/minio/health/live`.
- **minio-init**: Runs the `mc` client, sets alias, and ensures buckets `cipher-artifacts` and `cipher-checkpoints` exist (idempotent `mc mb --ignore-existing`). `depends_on: minio (service_healthy)`. Exits 0.
- **NATS**: `-js -m 8222` — JetStream on, monitoring HTTP on 8222.
- **OTel Collector**: Mounted config (`otel-config.yaml`) defines OTLP gRPC/HTTP receivers, batch processor, `logging` exporter. Healthcheck disabled.
- **OPA**: `run --server --addr :8181 --diagnostic-addr :8282 /policies`. Loads Rego from the bind-mounted `./policies/` directory.

---

## §2 Volume Layout

Source: enumerated under `deploy/local/data/` on disk. All paths below are
**gitignored**; they hold runtime state, not source.

```
deploy/local/data/
├── redis/
│   ├── dump.rdb
│   └── appendonlydir/
│       ├── appendonly.aof.1.base.rdb
│       ├── appendonly.aof.1.incr.aof
│       └── appendonly.aof.manifest
├── qdrant/
│   ├── raft_state.json
│   └── aliases/data.json
├── minio/
│   └── .minio.sys/
│       ├── format.json
│       ├── pool.bin/...
│       ├── config/...
│       ├── buckets/
│       │   ├── cipher-artifacts/
│       │   └── cipher-checkpoints/
│       └── tmp/...
└── langfuse/
    └── langfuse.db          (see §7 TODO — no compose service writes this)
```

Memgraph state lives in the Docker-managed named volume `memgraph_data`, not
on the host bind-mount tree.

No `sqlite/` directory currently exists despite `.env.example` declaring
`CIPHER_SQLITE_DIR=deploy/local/data/sqlite` — **not yet implemented**.

---

## §3 Network Topology

The Compose file does not declare an explicit `networks:` block, so all
services share the **default project bridge network**
(`local_default` under Compose v2 with project name `local`).

### 3.1 Hostnames

Inside the bridge network, each service is reachable from any other service
by its Compose service name:

| From → To | URL |
|---|---|
| `minio-init` → `minio` | `http://minio:9000` (see compose line 94) |
| Any sidecar → `redis` | `redis://redis:6379/0` |
| Any sidecar → `memgraph` | `bolt://memgraph:7687` |
| Any sidecar → `qdrant` | `http://qdrant:6333` |
| Any sidecar → `nats` | `nats://nats:4222` |
| Any sidecar → `opa` | `http://opa:8181` |
| Any sidecar → `otel-collector` | `http://otel-collector:4317` |

### 3.2 Host-side access

The CIPHER Python app runs on the host (not inside Compose) and reaches each
service via `127.0.0.1:<port>` as listed in §1. This is the addressing
form used by `.env.example` (LLD §4).

### 3.3 External egress

Only `minio-init` performs container-to-container traffic. No service in the
stack is configured for outbound internet calls at runtime (image pulls
notwithstanding).

---

## §4 Configuration

### 4.1 `.env` key contract

Template lives at `deploy/local/.env.example`. The active `.env` is
gitignored. Keys (values not transcribed where they are credentials):

| Section | Key | Purpose |
|---|---|---|
| LLM Backends | `OLLAMA_BASE_URL` | Host Ollama endpoint (default `http://localhost:11434`) |
| | `OLLAMA_MODEL` | Default Ollama model tag |
| | `GEMINI_CLI_PATH` | Path to `gemini` CLI on host |
| | `GEMINI_MODEL` | Default Gemini model id |
| | `GCA_BRIDGE_URL` | Local GCA bridge endpoint |
| Data Stores | `REDIS_URL` | `redis://localhost:6379/0` |
| | `MEMGRAPH_URI` | `bolt://localhost:7687` |
| | `QDRANT_URL` | `http://localhost:6333` |
| | `MINIO_ENDPOINT` | `localhost:9000` |
| | `MINIO_ROOT_USER` | MinIO admin user (consumed by `minio` and `minio-init`) |
| | `MINIO_ROOT_PASSWORD` | MinIO admin secret |
| Messaging | `NATS_URL` | `nats://localhost:4222` |
| SQLite | `CIPHER_SQLITE_DIR` | Path for audit journal SQLite (dir missing — stub) |
| Observability | `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` |
| | `LANGFUSE_HOST` | Langfuse base URL (no service yet — see §7) |
| | `LANGFUSE_SECRET_KEY` | Langfuse secret |
| | `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| Governance | `OPA_URL` | `http://localhost:8181` |
| MKF | `EMBEDDING_MODEL` | Sentence-transformer model name (consumed by Python, not Compose) |

### 4.2 Makefile targets

Source: `deploy/local/Makefile`.

| Target | Behavior |
|---|---|
| `make up` | `docker compose --env-file .env up -d --wait` |
| `make down` | `docker compose down` |
| `make status` | `docker compose ps` |
| `make logs` | `docker compose logs -f --tail=50` |
| `make health` | Sequential curl/exec probes against Redis, Qdrant, NATS, OPA, MinIO, Langfuse |
| `make lint` | `ruff check . && pyright .` (from repo root) |
| `make test` | `pytest tests/ -v --tb=short` |
| `make test-unit` / `test-integration` / `test-e2e` | Scoped pytest runs |
| `make poc-demo` | `pytest tests/e2e/test_poc_spine.py -v --tb=long` |
| `make clean` | `docker compose down -v && rm -rf ./data` (destructive) |

### 4.3 Policy mount

`deploy/local/policies/poc_allow_all.rego`:

```rego
package cipher.authz
default allow := true
```

Permissive POC default. The GCL layer is expected to replace this with
restrictive per-agent policies for MVP.

### 4.4 OTel pipeline

`deploy/local/otel-config.yaml`:
- Receivers: OTLP gRPC `:4317`, HTTP `:4318`
- Processors: `batch` (`timeout: 5s`, `send_batch_size: 1024`)
- Exporters: `logging` (loglevel info) — no durable backend
- Extensions: `health_check` at `:13133`
- Pipelines: `traces` and `metrics` (no `logs` pipeline)

---

## §5 Test Coverage

Two test files target DRS-managed services:

| File | Marker | Notes |
|---|---|---|
| `tests/unit/test_adapters_infra.py` | unit | Adapter-level unit tests (no live containers required). |
| `tests/e2e/test_live_infra.py` | `@pytest.mark.e2e` | Live integration: pings Redis (`redis.asyncio`), Memgraph, etc. Requires `make up` first. Invoked via `make test-e2e` or `make poc-demo`. |

There is **no compose-config lint test** (e.g., `docker compose config`
validation) and **no test asserting `.env.example` ↔ compose `${VAR}`
consistency** — gap.

---

## §6 Wrap / Refactor / Rewrite Status (ASDLC Wrap-First)

| Component | Status | Rationale |
|---|---|---|
| `docker-compose.yml` | **Wrap** — keep as-is | Works for the POC; no need to fragment yet. |
| `Makefile` | **Wrap** | Functional; `health` target is slightly out of sync with services (see §7). |
| `.env.example` | **Refactor** (minor) | Add comments separating "consumed by Compose" vs. "consumed by app"; remove orphan keys (`CIPHER_SQLITE_DIR` if SQLite dir is not used; Langfuse keys if no Langfuse service). |
| `otel-config.yaml` | **Wrap** | Minimal but valid. Defer durable exporter wiring. |
| `policies/poc_allow_all.rego` | **Rewrite** (planned, GCL-owned) | Permissive-by-default is acceptable only during POC. |
| Cloud / K8s topology drivers | **Not yet implemented** | Only `deploy/local/` exists. HLD §3.1 promises topology-independence; DRS only delivers the Compose driver today. |
| `cipher/deploy/local/README.md` | Placeholder | Move content here or delete file. |

---

## §7 TODOs from code / compose comments / divergences

1. **Langfuse service is missing from `docker-compose.yml`** but `make
   health` probes `http://localhost:3000/api/public/health`, `.env.example`
   declares Langfuse keys, and `deploy/local/data/langfuse/langfuse.db`
   exists on disk. Either add a `langfuse` service or remove the stale
   probe + env keys.
2. **SQLite directory referenced but not created.** `CIPHER_SQLITE_DIR=
   deploy/local/data/sqlite` has no creator. Either init via a
   `sqlite-init` job or mark obsolete.
3. **`docker-compose.yml` header comment lists "SQLite (host-file)"** as a
   service (line 10) but it is intentionally not a Compose service.
   Comment is descriptive only — confirm and leave.
4. **OTel collector healthcheck disabled** (`healthcheck: disable: true`,
   line 129). The container exposes `health_check` extension on `:13133` —
   wire a healthcheck against it for parity with other services.
5. **`make lint`** runs `pyright .` from repo root — not yet implemented as
   a gating CI hook at the DRS level.
6. **No staging / production compose overlays.** Add `compose.override.yml`
   variants or document that only `deploy/local/` is supported.
7. **`cipher/deploy/local/README.md`** contains only a placeholder ("Placeholder location for local MVP deployment assets") — reconcile with the active `deploy/local/` tree.
