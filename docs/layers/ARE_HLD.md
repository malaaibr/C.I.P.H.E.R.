---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# ARE — High-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | HLD-ARE-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Layer | ARE — Agent Runtime Environment |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dir | `cipher/are/` |
| Authoritative sources | `cipher/are/a2a_server/server.py`, `cipher/are/a2a_server/task_handler.py`, `cipher/are/skill_loader/loader.py`, `cipher/core/schemas/agent_card.py`, `cipher/core/schemas/task_contract.py`, `run_poc.py` (registration site), `docs/CIPHER_HLD.md` §3.6, `docs/CIPHER_LLD.md` §8 |

---

## §1 Purpose & Scope

The Agent Runtime Environment (ARE) is the **decoupling layer** between platform
infrastructure (DRS, PKL, MKF, TRF, GCL) and agent implementations (AAL). Per
`docs/CIPHER_HLD.md` (line 516), it mirrors AUTOSAR's RTE exactly: above the
ARE, the architecture style changes from layered to component/agent style.
Agents communicate exclusively through typed A2A `TaskContract` messages
brokered by the ARE; no agent shares Python memory with another (HLD Rule 5,
line 1196).

The ARE materializes two responsibilities:

1. **A2A protocol surface** — a FastAPI application (bound to `127.0.0.1:8100`
   in the POC) that accepts `TaskContract` submissions, returns a `task_id`,
   streams progress over Server-Sent Events (SSE), and exposes status polling.
2. **SkillLoader registry** — a process-local registry that maps `skill_id`
   strings to executable `Skill` instances. The A2A task handler resolves
   incoming tasks against this registry and dispatches to the matching skill.

**In scope (this doc).**
- The `FastAPI` app in `cipher/are/a2a_server/server.py`.
- The task dispatch path in `cipher/are/a2a_server/task_handler.py`.
- The `Skill` protocol and `SkillLoader` registry in
  `cipher/are/skill_loader/loader.py`.
- The `AgentCard` / `SkillDescriptor` schemas in
  `cipher/core/schemas/agent_card.py` (consumed at the ARE surface).
- The registration site in `run_poc.py` (`loader.register(S1N1Skill())`).

**Out of scope.**
- Agent implementations themselves (AAL — `cipher/agents/`).
- `TaskContract` schema definition (lives in Core schemas; ARE consumes it).
- Policy evaluation and audit (GCL is invoked side-channel; not yet wired in
  the ARE submit path — see §7).

---

## §2 Position in the 7-Layer Architecture

From the canonical dependency chain in `docs/CIPHER_HLD.md` line 255:

```
DRS → PKL → MKF → TRF → GCL → ARE → AAL → GUI
```

The ARE sits between GCL (below) and AAL (above). Per the Layer Interaction
Matrix (HLD lines 266–273), ARE may read from MKF, TRF and GCL, and is the
sole upward gateway to AAL. **The ARE boundary is the key decoupling point**
(HLD Rule 3, line 1192): below it, calls are layered API invocations; above
it, all communication is component-style A2A.

In the running POC (`run_poc.py`), the ARE is one of two FastAPI threads
launched alongside the TRF LLM Gateway and the PyQt6 GUI process.

---

## §3 External Interfaces

The ARE exposes one network-facing interface (HTTP + SSE) and one in-process
registration interface for skills.

### 3.1 A2A HTTP / SSE surface (`127.0.0.1:8100`)

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness probe (`{"status": "ok", "service": "a2a-server"}`). |
| `/v1/tasks` | POST | Submit a `TaskContract`; returns `{task_id, status="PENDING"}` with HTTP 202. |
| `/v1/tasks/{task_id}` | GET | Poll status — returns either the final `TaskResult` or `{status: "IN_PROGRESS"}`; 404 if unknown. |
| `/v1/tasks/{task_id}/stream` | GET | Server-Sent Events stream of task lifecycle events; closes after `COMPLETED` or `FAILED`. |

Full request/response shapes in `ARE_LLD.md` §2.

### 3.2 AgentCard / SkillDescriptor schema

Defined in `cipher/core/schemas/agent_card.py`. `AgentCard` advertises an
agent's identity (`agent_id`, `name`, `version`, `url`), supported protocols
(default `["a2a/v1"]`), and a list of `SkillDescriptor` entries. Each
`SkillDescriptor` carries `skill_id`, `name`, `description`,
`supported_task_classes`, and `v_cycle_stages`. **Status:** schema is defined
and used in unit tests, but the ARE A2A server does **not** currently expose a
discovery endpoint (e.g., `GET /v1/agents`). See §7.

### 3.3 Skill registration contract (in-process)

Skill objects conform to the `Skill` Protocol
(`cipher.are.skill_loader.loader.Skill`):

```python
class Skill(Protocol):
    @property
    def skill_id(self) -> str: ...
    async def execute(self, task: TaskContract) -> TaskResult: ...
```

Skills are registered against the process-wide singleton returned by
`get_skill_loader()`. In the current POC, registration happens in `run_poc.py`
at startup (`loader.register(S1N1Skill())`).

---

## §4 Internal Decomposition

The ARE has three internal components:

### 4.1 A2A FastAPI Server (`cipher/are/a2a_server/server.py`)

A single FastAPI application module. Holds three in-memory dicts keyed by
`task_id` (UUID): `_tasks` (submitted contracts), `_results` (completed
results), `_events` (per-task `asyncio.Queue` for SSE). The `submit_task`
endpoint enqueues an `asyncio.create_task(_dispatch_task(...))` and returns
immediately. The `_dispatch_task` coroutine posts an `IN_PROGRESS` event,
awaits the handler, then enqueues the final `TaskResult` JSON.

