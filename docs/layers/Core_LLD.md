---
doc_id: LLD-CORE-001
title: CIPHER Core — Low-Level Design
layer: Core (shared SDK)
status: Draft
version: 0.1.0
last_updated: 2026-05-17
implementation_dirs:
  - cipher/core/
  - cipher/observability/
source_refs:
  - docs/CIPHER_LLD.md §10
  - docs/SESSION_HANDOFF.md §4.3
  - tests/unit/test_schemas.py, test_otel_tracing.py
---

# 1. Module Inventory

## 1.1 `cipher/core/`

| File | Purpose | Status |
|---|---|---|
| `__init__.py` | Package marker; docstring "CIPHER Core — shared SDK with no agent dependencies." | Stable |
| `README.md` | Brief intent statement (A2A envelopes, agent-card models, memory/tool client contracts, trace metadata) | Stable |
| `contracts.py` | Legacy dataclasses `Budget`, `TaskMessage`, `TaskEnvelope` — predates Pydantic schemas | **Legacy / not re-exported** |
| `orchestrator.py` | `CipherOrchestrator` mother node — child registry, well-known URLs, lifecycle hooks | Working, **not wired** as parent yet (SESSION_HANDOFF §4.3) |

## 1.2 `cipher/core/schemas/`

| File | Exports | Purpose |
|---|---|---|
| `__init__.py` | re-exports `AgentCard`, `ArtifactRelation`, `CloudEvent`, `RelationType`, `SkillDescriptor`, `TaskClass`, `TaskContract`, `TaskResult`, `TaskStatus` | Public façade |
| `task_contract.py` | `TaskClass`, `TaskStatus`, `TaskContract`, `TaskResult` | A2A wire schemas |
| `agent_card.py` | `AgentCard`, `SkillDescriptor` | Agent identity advertisement |
| `artifact_relation.py` | `RelationType`, `ArtifactRelation` | Knowledge-graph edges |
| `cloud_event.py` | `CloudEvent` | CloudEvents v1.0 envelope for NATS |
| `devnex_types.py` | `VCycleStage`, `NodeStatus`, `NodeResult`, `SkillManifest`, `WorkflowDefinition`, `BridgeRequest`, `BridgeResponse` | DevNex internals migrated from CAR-002 dataclasses (T-029) |

## 1.3 `cipher/core/adapters/`

| File | Class / Functions | Backend |
|---|---|---|
| `redis_client.py` | `RedisClient`, `get_redis_url()` | Redis 7 |
| `memgraph_client.py` | `MemgraphClient`, `get_memgraph_uri()` | Memgraph via Neo4j bolt |
| `qdrant_client_wrapper.py` | `QdrantHealthClient`, `get_qdrant_url()` | Qdrant (health only) |
| `minio_client.py` | `MinioStore`, `get_minio_client()`, `get_minio_endpoint()` | MinIO S3 |
| `sqlite_factory.py` | `create_cipher_db()`, `create_audit_db()`, `create_checkpoints_db()` | SQLite WAL |
| `state_store.py` | `StateStore(client, namespace)` | Redis-backed K/V (T-014) |

## 1.4 `cipher/core/otel/`

| File | Exports |
|---|---|
| `tracing.py` | `init_tracing(service_name, otlp_endpoint)`, `get_tracer(name)`, `@traced(name, attributes)` |
| `__init__.py` | re-exports `get_tracer`, `init_tracing`, `traced` |

## 1.5 `cipher/core/substrate/`

| File | Exports |
|---|---|
| `compose_driver.py` | `ComposeConfig`, `ComposeDriver` — env-resolved endpoint surface (T-001) |

## 1.6 `cipher/observability/`

| File | Status |
|---|---|
| `__init__.py` | Placeholder ("Observability scaffold for the CIPHER local MVP.") |
| `README.md` | Planned: OpenTelemetry tracing, structured logging, audit instrumentation |

**No implementation yet.**

# 2. Schemas

## 2.1 `TaskContract` (`task_contract.py`)

```python
class TaskClass(StrEnum):      TRIAGE | PLAN | CODE_GEN
class TaskStatus(StrEnum):     PENDING | IN_PROGRESS | COMPLETED | FAILED | CANCELLED

class TaskContract(BaseModel):
    task_id: UUID            = uuid4()           # default
    task_class: TaskClass
    skill_id: str
    prompt: str
    context: dict            = {}
    requester_agent_id: str
    target_agent_id: str
    created_at: datetime     = now(UTC)
    timeout_s: float         = 300.0
    metadata: dict           = {}
```

