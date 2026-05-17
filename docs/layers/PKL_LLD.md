---
doc_id: LLD-PKL-001
layer: PKL (Process / Knowledge Layer — Platform Kernel)
status: Draft
version: 0.1.0
last_updated: 2026-05-17
related: HLD-PKL-001
sources:
  - CIPHER_Repo/cipher/pkl/event_bus/nats_bus.py
  - CIPHER_Repo/cipher/pkl/workflow/workflow_engine.py
  - CIPHER_Repo/cipher/pkl/observability/langfuse_check.py
  - CIPHER_Repo/cipher/orchestrator/lifecycle.py
  - CIPHER_Repo/tests/unit/test_nats_bus.py
  - CIPHER_Repo/tests/unit/test_workflow_engine.py
---

# PKL — Low-Level Design

## §1. Module Inventory

| Path | LOC | Purpose | Status |
|---|---:|---|---|
| `cipher/pkl/__init__.py` | 3 | Package marker | stable |
| `cipher/pkl/event_bus/__init__.py` | 7 | Re-exports `NatsBus` | stable |
| `cipher/pkl/event_bus/nats_bus.py` | 85 | Async NATS JetStream wrapper with CloudEvent (de)serialisation | implemented, minimal |
| `cipher/pkl/workflow/__init__.py` | 3 | Package marker | stable |
| `cipher/pkl/workflow/workflow_engine.py` | 69 | LangGraph `StateGraph` runner + `AsyncSqliteSaver` checkpointing | implemented, sequential-only |
| `cipher/pkl/observability/__init__.py` | 3 | Package marker | stable |
| `cipher/pkl/observability/langfuse_check.py` | 39 | HTTP health probes for Langfuse and OTel Collector | implemented |
| `cipher/orchestrator/__init__.py` | 2 | Package marker | scaffold |
| `cipher/orchestrator/lifecycle.py` | 30 | `AgentState` enum + `AgentDescriptor` dataclass | **scaffold only** — no behaviour |
| `cipher/orchestrator/README.md` | — | Lists *planned* responsibilities (agent spawn, V-cycle routing, checkpoint, HITL) | doc only |

The PKL itself is **~210 LOC of production code** across 3 modules. The
`cipher/orchestrator/` sibling adds 30 LOC of type-only scaffolding with no callers.

## §2. Key Data Structures

### 2.1 CloudEvent envelope (`cipher/core/schemas/cloud_event.py`)

```python
class CloudEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source: str                                # e.g. "cipher.devnex.s1n1"
    type: str                                  # e.g. "com.cipher.task.completed.v1"
    specversion: str = "1.0"
    time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    subject: str | None = None
    datacontenttype: str = "application/json"
    data: dict[str, Any] = Field(default_factory=dict)
```

Owned by the **Core** layer; PKL only consumes it. Serialised on the wire as
`event.model_dump_json().encode()` and round-tripped through Pydantic on receive.

### 2.2 WorkflowState (`cipher/pkl/workflow/workflow_engine.py`)

```python
class WorkflowState(TypedDict, total=False):
    task_id: str
    skill_id: str          # e.g. "vcycle_s1n1"
    prompt: str
    context: dict[str, Any]
    node_results: dict[str, Any]
    current_node: str
    status: str            # "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
    error: str | None
```

`total=False` lets nodes return partial updates which LangGraph merges into the state
dict between transitions.

### 2.3 AgentDescriptor (`cipher/orchestrator/lifecycle.py`)

```python
class AgentState(str, Enum):
    SPAWNED, READY, RUNNING, WAITING, SUSPENDED, TERMINATED, FAILED

@dataclass(slots=True)
class AgentDescriptor:
    agent_id: str
    agent_name: str
    trust_tier: str
    budget: Budget                  # from cipher.core.contracts
    scopes: list[str]
    state: AgentState = AgentState.SPAWNED
    checkpoint_uri: str | None = None
```

**Currently unused** in code — defined for the planned agent lifecycle manager.

