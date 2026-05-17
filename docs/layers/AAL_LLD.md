# AAL — Low-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | LLD-AAL-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.3 (Software Detailed Design) |
| Layer | AAL — Agent Application Layer |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dir | `cipher/agents/` |
| Companion HLD | `docs/layers/AAL_HLD.md` |
| Authoritative sources | `cipher/agents/__init__.py`, `cipher/agents/README.md`, `cipher/are/skill_loader/loader.py`, `run_poc.py` |

---

## §1 Layer-level Module Inventory

This document covers **only the AAL layer's shared surface** — the files that
belong to the layer itself rather than to a specific agent. Each agent
subpackage has its own LLD under `docs/agents/<agent>.md`.

| Module | Path | Purpose | Notes |
|---|---|---|---|
| Layer package marker | `cipher/agents/__init__.py` | Marks `cipher.agents` as a Python package. Single docstring: *"Agent package scaffold for the CIPHER local MVP."* No exports. | 2 lines. No `__all__`, no re-exports. |
| Layer README | `cipher/agents/README.md` | Human-readable map of the 10 agent subdirectories, separating "implementation target" (devnex_assistant, compliance, tool_agent, memory_agent) from "stubbed for later phases" (planner, asil_reviewer, research, test_agent, traceability). | 19 lines. |
| (Agent subpackages) | `cipher/agents/<agent>/` × 10 | One subdirectory per agent. Documented in `docs/agents/<agent>.md`. | Not in scope here. |

**There is no `cipher/agents/base.py`, no abstract `BaseAgent` class, and no
layer-level test directory** at the time of writing. See §3 and §5.

The 10 agent subpackages (from `cipher/agents/` listing) are:
`asil_reviewer`, `compliance`, `devnex`, `devnex_assistant`, `memory_agent`,
`planner`, `research`, `test_agent`, `tool_agent`, `traceability`.

---

## §2 Agent Registration Mechanism

### 2.1 The contract — `Skill` Protocol

The contract every agent must satisfy is defined **outside the AAL** in
`cipher/are/skill_loader/loader.py`:

```python
class Skill(Protocol):
    @property
    def skill_id(self) -> str: ...
    async def execute(self, task: TaskContract) -> TaskResult: ...
```

AAL agents implement this Protocol structurally — no explicit inheritance is
required because `Skill` is a `typing.Protocol`.

### 2.2 Registration today (POC, manual)

Registration is **performed by the process bootstrap, not by the agent
subpackages**. In `run_poc.py`:

```python
from cipher.are.skill_loader.loader import get_skill_loader
from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill
...
loader = get_skill_loader()
loader.register(S1N1Skill())
print(f"[CIPHER] Registered skills: {loader.list_skills()}")
```

`get_skill_loader()` returns a process-wide singleton `SkillLoader` instance.
`SkillLoader.register(skill)` keys the skill by `skill.skill_id` into an
in-memory `dict[str, Skill]`. The A2A server's task handler then resolves
skills by id (`cipher/are/a2a_server/task_handler.py`).

### 2.3 What each agent's `__init__.py` actually does

Inspecting the agent `__init__.py` files:

| Agent | `__init__.py` contents | Auto-registers? |
|---|---|---|
| `devnex/` | `"""DevNex Agent — automotive V-cycle LLD generation."""` + `from __future__ import annotations` | No |
| `compliance/` | `"""Compliance agent scaffold for the local MVP."""` | No |
| `memory_agent/` | `"""Memory agent scaffold for the local MVP."""` | No |
| `tool_agent/` | `"""Tool agent scaffold for the local MVP."""` | No |
| `devnex_assistant/` | See `docs/agents/devnex_assistant.md` | n/a (loaded indirectly via `devnex.adapter`) |
| `asil_reviewer/`, `planner/`, `research/`, `test_agent/`, `traceability/` | (no `__init__.py`; README-only stubs) | No |

**No agent registers itself on import.** Importing
`cipher.agents.devnex` has no side effects. The bootstrap must explicitly
instantiate the skill and call `loader.register(...)`.

### 2.4 Dispatch path

Once registered, a `TaskContract` flows top-down through:

```
A2A client  →  ARE A2A server  →  task_handler
                                       │
                                       ▼
                              loader.resolve(skill_id)
                                       │
                                       ▼
                              skill.execute(task)  ───►  TaskResult
                              (AAL agent code)
```

The `@traced(attributes={"layer": "aal"})` decorator on each agent's
`execute()` is what tags spans as belonging to AAL in OTel.

---

## §3 Common Patterns

### 3.1 Shared base class — **does not exist today**

There is no `cipher/agents/base.py` and no abstract `BaseAgent` /
`BaseSkill` class. Every implemented agent (`devnex/adapter.py`,
`devnex/skills/vcycle_s1n1/skill.py`) is a plain class that structurally
satisfies the `Skill` Protocol.

What every implemented agent does ad-hoc:

| Concern | How it is handled today | Cross-cutting candidate? |
|---|---|---|
| Tracing | `@traced(name=..., attributes={"layer": "aal"})` decorator on `execute`. | Yes — could move to a base class. |
| Skill id | Hard-coded `@property def skill_id(self) -> str: return "..."`. | Could be a class attribute on a base class. |
| Error → `TaskResult(FAILED)` | `try/except Exception as e: ... return TaskResult(status=FAILED, error_message=str(e))` — see `S1N1Skill.execute`. | Yes — duplicated wrapping logic. |
| Duration measurement | `t0 = time.perf_counter()` ... `duration_ms = (t0 - ...) * 1000`. | Yes. |

These four are the obvious candidates for a future `BaseSkill` class. AAL HLD
§7 Q2 tracks the decision.