Validation rules (Pydantic v2 defaults):

- `task_id` MUST be a UUID; auto-generated if absent.
- `task_class`, `skill_id`, `prompt`, `requester_agent_id`, `target_agent_id`
  are required (no default).
- `timeout_s` is a positive float (no explicit min validator yet — TODO).
- `context` and `metadata` are arbitrary JSON-serialisable dicts.

> Note: CIPHER_LLD §10.1 shows lowercase enum values (`"triage"`,
> `"pending"`); the implementation uses **uppercase** StrEnum members. The
> implementation is the source of truth; LLD will be updated.

## 2.2 `TaskResult`

```python
class TaskResult(BaseModel):
    task_id: UUID
    status: TaskStatus
    output: dict             = {}
    artifact_refs: list[str] = []
    error_message: str | None = None
    completed_at: datetime   = now(UTC)
    duration_ms: float | None = None
```

`artifact_refs` are opaque URIs (e.g. `minio://cipher-artifacts/lld.csv`,
verified in `test_schemas.py::TestTaskResult`).

## 2.3 `AgentCard` (`agent_card.py`)

```python
class SkillDescriptor(BaseModel):
    skill_id: str
    name: str
    description: str
    supported_task_classes: list[str] = []
    v_cycle_stages: list[str] = []

class AgentCard(BaseModel):
    agent_id: str
    name: str
    description: str
    version: str = "0.1.0"
    url: str
    skills: list[SkillDescriptor] = []
    supported_protocols: list[str] = ["a2a/v1"]
    metadata: dict[str, str] = {}
```

Adapted from the Google A2A AgentCard spec. `version` enables backwards
discrimination across protocol revisions.

## 2.4 `ArtifactRelation` (`artifact_relation.py`)

```python
class RelationType(StrEnum):
    DERIVES_FROM | REFINES | IMPLEMENTS | TESTS | SUPERSEDES | REFERENCES

class ArtifactRelation(BaseModel):
    relation_id: UUID        = uuid4()
    source_artifact_id: str
    target_artifact_id: str
    relation_type: RelationType
    v_cycle_stage: str | None = None
    created_at: datetime     = now(UTC)
    created_by_agent: str | None = None
    metadata: dict[str, str] = {}
```

## 2.5 `CloudEvent` (`cloud_event.py`)

CloudEvents v1.0-compliant envelope: `id`, `source`, `type`, `specversion="1.0"`,
`time`, `subject`, `datacontenttype="application/json"`, `data`.

## 2.6 DevNex types (`devnex_types.py`)

`VCycleStage` enumerates `S1N1`..`S9N1`. `NodeStatus` covers
`PENDING|RUNNING|COMPLETED|FAILED|SKIPPED`. `NodeResult`, `SkillManifest`,
`WorkflowDefinition`, `BridgeRequest`, `BridgeResponse` are DevNex-internal
but kept in Core to avoid the AAL → AAL coupling that motivated T-029.

# 3. Adapters

## 3.1 `RedisClient` (`redis_client.py`)

- **Connection.** `aioredis.from_url(REDIS_URL, decode_responses=True)`.
  Internal pool managed by `redis-py`.
- **Public API.** `connect()`, `close()`, `pool` (raises if disconnected),
  `ping()`, `get`, `set(key, value, expire_s=None)`, `delete`, `exists`,
  `expire`, `keys(pattern="*")`.
- **Retry policy.** None — caller responsibility. **TODO.**

## 3.2 `MemgraphClient` (`memgraph_client.py`)

- **Connection.** `neo4j.AsyncGraphDatabase.driver(MEMGRAPH_URI)`; single
  driver per process.
- **Public API.** `connect()`, `close()`, `driver`, `health_check()`
  (`MATCH (n) RETURN count(n)`).
- **Retry policy.** None. Cypher execution is performed by callers.

## 3.3 `QdrantHealthClient` (`qdrant_client_wrapper.py`)

- **Connection.** httpx async GET against `QDRANT_URL/healthz`.
- **Public API.** `health_check() -> bool`. Vector CRUD is NOT in scope of
  this wrapper — MKF owns the full Qdrant client. **Stub-ish by design.**

## 3.4 `MinioStore` (`minio_client.py`)

