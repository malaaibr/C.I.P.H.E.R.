---
doc_id: HLD-CORE-001
title: CIPHER Core — High-Level Design
layer: Core (shared SDK, orthogonal to 7-layer stack)
status: Draft
version: 0.1.0
last_updated: 2026-05-17
implementation_dirs:
  - cipher/core/
  - cipher/observability/
source_refs:
  - docs/CIPHER_HLD.md §10 (referenced)
  - docs/CIPHER_LLD.md §10 Core Module — Schemas & Adapters
  - docs/SESSION_HANDOFF.md §4.3 (CipherOrchestrator wiring)
---

# 1. Purpose & Scope

The **Core** module is CIPHER's shared SDK. It is consumed by every other layer
(DRS, GCL, PKL, MKF, TRF, ARE, AAL, GUI) but depends on none of them. Its
responsibilities are intentionally narrow:

1. **Shared schemas** — Pydantic v2 models that every layer encodes/decodes on
   the wire: `TaskContract`, `TaskResult`, `TaskStatus`, `TaskClass`,
   `AgentCard`, `SkillDescriptor`, `ArtifactRelation`, `RelationType`,
   `CloudEvent`, plus DevNex-specific types (`VCycleStage`, `NodeResult`,
   `SkillManifest`, `WorkflowDefinition`, `BridgeRequest`, `BridgeResponse`).
2. **Platform adapters** — thin async/sync wrappers around the infra clients
   running in the DRS Docker Compose stack: Redis 7 (working memory),
   Memgraph (knowledge graph via the Neo4j bolt driver), Qdrant (vector
   search health probe), MinIO (object store) and SQLite (config / audit /
   LangGraph checkpoints with WAL mode).
3. **OpenTelemetry instrumentation** — `init_tracing()`, `get_tracer()`, and
   the `@traced` decorator that wraps any sync or async callable in an OTel
   span with OTLP gRPC export.
4. **Mother orchestrator** — `CipherOrchestrator`, the top-level node that
   owns child orchestrators (DevNex, future agents) and advertises the
   well-known URLs of the LLM Gateway (`:8200`) and A2A Server (`:8100`).
5. **Substrate driver** — `ComposeDriver`/`ComposeConfig` expose the
   environment-resolved endpoints of every infra component to the rest of the
   codebase as a single typed surface.

Scope **excludes** business logic, workflow execution, LLM routing, RAG, GUI,
and policy evaluation — those belong to the seven layered modules.

# 2. Position in the 7-Layer Architecture

```
+----------------------------------------------------------+
|  GUI  |  AAL  |  ARE  |  TRF  |  MKF  |  PKL  |  GCL  |  | DRS
+----------------------------------------------------------+
                         |  imports
                         v
                +------------------+
                |   cipher.core    |  <- schemas, adapters,
                +------------------+      OTel, mother orch.
```

Core is **orthogonal** to the 7-layer stack. CIPHER_LLD §10 lists it as
"Module 10" rather than a layer; CIPHER_HLD §522 describes it as the library
surface "all agents depend on at their north interface". Every layer above
either:

- imports a schema from `cipher.core.schemas`,
- opens a backend connection through `cipher.core.adapters`, or
- decorates a function with `cipher.core.otel.traced`.

# 3. External Interfaces

| Surface | Module | Purpose |
|---|---|---|
| `from cipher.core.schemas import TaskContract, TaskResult, AgentCard, ArtifactRelation, CloudEvent, ...` | `cipher/core/schemas/__init__.py` | Wire-format Pydantic models for A2A, NATS, and the graph store |
| `RedisClient`, `MemgraphClient`, `QdrantHealthClient`, `MinioStore` | `cipher/core/adapters/` | Async/sync clients for the DRS infra services |
| `create_cipher_db()`, `create_audit_db()`, `create_checkpoints_db()` | `cipher/core/adapters/sqlite_factory.py` | WAL-mode SQLite factories for config, audit and LangGraph checkpoints |
| `StateStore(client, namespace)` | `cipher/core/adapters/state_store.py` | Redis-backed key-value persistence preserving the legacy DevNex `save()/load()` API |
| `init_tracing()`, `get_tracer()`, `@traced(...)` | `cipher/core/otel/tracing.py` | Bootstrap OTLP export and emit spans |
| `ComposeDriver`, `ComposeConfig.from_env()` | `cipher/core/substrate/compose_driver.py` | Resolved endpoint URLs for the local Docker Compose stack |
| `CipherOrchestrator()`, `.register_child(name, orch)`, `.get_child(name)`, `.start()`, `.stop()` | `cipher/core/orchestrator.py` | Mother-node lifecycle and child-orchestrator registry |

The `cipher/observability/` package is currently a placeholder
(`__init__.py` docstring only); structured-logging and audit instrumentation
hooks are TBD per its README.

# 4. Internal Decomposition