### 3.2 Skill vs Adapter pattern (DevNex)

DevNex demonstrates a two-tier pattern that other complex agents may follow:

- **Adapter** (`cipher/agents/devnex/adapter.py`, `DevNexAdapter`): thin A2A
  surface — owns the `skill_id`, delegates to the actual skill.
- **Skill** (`cipher/agents/devnex/skills/vcycle_s1n1/skill.py`, `S1N1Skill`):
  domain logic — calls TRF router, writes to MinIO, returns the result.

The adapter pattern lets the same domain implementation be exposed under
multiple skill ids, and keeps domain code free of A2A vocabulary.

### 3.3 Subpackage layout

The recommended layout (inferred from `devnex/`) for a non-stub agent:

```
cipher/agents/<agent>/
├── __init__.py             # package marker, docstring
├── adapter.py              # A2A skill_id binding (optional)
├── skills/
│   ├── __init__.py
│   └── <skill_name>/
│       ├── __init__.py
│       └── skill.py        # Skill Protocol implementation
└── (additional internal modules)
```

Stub agents (`asil_reviewer/`, `planner/`, ...) currently contain only a
`README.md`, sometimes with an empty `__init__.py`.

---

## §4 Configuration

### 4.1 Layer-level configuration

There is **no layer-level configuration file** (no `cipher/agents/config.py`,
no `agents.yaml`). All configuration is either:

1. **Bootstrap-level** — `run_poc.py` decides which skills to register.
2. **Agent-internal** — each agent owns its own config. Example: DevNex
   Assistant ships `cipher/agents/devnex_assistant/configs/` for its own
   internal use; this is documented in its per-agent LLD.

### 4.2 Conventions

When a new agent needs configuration, the conventions in use today are:

- Place a `configs/` directory **inside the agent subpackage**, not at the
  AAL layer root.
- Use Pydantic models in the agent's own `models/` or `core/schemas.py` for
  typed access — mirroring the pattern in
  `cipher/agents/devnex_assistant/run_context.py` (`DevNexRunContext` is a
  Pydantic model per `CLAUDE.md` line 33).
- Tool/LLM endpoints (LLM Gateway URL, NATS URL, OPA URL) come from
  environment variables read at startup — agents do not hard-code endpoints.

### 4.3 Skill-id namespace

Skill ids are flat strings in a single global namespace owned by the
`SkillLoader` registry. Currently in use:

| skill_id | Owner |
|---|---|
| `vcycle_s1n1` | `cipher.agents.devnex.skills.vcycle_s1n1.skill.S1N1Skill` |
| `devnex_orchestrator` | `cipher.agents.devnex.adapter.DevNexAdapter` |

A naming convention (`<agent>_<stage>` or `<agent>.<skill>`) is not yet
codified — see §6.

---

## §5 Test Coverage

### 5.1 AAL-layer-shared tests

There are **no tests dedicated to layer-level AAL code**. The layer-level
modules (`cipher/agents/__init__.py`, `cipher/agents/README.md`) carry no
executable behaviour beyond the package marker, so no unit tests are
required at the layer level today.

### 5.2 Agent registration / dispatch tests

Tests that exercise the AAL-↔-ARE wiring live under `tests/`:

| Test file | What it exercises |
|---|---|
| `tests/unit/test_sprint2.py` (lines 97, 131) | Imports `S1N1Skill` and `DevNexAdapter`; validates the skill can be registered with the loader and dispatched. |
| `tests/e2e/test_poc_spine.py` (lines 37, 86) | End-to-end POC spine — registers the skill, submits a `TaskContract` via the A2A server, asserts a `TaskResult`. |

These are technically ARE/integration tests, but they are the only place
where AAL contract compliance is exercised today.

### 5.3 Per-agent tests

Per-agent tests live inside each agent subpackage (e.g.
`cipher/agents/devnex_assistant/tests/`) and are documented in each
agent's per-agent LLD, not here.

### 5.4 Test gaps at the layer level

- No test that asserts every agent subpackage has a registrable `Skill`.
- No test that detects skill-id collisions when more than one agent is
  registered.
- No test for the (currently absent) `BaseSkill` cross-cutting behaviour.

---

## §6 TODOs

1. **`BaseSkill` decision (HLD §7 Q2).** Either introduce
   `cipher/agents/base.py` with a `BaseSkill` ABC that bundles tracing,
   timing, and error-to-`TaskResult` mapping — or document the explicit
   decision to stay with the duck-typed Protocol.
2. **Self-registering subpackages.** Today each agent's `__init__.py` is
   inert. Consider an `entry_points` / decorator-based mechanism so that
   importing `cipher.agents.<agent>` is enough for the SkillLoader to see
   it, removing the manual `loader.register(...)` calls in `run_poc.py`.
3. **AgentCard publication.** Add a per-agent `AgentCard` instance
   (typically `cipher/agents/<agent>/agent_card.py`) and a layer-level
   collector that publishes all cards to the A2A `/agents` discovery
   endpoint.
4. **Skill-id namespace policy.** Adopt and document a naming convention
   (`<agent>.<skill>` is the natural choice given the dotted module path)
   and add a startup assertion that `loader.list_skills()` has no
   collisions.
5. **Stub promotion order.** Track which of the 8 stub agents
   (`asil_reviewer`, `compliance`, `memory_agent`, `planner`, `research`,
   `test_agent`, `tool_agent`, `traceability`) is next in scope. Each
   promotion should land with its own `docs/agents/<agent>.md` LLD and
   minimum a smoke test that registers its skill.
6. **Layer-level test directory.** Once `BaseSkill` lands (or once a
   self-registration mechanism is introduced), create
   `tests/unit/aal/` for layer-level invariants — distinct from
   per-agent tests.