- **Connection.** `minio.Minio(endpoint, access_key, secret_key, secure=False)`.
  Credentials from env (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`) default to
  `cipher` / `cipher_secret`.
- **Public API.** `ensure_bucket()` (creates `cipher-artifacts` if missing),
  `bucket_exists()`, `put_object(key, data, content_type)`,
  `get_object(key) -> bytes`.
- **Retry policy.** None — the `minio` SDK applies its own HTTP retry.

## 3.5 SQLite factories (`sqlite_factory.py`)

All three factories:

1. Resolve a directory from `CIPHER_SQLITE_DIR` (default `deploy/local/data/sqlite`).
2. `mkdir -p` the parent directory.
3. `sqlite3.connect(path)` then `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`.
4. Execute idempotent `CREATE TABLE IF NOT EXISTS` DDL.

Schemas:

- `cipher.db` → `config(key, value, updated_at)`, `agent_registry(agent_id, card_json, registered_at)`
- `audit.db` → `audit_log(id, timestamp, agent_id, action, detail_json, trace_id, span_id)` + indices on `agent_id`, `timestamp`
- `checkpoints.db` → `checkpoints(thread_id, checkpoint_id, parent_id, checkpoint BLOB, metadata, created_at)`, `writes(thread_id, checkpoint_id, task_id, channel, value BLOB)` — LangGraph-compatible

## 3.6 `StateStore` (`state_store.py`)

Redis-backed K/V replacing the original DevNex JSON `StateStore` (ADR-0003
§1.3, T-014). `save/load/delete/exists` operate on JSON-encoded values under
the namespace prefix `cipher:state:` (configurable per instance).

# 4. CipherOrchestrator (`orchestrator.py`)

## 4.1 Responsibilities

- Own a registry of child orchestrators keyed by name (e.g. `"devnex"`).
- Advertise the well-known infra URLs as properties:
  - `llm_gateway_url == "http://127.0.0.1:8200"`
  - `a2a_url == "http://127.0.0.1:8100"`
- Provide an async lifecycle (`start()` / `stop()`) for future use.
- Expose a `devnex` convenience property (`get_child("devnex")`).

## 4.2 Child registration API

```python
orchestrator = CipherOrchestrator()
orchestrator.register_child("devnex", devnex_orch)
orchestrator.get_child("devnex")  # -> devnex_orch
orchestrator.devnex                # -> devnex_orch
```

## 4.3 Lifecycle

- `__init__` logs `"CipherOrchestrator initialized"`.
- `start()` flips `_running` → `True`, logs child count. **Does NOT call
  `.start()` on children** — children manage their own lifecycle today.
- `stop()` flips `_running` → `False`.
- `is_running` property exposes the flag.

## 4.4 Known gap

Per `docs/SESSION_HANDOFF.md` §4.3: the mother orchestrator is created in
`run_poc.py` but **not passed to `CipherMainWindow`**, so DevNex is created
independently inside `cipher/gui/main_window.py` and never registered. To
complete the wiring, `run_poc.py` must pass the instance to the window and
the window must call `orchestrator.register_child("devnex", devnex_orch)`
once DevNex is constructed. **Open TODO.**

# 5. OTel (`otel/tracing.py`)

## 5.1 Bootstrap

```python
init_tracing(service_name="cipher",
             otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT",
                                          "http://localhost:4317"))
```

- Resource attribute: `service.name=<service_name>`.
- Exporter: `OTLPSpanExporter(endpoint, insecure=True)` (gRPC).
- Processor: `BatchSpanProcessor` (async, batched).
- Global state: sets `_initialized = True`; idempotent if called twice
  (OTel itself enforces single TracerProvider).

## 5.2 Span naming convention

The `@traced(name=...)` decorator defaults to
`"{func.__module__}.{func.__qualname__}"` when no name is provided.
Recommended convention (from CIPHER_LLD §10.5 example
`"skill.s1n1.execute"`):

```
<surface>.<component>.<operation>
e.g.  skill.s1n1.execute
      adapter.redis.set
      orchestrator.devnex.run_node