### 4.2 Task Handler (`cipher/are/a2a_server/task_handler.py`)

A thin dispatcher: looks up the skill via `SkillLoader.resolve(task.skill_id)`
and awaits `skill.execute(task)`. Returns a `TaskResult` with status
`FAILED` and `error_message` if the skill is not registered. Decorated with
`@traced(name="a2a.handle_task", attributes={"layer": "are"})` for OTel.

### 4.3 SkillLoader (`cipher/are/skill_loader/loader.py`)

A dict-backed registry (`self._registry: dict[str, Skill]`) with
`register`, `resolve`, and `list_skills`. Module-level
`_loader_instance` singleton accessed via `get_skill_loader()`.

There is **no AgentCard registry** as a distinct component yet; cards are a
schema only (see §7).

---

## §5 Dependencies

| Direction | Dependency | Use |
|---|---|---|
| Downward (consumed by ARE) | **Core schemas** | `TaskContract`, `TaskResult`, `TaskStatus`, `AgentCard`, `SkillDescriptor` (`cipher/core/schemas/`). |
| Downward | **Core OTel** | `@traced` decorator on `submit_task` and `handle_task` (`cipher.core.otel`). |
| Downward | **FastAPI / uvicorn** | Web framework (third-party, ≥ 0.111 per LLD §1 line 86). |
| Downward | **Python `asyncio`** | Task dispatch, SSE queues. |
| Upward (depends on ARE) | **AAL agent implementations** | Register skills with `SkillLoader` (e.g., `S1N1Skill`, `DevNexAdapter`). |
| Lateral | **TRF** | Skills invoked via the ARE typically call the LLM Gateway (TRF) — but that call is **inside** the skill, not the ARE itself. |
| Lateral | **GCL** | Per HLD §3.6, ARE should invoke `policy.evaluate()` on submit and `audit.record()` on completion. **Not wired in the current code.** See §7. |

The ARE does **not** directly call MKF, PKL substrate adapters, or DRS
services — these are skill-side concerns.

---

## §6 Quality Attributes

| Attribute | Current state |
|---|---|
| Agent / skill registration latency | O(1) dict insert; synchronous; performed once at process startup. No hot-reload path. |
| Task submission latency | HTTP 202 returned after a single dict insert and `asyncio.create_task`; no blocking I/O on the request path. |
| SSE backpressure | `asyncio.Queue` is unbounded — no producer throttling. A slow/disconnected consumer accumulates events in memory until process exit. No client-disconnect cleanup logic in `_dispatch_task`. |
| Skill hot-reload | Not supported. Re-registration overwrites the entry in `_registry` (last writer wins) but there is no file-watch / discovery mechanism. |
| Task persistence | `_tasks` / `_results` / `_events` are process-local in-memory dicts; restarting the A2A server loses all in-flight task state. |
| Concurrency model | Single-process uvicorn (`asyncio.run(server.serve())` in a daemon thread launched from `run_poc.py`); cooperative multitasking via `asyncio`. |
| Observability | `@traced` spans on `a2a.submit_task` and `a2a.handle_task` (layer attribute `"are"`). No metrics, no structured access log beyond uvicorn's `log_level="warning"`. |
| Auth / authz | None. The endpoint binds to `127.0.0.1` only; no JWT validation, no GCL policy check on submit. |
| Error handling | `_dispatch_task` catches all exceptions and emits a `FAILED` `TaskResult`; the handler likewise returns a `FAILED` result for unknown skills. No retry, no DLQ. |

---

## §7 Open Questions

1. **AgentCard discovery endpoint missing.** `AgentCard` and `SkillDescriptor`
   schemas exist, and HLD line 542 / LLD §10.2 describe agents advertising
   skills via cards, but the ARE FastAPI app does **not** expose a
   `GET /v1/agents` or `/.well-known/agent-card.json` route. How are remote
   peers (or the orchestrator) supposed to discover agents and skills today?
2. **No AgentCard registry component.** Skills are registered by `skill_id`
   only; there is no mapping from `agent_id` → `AgentCard` → owned skills.
   Should the SkillLoader be split into an AgentRegistry + per-agent skill
   table, or remain flat?
3. **GCL not wired into the submit path.** HLD §3.6 mandates policy evaluation
   and audit on every A2A submit. The current `submit_task` does neither.
   Should this happen in `server.py` (before dispatch) or in
   `task_handler.py` (around the skill call)?
4. **No persistence / no recovery.** All task state is in-memory dicts. Is
   PKL-backed durable storage (Redis / NATS JetStream) in scope for the POC
   ARE, or accepted as a known POC limitation?
5. **SSE consumer cleanup.** `_events[task_id]` queues are never deleted; a
   long-running server accumulates dead queues. What is the intended lifetime
   policy?
6. **`devnex_orchestrator` skill registered nowhere.** `DevNexAdapter`
   declares `skill_id = "devnex_orchestrator"` but `run_poc.py` only registers
   `S1N1Skill`. Intentional, or registration gap?
7. **`task_classes`, `requester_agent_id`, `target_agent_id` enforcement.**
   `TaskContract` carries these fields, but the ARE does not validate that
   `target_agent_id` matches the agent owning the resolved skill, nor that
   the resolved skill supports the declared `task_class`. Should the handler
   enforce this?
