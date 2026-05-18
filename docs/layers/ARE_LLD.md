---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# ARE — Low-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | LLD-ARE-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.3 (Software Detailed Design) |
| Layer | ARE — Agent Runtime Environment |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dir | `cipher/are/` |
| Companion HLD | `docs/layers/ARE_HLD.md` (HLD-ARE-001) |
| Authoritative sources | `cipher/are/a2a_server/server.py`, `cipher/are/a2a_server/task_handler.py`, `cipher/are/skill_loader/loader.py`, `cipher/core/schemas/agent_card.py`, `cipher/core/schemas/task_contract.py`, `run_poc.py`, `tests/unit/test_sprint2.py`, `tests/unit/test_schemas.py`, `docs/CIPHER_LLD.md` §8 |

---

## §1 Module Inventory

| Path | LOC | Role |
|---|---|---|
| `cipher/are/__init__.py` | 3 | Package marker; docstring only — no exports. |
| `cipher/are/a2a_server/__init__.py` | 3 | Package marker. |
| `cipher/are/a2a_server/server.py` | 77 | FastAPI `app`, in-memory task registries, four HTTP routes, `_dispatch_task` coroutine. |
| `cipher/are/a2a_server/task_handler.py` | 22 | `handle_task(task)` — resolves skill, awaits `execute`, emits `FAILED` `TaskResult` on miss. |
| `cipher/are/skill_loader/__init__.py` | 3 | Package marker. |
| `cipher/are/skill_loader/loader.py` | 43 | `Skill` Protocol, `SkillLoader` class, `get_skill_loader()` singleton accessor. |

External companions:

| Path | Role |
|---|---|
| `cipher/core/schemas/task_contract.py` | `TaskContract`, `TaskResult`, `TaskStatus`, `TaskClass`. |
| `cipher/core/schemas/agent_card.py` | `AgentCard`, `SkillDescriptor`. |
| `cipher/core/otel.py` | `@traced` decorator used on the submit and handle paths. |
| `run_poc.py` | Imports `app as a2a_app`, registers `S1N1Skill`, launches uvicorn on `:8100` in a daemon thread. |

---

## §2 A2A Endpoints

All routes are served from the `FastAPI` instance in
`cipher/are/a2a_server/server.py`, bound to `127.0.0.1:8100` by `run_poc.py`.

| Route | Method | Request body | Response (HTTP) | Response body |
|---|---|---|---|---|
| `/health` | GET | — | 200 | `{"status": "ok", "service": "a2a-server"}` |
| `/v1/tasks` | POST | `TaskContract` JSON (see §4) | 202 | `{"task_id": "<uuid>", "status": "PENDING"}` |
| `/v1/tasks/{task_id}` | GET | path: `task_id: UUID` | 200 if known; 404 if unknown | If `task_id in _results`: full `TaskResult` (`model_dump(mode="json")`). Else if in `_tasks`: `{"task_id": "<uuid>", "status": "IN_PROGRESS"}`. Else `{"detail": "Task not found"}`. |
| `/v1/tasks/{task_id}/stream` | GET | path: `task_id: UUID` | 200 SSE; 404 if unknown | `text/event-stream`; each frame `data: <json>\n\n`. First frame: `{"task_id": "<uuid>", "status": "IN_PROGRESS"}`. Final frame: serialized `TaskResult`. Stream closes when the frame contains `"status":"COMPLETED"` or `"status":"FAILED"`. |

### 2.1 Submit-path detail

`submit_task` is annotated `@traced(name="a2a.submit_task", attributes={"layer": "are"})`.
Sequence on a successful submit:

1. Store `task` in `_tasks[task.task_id]`.
2. Allocate `asyncio.Queue` at `_events[task.task_id]`.
3. Fire-and-forget `asyncio.create_task(_dispatch_task(task))`.
4. Return 202 with `{task_id, status: "PENDING"}`.

`_dispatch_task`:

1. Push `{"task_id": "...", "status": "IN_PROGRESS"}` onto the event queue.
2. Lazy import `handle_task` (`from cipher.are.a2a_server.task_handler import handle_task`).
3. Await `handle_task(task)`; on success, store the `TaskResult` in
   `_results` and push its JSON onto the queue.