### 2.4 NATS connection state (`NatsBus`)

| Field | Type | Set by | Note |
|---|---|---|---|
| `_url` | `str` | `__init__` or `NATS_URL` env | default `nats://localhost:4222` |
| `_nc` | `nats.aio.client.Client \| None` | `connect()` | `None` until connected |
| `_js` | `JetStreamContext \| None` | `connect()` | created from `_nc.jetstream()` |
| `STREAM_NAME` | `"CIPHER"` (class const) | — | single stream for all subjects |
| `SUBJECTS` | `"cipher.>"` (class const) | — | catch-all wildcard |

`_ensure_stream()` calls `js.find_stream_info_by_subject(SUBJECTS)`; on any exception it
creates the stream with default retention.

## §3. Event Subject Naming Convention

Per `docs/CIPHER_archi.md` §6 (canonical), subjects use **singular noun** segments:

```
cipher.<domain>.<event>     # e.g. cipher.task.created, cipher.gate.pending
```

`CloudEvent.type` mirrors the subject with a reverse-DNS prefix and version suffix:

```
com.cipher.<domain>.<event>.v<N>     # e.g. com.cipher.task.completed.v1
```

`CloudEvent.source` identifies the emitting component using dotted path notation, e.g.
`cipher.devnex.s1n1`, `cipher.gcl.hitl`, `cipher.mkf.memory_agent`.

**Known drift**: `tests/unit/test_nats_bus.py` uses `cipher.tasks.created` (plural). This
contradicts the architecture doc and should be aligned (see PKL_HLD §7.3).

Stream / consumer rules:
- One JetStream stream `CIPHER` captures all `cipher.>` subjects.
- Subscribers pass a `durable=<consumer-name>` string to survive reconnects.
- Handlers must `await msg.ack()` exactly once per message (done in the internal `_cb`
  inside `NatsBus.subscribe`).

## §4. Implementation Notes

### 4.1 Async-only API

Both `NatsBus` and `WorkflowEngine` are fully async (`async def`). No sync wrappers are
provided. Callers from synchronous contexts (e.g. the PyQt6 GUI thread) must dispatch
through `asyncio.run()` or use a `QThread` + `asyncio.new_event_loop()` pattern. This is
already done in `cipher/agents/devnex_assistant/interfaces/gui/workers/`.

### 4.2 Subscribe callback wrapping

`NatsBus.subscribe(subject, handler, durable)` wraps the user handler in an internal
`_cb(msg)` that:
1. Decodes the raw bytes (`msg.data.decode()`).
2. JSON-parses into a `dict`.
3. Validates against `CloudEvent` via `CloudEvent.model_validate(data)`.
4. Awaits the user handler with the typed event.
5. Acks the JetStream message.

Notes:
- The returned `sub` object is **not retained** — there is no `unsubscribe()` helper. The
  subscription lives until the NATS client closes.
- No try/except around handler invocation: a handler exception will propagate up through
  the NATS consumer task and likely cause re-delivery without ack.

### 4.3 Checkpoint lifecycle (LangGraph)

```python
async with AsyncSqliteSaver.from_conn_string(self._checkpoint_db) as saver:
    compiled = self._graph.compile(checkpointer=saver)
    config = {"configurable": {"thread_id": thread_id}}
    result = await compiled.ainvoke(initial_state, config=config)
```

The graph is compiled **inside every `run()` / `resume()` call**. This is acceptable for
the MVP but pays a recompile cost per invocation. The SQLite file is opened per call via
context manager — short-lived connection, no pool.

`resume(thread_id)` calls `ainvoke(None, config=...)`: passing `None` as the input tells
LangGraph to continue from the last checkpoint for that `thread_id`.

### 4.4 Graph topology

`build_sequential()` requires `len(self._nodes) >= 1` (asserts). It sets the first node
as entry, chains adjacent nodes with `add_edge`, and adds a final edge to the `END`
sentinel. **No helpers exist for conditional, parallel, or cyclic graphs** — callers
must drop down to the underlying `StateGraph` API via `engine._graph` (private).