```

## 5.3 Sync / async handling

`@traced` inspects the wrapped function with `inspect.iscoroutinefunction` and
selects an async or sync wrapper accordingly. Both wrappers:

1. Open `tracer.start_as_current_span(span_name)`.
2. Set any `attributes` provided at decoration time.
3. On success: `span.set_status(StatusCode.OK)`.
4. On exception: `span.set_status(StatusCode.ERROR, str(exc))`,
   `span.record_exception(exc)`, re-raise.

## 5.4 Propagation

Not currently configured. Cross-service propagation (e.g. NATS message
headers, A2A HTTP headers) requires `opentelemetry.propagate.inject` /
`extract`. **TODO.**

# 6. Configuration

All Core configuration is environment-variable driven; `ComposeDriver`
centralises the defaults:

| Variable | Default | Consumer |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | `RedisClient`, `StateStore` |
| `MEMGRAPH_URI` | `bolt://localhost:7687` | `MemgraphClient` |
| `QDRANT_URL` | `http://localhost:6333` | `QdrantHealthClient` |
| `MINIO_ENDPOINT` | `localhost:9000` | `MinioStore` |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `cipher` / `cipher_secret` | `MinioStore` |
| `NATS_URL` | `nats://localhost:4222` | `ComposeDriver` (not used by Core itself) |
| `OPA_URL` | `http://localhost:8181` | `ComposeDriver` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | `init_tracing` |
| `LANGFUSE_HOST` | `http://localhost:3000` | `ComposeDriver` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `ComposeDriver` |
| `GCA_BRIDGE_URL` | `http://127.0.0.1:37778` | `ComposeDriver` |
| `CIPHER_SQLITE_DIR` | `deploy/local/data/sqlite` | `sqlite_factory` |
| `CIPHER_DEPLOY_DIR` | `deploy/local` | `ComposeConfig.from_env` |

# 7. Test Coverage

| Suite | File | Covers |
|---|---|---|
| Schemas round-trip | `tests/unit/test_schemas.py` | `TaskContract`, `TaskResult`, `AgentCard` (+ defaults), `ArtifactRelation`, `CloudEvent` JSON round-trip and stdlib-`json` compatibility |
| OTel decorator | `tests/unit/test_otel_tracing.py` | Sync + async span emission, attribute propagation, exception → `StatusCode.ERROR` |
| Redis client | `tests/unit/test_redis_client.py` | Adapter contract (presence verified; full read pending) |
| SQLite factory | `tests/unit/test_sqlite_factory.py` | DDL idempotency / WAL mode (presence verified) |
| State store | `tests/unit/test_state_store.py` | Redis-backed save/load (presence verified) |
| Compose driver | `tests/unit/test_compose_driver.py` | Endpoint resolution (presence verified) |
| Adapters infra | `tests/unit/test_adapters_infra.py` | Cross-adapter smoke (presence verified) |

No tests yet exist for `CipherOrchestrator` itself or for
`cipher/observability/`. **TODO.**

# 8. TODOs

1. **Wire `CipherOrchestrator` as the parent of `DevNexOrchestrator`** —
   resolve SESSION_HANDOFF §4.3 by passing the mother instance into
   `CipherMainWindow` and calling `register_child("devnex", …)` once DevNex
   is constructed. Add a unit test asserting registration and lifecycle.
2. **Implement `cipher/observability/`** — decide whether structured logging
   (JSONL with trace/span IDs) and Langfuse linkage live here vs. under
   `core/otel/`. Today the package is empty.
3. **Schema versioning policy** — add an explicit `schema_version` (or rely
   on the existing `AgentCard.version` / `CloudEvent.specversion` pattern)
   across `TaskContract`, `TaskResult`, `ArtifactRelation`.
4. **Adapter retries** — introduce a shared `tenacity`-based helper for
   transient network errors in `RedisClient`, `MemgraphClient`, and
   `MinioStore`.
5. **OTel propagation** — wire `inject`/`extract` for A2A HTTP and NATS
   message headers so traces span ARE → AAL → MKF.
6. **Connection-pool sizing** — expose explicit pool size / max-overflow
   options on `RedisClient` and `MemgraphClient`.
7. **Migrate `contracts.py`** — either Pydantic-ify
   `Budget`/`TaskMessage`/`TaskEnvelope` and re-export from `schemas`, or
   delete if dead.
8. **Lifecycle propagation** — have `CipherOrchestrator.start()/stop()`
   actually call `start()`/`stop()` on registered children when they expose
   the protocol.
9. **`QdrantHealthClient`** — decide whether to fold it into MKF's full
   client or keep as a minimal liveness probe.
10. **Sync-aware `@traced`** — currently `inspect.iscoroutinefunction` is
    evaluated **once** at decoration; verify behaviour with `functools.wraps`
    on partials and generators (suspected TODO).