4. On any exception, synthesize a `TaskResult(status=FAILED, error_message=str(e))`,
   store, and push.

There is no cancellation path, no timeout enforcement against
`TaskContract.timeout_s`, and no client-disconnect handling on the SSE side.

### 2.2 SSE termination semantics

`stream_task` reads from the queue until a payload contains the literal
substring `"status":"COMPLETED"` or `"status":"FAILED"` (string match, not
JSON parse) — at which point the generator breaks. The queue object itself
is not deleted from `_events` after termination.

---

## §3 SkillLoader Mechanism

### 3.1 Discovery

There is **no auto-discovery**. Skills are imported and instantiated
explicitly by the entry-point (`run_poc.py`). No plugin entry-points
(`importlib.metadata.entry_points`), no path-scan, no manifest file.

### 3.2 Registration

```python
loader = get_skill_loader()          # module-level singleton
loader.register(S1N1Skill())          # writes self._registry[skill.skill_id] = skill
```

`register` is idempotent in the sense that a duplicate `skill_id` simply
overwrites the prior entry. There is no logging or error on collision.

### 3.3 Invocation

The handler path:

```python
loader = get_skill_loader()
skill = loader.resolve(task.skill_id)        # dict.get → Skill | None
if skill is None:
    return TaskResult(status=FAILED, error_message="Skill not found: ...")
return await skill.execute(task)
```

`Skill.execute` is a coroutine returning a `TaskResult`. Skills are expected
to set `task_id`, `status`, and either `output` / `artifact_refs` or
`error_message`. The S1N1 reference skill (`cipher/agents/devnex/skills/vcycle_s1n1/skill.py`)
measures `duration_ms` itself; the ARE does not.

### 3.4 Lifecycle

Skill instances live as long as the `SkillLoader` singleton — i.e., for the
process lifetime. There is no `unregister`, no health probe, no
re-instantiation on failure.

### 3.5 Currently registered skills (POC)

| skill_id | Class | Module | Registered at |
|---|---|---|---|
| `vcycle_s1n1` | `S1N1Skill` | `cipher.agents.devnex.skills.vcycle_s1n1.skill` | `run_poc.py` line 44 |
| `devnex_orchestrator` | `DevNexAdapter` | `cipher.agents.devnex.adapter` | **Not registered anywhere in tree.** Stub only. |

---

## §4 AgentCard Schema

Defined in `cipher/core/schemas/agent_card.py` (Pydantic v2 `BaseModel`).

### 4.1 `SkillDescriptor`

| Field | Type | Default | Notes |
|---|---|---|---|
| `skill_id` | `str` | — | Matches the key registered in `SkillLoader`. |
| `name` | `str` | — | Human-readable. |
| `description` | `str` | — | — |
| `supported_task_classes` | `list[str]` | `[]` | String form (not the `TaskClass` enum) — type drift vs. `TaskContract.task_class`. See §7. |
| `v_cycle_stages` | `list[str]` | `[]` | Free-form stage tags (e.g., `"S1N1"`). |

### 4.2 `AgentCard`

| Field | Type | Default | Notes |
|---|---|---|---|
| `agent_id` | `str` | — | Stable identifier. |
| `name` | `str` | — | — |
| `description` | `str` | — | — |
| `version` | `str` | `"0.1.0"` | Semver expected, not enforced. |
| `url` | `str` | — | A2A endpoint URL. |
| `skills` | `list[SkillDescriptor]` | `[]` | — |
| `supported_protocols` | `list[str]` | `["a2a/v1"]` | Default factory. |
| `metadata` | `dict[str, str]` | `{}` | Free-form. |

Note: this diverges slightly from the LLD §10.2 sketch (which used
`endpoint: str = ""` and a `task_classes` field typed as `list[TaskClass]`).
The current code uses `url` and string `supported_task_classes`.

### 4.3 Where AgentCards are consumed

- `tests/unit/test_schemas.py::TestAgentCard` — round-trip serialization
  test only.

The ARE itself **does not consume `AgentCard` at runtime** (no card
registry, no discovery endpoint). This is a known gap (HLD §7 Q1–Q2).

---

## §5 Configuration

The ARE layer has no `.env` keys of its own. All configuration is
hard-coded or supplied at the call site.

