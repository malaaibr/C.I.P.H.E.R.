---
doc_id: HLD-PKL-001
layer: PKL (Process / Knowledge Layer — Platform Kernel)
status: Draft
version: 0.1.0
last_updated: 2026-05-17
sources:
  - CIPHER_Repo/cipher/pkl/
  - CIPHER_Repo/cipher/orchestrator/
  - docs/CIPHER_HLD.md §3.2
  - docs/CIPHER_LLD.md §5
---

# PKL — High-Level Design

## §1. Purpose & Scope

The Platform Kernel Layer (PKL) is CIPHER's foundational asynchronous runtime. It provides
two primary services and one auxiliary service to every layer above it:

1. **NATS JetStream Event Bus** — a CloudEvents v1.0 pub/sub backbone used for inter-agent
   and inter-layer asynchronous communication (`cipher.task.*`, `cipher.gate.*`,
   `cipher.artifact.*` subjects).
2. **LangGraph Workflow Engine** — a checkpointed StateGraph runtime that executes
   multi-node agent workflows with durable resume from any node boundary.
3. **Observability health probes** — small health checks for Langfuse and the OTel
   Collector that allow higher layers to verify telemetry sinks are reachable before
   emitting spans.

**Scope boundary.** PKL owns the *event transport mechanism* and the *workflow execution
machinery*. It does **not** own:
- Agent business logic or V-cycle node implementations (that is AAL).
- Top-level agent supervision / mother-node behaviour (that is `cipher/core/orchestrator.py`
  — see §7 Open Questions).
- Storage adapters (those live in `cipher/core/adapters/`).
- LLM routing (that is TRF).

## §2. Position in the 7-Layer Architecture

```
GUI  ─────────────────────────────────────────────
AAL  (agents, DevNex, V-cycle nodes)             ▲ publish workflow events
ARE  (A2A, skills, agent registry)               │
GCL  (OPA, audit, HITL gates)                    │ emit cipher.gate.* events
TRF  (LLM Gateway, MCP tools)                    │
MKF  (Memgraph + Qdrant + Redis + MinIO)         │
PKL  ────  NATS bus + LangGraph engine  ─────────┤
DRS  (Docker Compose: nats container, sqlite vol)▼
```

PKL sits directly above DRS. Per the Layer Interaction Matrix in `CIPHER_HLD.md`, PKL has
write access into DRS (it requests the NATS container and the SQLite checkpoint volume)
and **read/publish access from every layer above**: agents publish task lifecycle events,
GCL publishes HITL gate events, MKF can publish artifact-creation events.

PKL is the only platform layer whose API surface is *push-based*: every other layer is
called synchronously; PKL is *subscribed to* by anyone who needs to react to platform
events.

## §3. External Interfaces

### 3.1 NATS subject conventions (per `CIPHER_archi.md` §6)

| Subject | CloudEvent `type` | Producer | Consumer(s) |
|---|---|---|---|
| `cipher.task.created` | `com.cipher.task.created.v1` | ARE on `tasks/send` | Orchestrator (AAL), Audit (GCL) |
| `cipher.task.completed` | `com.cipher.task.completed.v1` | Agent on terminal node | Orchestrator, GUI status panel |
| `cipher.task.failed` | `com.cipher.task.failed.v1` | Agent on exception | Orchestrator, Audit |
| `cipher.artifact.created` | `com.cipher.artifact.created.v1` | MKF on graph write | Memory Agent, downstream tasks |
| `cipher.gate.pending` | `com.cipher.gate.pending.v1` | GCL HITL Manager | GUI approval panel |
| `cipher.gate.resolved` | `com.cipher.gate.resolved.v1` | GCL on signed approval | suspended LangGraph runs |

All messages share the **CloudEvent envelope** defined in
`cipher/core/schemas/cloud_event.py`: `id`, `source`, `type`, `specversion=1.0`, `time`,
optional `subject`, `datacontenttype="application/json"`, and a free-form `data: dict`.

The single JetStream stream `CIPHER` captures all subjects under wildcard `cipher.>`.

### 3.2 LangGraph state schema

PKL exposes a generic `WorkflowState` TypedDict (`cipher/pkl/workflow/workflow_engine.py`):

```python
class WorkflowState(TypedDict, total=False):
    task_id: str
    skill_id: str
    prompt: str
    context: dict[str, Any]
    node_results: dict[str, Any]
    current_node: str
    status: str
    error: str | None
```

Higher layers register node functions via `WorkflowEngine.add_node(name, fn)` and either
build a sequential graph (`build_sequential()`) or, when richer topologies are needed,
access the underlying `StateGraph` directly. Checkpointing uses
`AsyncSqliteSaver.from_conn_string(...)` against the file
`deploy/local/data/sqlite/checkpoints.db`.