### 4.5 Observability probes

`langfuse_health_check()` does a GET on `/api/public/health` (200 = OK). For the OTel
Collector, the function rewrites `:4317` (gRPC) to `:4318` (HTTP) and probes `/v1/health`,
accepting both 200 and 405 (405 means the endpoint exists but rejects GET — confirms
the receiver is up). Both probes return `bool`, swallowing `ConnectError` and
`TimeoutException`.

## §5. Configuration

| Env var | Default | Read by |
|---|---|---|
| `NATS_URL` | `nats://localhost:4222` | `nats_bus.get_nats_url()` |
| `LANGFUSE_HOST` | `http://localhost:3000` | `langfuse_check.get_langfuse_host()` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | `otel_collector_health_check()` |

Hard-coded constants:
- `NatsBus.STREAM_NAME = "CIPHER"`
- `NatsBus.SUBJECTS = "cipher.>"`
- `WorkflowEngine` default `checkpoint_db = "deploy/local/data/sqlite/checkpoints.db"`

There is no PKL-level config file; values are either env-driven or constructor args.

## §6. Test Coverage

### 6.1 Existing unit tests

| Test file | Covers | Style |
|---|---|---|
| `tests/unit/test_nats_bus.py` | `get_nats_url` env handling; `is_connected` flag; `publish` payload shape; `subscribe` registers callback; `close` clears state | Mocks `_js` and `_nc` with `AsyncMock` / `MagicMock`. No live NATS. |
| `tests/unit/test_workflow_engine.py` | `add_node` registers; `build_sequential` sets entry + edges; `WorkflowState` accepts typed dict | Mocks the entire `langgraph` module via `sys.modules.setdefault` before import. |

### 6.2 E2E coverage

| Test file | PKL coverage |
|---|---|
| `tests/e2e/test_live_infra.py` | Likely touches a live NATS container (not inspected here). |
| `tests/e2e/test_poc_spine.py` | Exercises end-to-end run path; will use PKL transitively. |

### 6.3 Gaps

- No test for `NatsBus.connect()` against a real NATS server (`_ensure_stream` is
  untested).
- No test for handler exception propagation / redelivery.
- No test for `WorkflowEngine.run()` or `.resume()` against a real `AsyncSqliteSaver`.
- No test that the subject naming convention is honoured by producers (the existing
  test in fact uses the *incorrect* plural form).
- No test for `langfuse_check`.

## §7. TODOs

1. **Resolve `cipher/orchestrator/` placement.** Currently a scaffold with no callers.
   Either implement the planned lifecycle manager here, fold it into
   `cipher/pkl/workflow/`, or delete the scaffold. (See PKL_HLD §7.1.)
2. **Add conditional-edge helpers** to `WorkflowEngine` so HITL-bearing graphs
   (DevNex S1–S9) can be constructed through PKL instead of bypassing it.
3. **Add `unsubscribe()`** and retain the `sub` handle returned by `js.subscribe`.
4. **Wrap handler invocation** in `NatsBus.subscribe._cb` with try/except + structured
   logging + configurable nack/term policy.
5. **Configure JetStream consumer limits** (`max_deliver`, `ack_wait`) instead of NATS
   defaults; add a DLQ subject like `cipher.dlq.>`.
6. **Cache the compiled LangGraph** inside `WorkflowEngine` so `run()` does not recompile
   on every invocation.
7. **Lift subject constants** into a single `cipher/pkl/event_bus/subjects.py` module
   and reference them from both producers and tests, eliminating the
   singular/plural drift between `CIPHER_archi.md` and `test_nats_bus.py`.
8. **Add import-linter rule** preventing PKL from importing anything in AAL/ARE/GCL/TRF/
   MKF/GUI.
9. **Emit PKL-internal OTel spans** for `publish`, `subscribe._cb`, `run`, `resume` so
   the bus and engine are observable in Langfuse/OTel, not just probe-able.