```
cipher/core/
  __init__.py
  contracts.py                # legacy dataclasses: Budget, TaskMessage, TaskEnvelope
  orchestrator.py             # CipherOrchestrator mother node
  README.md
  schemas/
    __init__.py               # re-exports
    task_contract.py          # TaskClass, TaskStatus, TaskContract, TaskResult
    agent_card.py             # AgentCard, SkillDescriptor
    artifact_relation.py      # RelationType, ArtifactRelation
    cloud_event.py            # CloudEvent (CloudEvents v1.0 envelope)
    devnex_types.py           # VCycleStage, NodeStatus, NodeResult, SkillManifest,
                              # WorkflowDefinition, BridgeRequest, BridgeResponse
  adapters/
    __init__.py
    redis_client.py           # RedisClient (async)
    memgraph_client.py        # MemgraphClient (async neo4j driver)
    qdrant_client_wrapper.py  # QdrantHealthClient (httpx health probe)
    minio_client.py           # MinioStore + get_minio_client()
    sqlite_factory.py         # create_cipher_db / create_audit_db / create_checkpoints_db
    state_store.py            # Redis-backed StateStore
  otel/
    __init__.py
    tracing.py                # init_tracing, get_tracer, @traced
  substrate/
    __init__.py
    compose_driver.py         # ComposeDriver, ComposeConfig

cipher/observability/
  __init__.py                 # placeholder
  README.md                   # planned: OTel, structured logging, audit hooks
```

# 5. Dependencies

| Dependency | Used by |
|---|---|
| `pydantic >= 2.0` | all `cipher/core/schemas/*` |
| `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc` | `cipher/core/otel/tracing.py` |
| `redis>=5` (async API) | `redis_client.py`, `state_store.py` |
| `neo4j` (AsyncGraphDatabase) | `memgraph_client.py` |
| `httpx` | `qdrant_client_wrapper.py` |
| `minio` | `minio_client.py` |
| `sqlite3` (stdlib) | `sqlite_factory.py` |

No upstream CIPHER layers are imported. Environment variables (`REDIS_URL`,
`MEMGRAPH_URI`, `QDRANT_URL`, `MINIO_ENDPOINT`, `OTEL_EXPORTER_OTLP_ENDPOINT`,
`CIPHER_SQLITE_DIR`, etc.) are the sole runtime coupling to DRS.

# 6. Quality Attributes

- **Schema stability.** Every schema includes a `version` (`AgentCard.version`)
  or a `specversion` (`CloudEvent`) field; non-version-bearing schemas
  (`TaskContract`, `ArtifactRelation`) rely on additive Pydantic fields with
  defaults so that JSON written by old producers continues to round-trip
  (verified by `tests/unit/test_schemas.py::test_round_trip`).
- **Adapter pool sizing.** `RedisClient` uses `redis.asyncio.from_url` which
  builds an internal connection pool; `MemgraphClient` reuses a single
  `AsyncDriver` per process. No explicit pool-size configuration is exposed
  yet — TODO.
- **Trace overhead.** `@traced` adds one `start_as_current_span` call and an
  optional attribute set per invocation; export is `BatchSpanProcessor` so
  emission is asynchronous. The decorator is a no-op on tracers when
  `init_tracing` has not been called (OTel returns the default no-op tracer).
- **WAL durability.** All SQLite factories set `PRAGMA journal_mode=WAL` and
  `synchronous=NORMAL` for concurrent reader safety with audit/checkpoint
  writers.
- **Wire fidelity.** `CloudEvent.datacontenttype` defaults to
  `application/json`; UTC timestamps are produced via
  `datetime.now(UTC)` in every schema.

# 7. Open Questions

1. **Parent–child wiring (SESSION_HANDOFF §4.3).** `CipherOrchestrator` is
   instantiated in `run_poc.py` but is **not yet passed to**
   `CipherMainWindow`. As a consequence `DevNexOrchestrator` is created
   independently and `orchestrator.register_child("devnex", devnex_orch)` is
   never called. The mother-node lifecycle (`start()`/`stop()`) therefore
   does not currently drive child orchestrators.
2. **`cipher/observability/` content.** The package is a placeholder.
   Decision needed on whether structured logging, audit emission, and
   Langfuse linkage live here or stay under `cipher/core/otel/` and
   `cipher/pkl/observability/`.
3. **Legacy `contracts.py`.** `Budget`, `TaskMessage`, `TaskEnvelope` are
   dataclass-based and not re-exported from `cipher.core.schemas`. Decision:
   migrate to Pydantic and unify, or mark deprecated.
4. **Schema versioning policy.** `TaskContract` and `ArtifactRelation` carry
   no explicit `version` field; if/when a breaking change is required, a
   policy (e.g. `schema_version: int = 1`) must be agreed.
5. **Adapter retries.** No retry/backoff is wired into any adapter today;
   callers handle failures. A shared retry helper (e.g. `tenacity`) may be
   warranted once production load patterns emerge.
6. **CipherOrchestrator skills surface.** It exposes `llm_gateway_url` and
   `a2a_url` but no typed client; consumers currently hit those endpoints via
   their own HTTP code. Whether to host a typed `A2AClient` here or in ARE
   is TBD.