## §4. Internal Decomposition

```
cipher/pkl/
├── event_bus/
│   └── nats_bus.py            # NatsBus — async JetStream wrapper
├── workflow/
│   └── workflow_engine.py     # WorkflowEngine — LangGraph StateGraph runner
└── observability/
    └── langfuse_check.py      # Langfuse + OTel Collector HTTP health probes
```

Three modules, no internal cross-imports. Each subpackage is independently importable
and independently testable.

`cipher/orchestrator/` (sibling top-level dir) is currently a **scaffold only**:
`lifecycle.py` defines `AgentState` enum and `AgentDescriptor` dataclass; the README
labels it "Phase 1 control-plane scaffold" with planned (not implemented) responsibilities
for agent process spawning, V-cycle routing, checkpointing, and HITL suspend/resume.

## §5. Dependencies

| Dependency | Kind | Provider |
|---|---|---|
| NATS server `:4222` | runtime infra | DRS (`deploy/local/docker-compose.yml`) |
| SQLite file `checkpoints.db` | runtime infra | DRS Storage Fabric |
| `nats-py` | library | pyproject.toml |
| `langgraph`, `langgraph-checkpoint-sqlite` | library | pyproject.toml |
| `pydantic` | library | for CloudEvent / WorkflowState |
| `httpx` | library | for observability health probes |
| `cipher.core.schemas.cloud_event.CloudEvent` | internal | Core layer schema |

PKL has **no upward dependencies**. It does not import from `cipher/agents/`,
`cipher/are/`, `cipher/trf/`, `cipher/gcl/`, or `cipher/gui/`. This is enforced by code
review; there is no automated import-linter rule yet (see §7).

## §6. Quality Attributes

| Attribute | Target | Mechanism | Status |
|---|---|---|---|
| Event durability | At-least-once delivery | NATS JetStream durable consumers, `msg.ack()` after handler completes | implemented |
| Event ordering | Per-subject FIFO | JetStream default per-subject ordering | inherited from NATS |
| Replay | Resume from any checkpoint | `AsyncSqliteSaver` keyed by `thread_id` | implemented (sequential graphs only) |
| Idempotence | Handler-side, not bus-side | Each subscriber must dedupe on `CloudEvent.id` | **not enforced** — convention only |
| Observability | OTLP spans for every node | OTel Collector receives spans from agents; PKL itself emits no spans | partial (probe-only) |
| Back-pressure | JetStream consumer max-acks-pending | not configured in MVP | **stub** |
| Stream retention | "limits" policy default | not customised | acceptable for MVP |

## §7. Open Questions

1. **PKL vs Core orchestration boundary.** Two distinct orchestrators exist:
   - `cipher/core/orchestrator.py::CipherOrchestrator` — the mother node. Owns child
     agent orchestrators (DevNex, Voice, GCA Invoker), holds the LLM gateway and A2A
     server URLs. Lives in the **Core** layer, not PKL.
   - `cipher/orchestrator/` — a Phase-1 scaffold with `AgentState` and `AgentDescriptor`
     only. Per its README it is intended to handle agent process spawning, V-cycle
     routing, checkpointing, and HITL suspend/resume — *workflow-level orchestration*
     that conceptually belongs alongside the LangGraph engine in PKL.

   These are **two different things**: `CipherOrchestrator` is an agent-tree supervisor
   (Core); the PKL `WorkflowEngine` is a per-task state machine. The `cipher/orchestrator/`
   dir is currently neither — it is an empty placeholder. **Decision needed**: either
   (a) fold `cipher/orchestrator/` into `cipher/pkl/workflow/` as the per-task lifecycle
   manager, or (b) keep it separate as a "task scheduler" sibling to PKL. Until resolved,
   new workflow-level code should land in `cipher/pkl/workflow/`.

2. **Conditional / branching graphs.** `WorkflowEngine.build_sequential()` only wires
   linear `n1 → n2 → ... → END`. DevNex V-cycle nodes have HITL gates that need
   conditional edges. The engine exposes the underlying `StateGraph` via `self._graph`
   but provides no helper for conditional construction.

3. **Subject naming drift.** Tests use `cipher.tasks.created` (plural); the architecture
   doc uses `cipher.task.created` (singular). One of the two needs to win and be linted.

4. **No backpressure / DLQ.** Failed handlers re-deliver indefinitely; there is no
   dead-letter subject or max-deliver cap configured.

5. **No import-linter enforcement** of the "PKL imports nothing above DRS/Core schemas"
   rule.