| Setting | Source | Value |
|---|---|---|
| Bind host | `run_poc.py` line 34 | `127.0.0.1` |
| Bind port | `run_poc.py` line 27 (`A2A_PORT`) | `8100` |
| Uvicorn log level | `run_poc.py` line 34 | `"warning"` |
| FastAPI title / version | `server.py` line 14 | `"CIPHER A2A Server"` / `"0.1.0"` |
| OTel attributes | decorators in `server.py` / `task_handler.py` | `layer="are"` |
| Skill registrations | `run_poc.py` lines 43–45 | hardcoded `S1N1Skill()` |

No CLI flags, no env-var overrides, no config file. The audit / policy
endpoints expected by HLD §3.6 are not configured because they are not
wired (see ARE_HLD §7 Q3).

---

## §6 Test Coverage

| Test file | Class / function | Coverage |
|---|---|---|
| `tests/unit/test_sprint2.py` | `TestSkillLoader::test_register_and_resolve` | Verifies `register` then `resolve` round-trip on a `MagicMock` skill. |
| `tests/unit/test_sprint2.py` | `TestSkillLoader::test_resolve_missing_returns_none` | `resolve` of unknown id returns `None`. |
| `tests/unit/test_sprint2.py` | `TestSkillLoader::test_list_skills` | `list_skills` returns registered ids. |
| `tests/unit/test_schemas.py` | `TestAgentCard` | `AgentCard` JSON round-trip; verifies default `supported_protocols == ["a2a/v1"]`. |

Gaps (no automated test today):

- `POST /v1/tasks` happy path.
- `GET /v1/tasks/{id}` for unknown id (404).
- `GET /v1/tasks/{id}/stream` SSE event ordering.
- `_dispatch_task` exception-to-`FAILED` mapping.
- `handle_task` with unknown `skill_id`.
- `get_skill_loader()` singleton identity.
- Concurrent submits (race on `_tasks` / `_events` dict mutation).
- No integration test that boots the FastAPI app via `httpx.AsyncClient` /
  `TestClient`.

---

## §7 TODOs

| # | Item | Source / driver |
|---|---|---|
| 1 | Implement `GET /v1/agents` (and/or `/.well-known/agent-card.json`) backed by an `AgentRegistry` keyed by `agent_id`. | ARE_HLD §7 Q1–Q2 |
| 2 | Wire GCL `policy.evaluate()` and `audit.record()` into `submit_task` and `_dispatch_task` per `docs/CIPHER_HLD.md` §3.6. | HLD §3.6 line 522, Rule 4 line 1194 |
| 3 | Validate `target_agent_id` vs. skill owner and `task_class` vs. `SkillDescriptor.supported_task_classes` in `handle_task`. | LLD §4.1 cross-check |
| 4 | Honor `TaskContract.timeout_s` — wrap `skill.execute(task)` in `asyncio.wait_for`. | `task_contract.py` line 38 |
| 5 | Cleanup of `_events[task_id]` queues after stream termination; bound queue size to apply backpressure. | ARE_HLD §6 |
| 6 | Replace in-memory `_tasks` / `_results` with a PKL-backed store (Redis or NATS JetStream) for crash recovery. | ARE_HLD §7 Q4 |
| 7 | Register `DevNexAdapter` (`skill_id="devnex_orchestrator"`) in `run_poc.py`, or remove the adapter. | ARE_HLD §7 Q6 |
| 8 | Reconcile `SkillDescriptor.supported_task_classes: list[str]` with `TaskContract.task_class: TaskClass` enum — use `list[TaskClass]`. | §4.1 drift |
| 9 | Add a discovery / hot-reload mechanism for skills (entry-points, manifest, or `importlib.reload`). | ARE_HLD §6 row "Skill hot-reload" |
| 10 | Replace SSE termination-by-substring check (`'"status":"COMPLETED"' in msg`) with a typed sentinel. | `server.py` line 54 |
| 11 | Add A2A integration tests using `httpx.ASGITransport` / `TestClient`. | §6 gaps |
| 12 | Define and document the JSON wire format for SSE frames (currently ad-hoc: a mix of literal strings and `model_dump_json()` output). | `server.py` lines 64, 68, 73–76 |
