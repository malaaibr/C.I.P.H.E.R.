---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# AAL — High-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | HLD-AAL-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Layer | AAL — Agent Application Layer |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dir | `cipher/agents/` |
| Authoritative sources | `cipher/agents/README.md`, `cipher/agents/__init__.py`, `docs/CIPHER_HLD.md` §3.7 / §6.2, `docs/CIPHER_LLD.md` §9, `run_poc.py` |

---

## §1 Purpose & Scope

The Agent Application Layer (AAL) is the topmost CIPHER layer — Layer 7 in the
AUTOSAR-derived 7-layer model (see `docs/CIPHER_HLD.md` line 128: *"Application
Layer → Application / Agent Layer (AAL): Domain-specialized agents that
implement actual SDLC work"*).

AAL **hosts agent implementations**. Each agent is an independent plugin that is
discovered and loaded by the layer immediately below it — the **Agent Runtime
Environment (ARE)** — via the `SkillLoader` registry
(`cipher/are/skill_loader/loader.py`). Above the ARE, the architecture style
changes from layered to component/agent style (`docs/CIPHER_HLD.md` line 518):
agents do not call each other through layered APIs; they exchange typed A2A
task contracts.

**In scope (this doc).**
- The role of `cipher/agents/` as the plugin host for the platform.
- The contract every agent must satisfy to be loadable by the ARE SkillLoader.
- Inventory of the 10 subdirectories currently scaffolded under `cipher/agents/`
  with their implementation depth (file count → status).
- Layer-level dependencies on ARE, TRF, MKF, PKL.

**Out of scope.**
- Per-agent design. Each agent's HLD/LLD lives under `docs/agents/<agent>.md`
  and is authored independently of this document.
- ARE itself (skill loader internals, A2A server) — see ARE layer docs.
- DevNex Assistant's internal V-cycle pipeline — covered in
  `docs/agents/devnex_assistant.md` and `docs/CIPHER_LLD.md` §12.

---

## §2 Position in the 7-Layer Architecture

```
+------------------------------------------------------------------+
|                        GUI Layer (PyQt6)                         |
+------------------------------------------------------------------+
                                |
+------------------------------------------------------------------+
|       AAL — Agent Application Layer   (this layer)               |
|       cipher/agents/  →  DevNex, S1N1, future stubs              |
+------------------------------------------------------------------+
                                |
+------------------------------------------------------------------+
|       ARE — Agent Runtime Environment                            |
|       SkillLoader registry  |  A2A Server (:8100)                |
+------------------------------------------------------------------+
                                |
+--------+--------+--------+--------+----------+
|  TRF   |  MKF   |  PKL   |  GCL   |   DRS    |
+--------+--------+--------+--------+----------+
```

AAL sits at the top of the stack and depends only on the layer below it
(ARE) for runtime hosting, and laterally on TRF (LLM access), MKF (memory/RAG),
and PKL (event bus) for the services individual agents need to do their work.
GCL cross-cuts the layer — every agent action is subject to policy evaluation
(`docs/CIPHER_HLD.md` line 504).

---

## §3 External Interfaces

### 3.1 The Agent Contract

Every agent in `cipher/agents/` exposes a skill that satisfies the `Skill`
Protocol defined in `cipher/are/skill_loader/loader.py`:

```python
class Skill(Protocol):
    @property
    def skill_id(self) -> str: ...
    async def execute(self, task: TaskContract) -> TaskResult: ...
```

- **Input**: `TaskContract` (typed Pydantic model from
  `cipher/core/schemas/task_contract.py`).
- **Output**: `TaskResult` (typed Pydantic model, same module).
- **Discovery**: each agent's skill instance is registered with the ARE
  `SkillLoader` at process startup. The current POC wires this in
  `run_poc.py` lines 18–45 (`loader.register(S1N1Skill())`).

### 3.2 Agent Identity (AgentCard)

Each agent advertises itself via an `AgentCard` (see
`cipher/core/schemas/agent_card.py`). The AgentCard carries `agent_id`, `name`,
`url`, and a list of `SkillDescriptor` entries. The card is the A2A discovery
artefact — peer agents and the A2A server use it to resolve which agent can
handle a given task class or V-cycle stage.

> The AgentCard schema exists today; auto-publishing cards from every agent
> subpackage is a roadmap item (see §7).

---

## §4 Agent Inventory

Status convention used below:
- **Implemented** — production code present, registered with the SkillLoader.
- **Partial** — package layout and one or more skeleton modules present, but
  not yet wired into the platform.
- **Stub** — README only (or README + empty `__init__.py`); no executable code.

| Agent | Role | Depth | Status | Per-agent doc |
|---|---|---|---|---|
| `devnex_assistant/` | AGT-001 — V-cycle verification engine (13-node DevNex orchestrator) | 3034 files | Implemented | [devnex_assistant](../agents/devnex_assistant.md) |
| `devnex/` | A2A adapter + S1N1 LLD-generation skill bridging the ARE to DevNex | 5 files (`adapter.py`, `skills/vcycle_s1n1/`) | Implemented | [devnex](../agents/devnex.md) |
| `compliance/` | Local-MVP compliance gate / static-analysis boundary | 2 files (README + empty `__init__.py`) | Stub | [compliance](../agents/compliance.md) |
| `memory_agent/` | Memory ownership facade for the MVP | 2 files | Stub | [memory_agent](../agents/memory_agent.md) |
| `tool_agent/` | Tool-scope enforcement facade | 2 files | Stub | [tool_agent](../agents/tool_agent.md) |
| `asil_reviewer/` | Automotive ASIL safety review (later phase) | 1 file (README only) | Stub | [asil_reviewer](../agents/asil_reviewer.md) |
| `planner/` | Planning & orchestration agent (later phase) | 1 file | Stub | [planner](../agents/planner.md) |
| `research/` | Research & analysis agent (later phase) | 1 file | Stub | [research](../agents/research.md) |
| `test_agent/` | Test generation agent (later phase) | 1 file | Stub | [test_agent](../agents/test_agent.md) |
| `traceability/` | Requirements traceability (later phase) | 1 file | Stub | [traceability](../agents/traceability.md) |

**Roll-up.** 2 Implemented / 0 Partial / 8 Stub.

> File counts are non-test source files under each subdir. The
> `devnex_assistant/` figure is inflated by its bundled GUI assets, build
> artefacts, and `egg-info`; see its per-agent doc for the actual source
> breakdown.

---

## §5 Dependencies

Layer dependencies, taken from the Layer Interaction Matrix in
`docs/CIPHER_HLD.md` line 274 (*"AAL — — X — X X —"*: AAL depends on MKF, GCL,
and ARE):

| Depends on | Why | Used by |
|---|---|---|
| **ARE** | Agents are hosted as skills inside the ARE `SkillLoader` and reached via the A2A server. | All agents — every `skill_id` is resolved through `cipher.are.skill_loader.loader`. |
| **TRF** | LLM access via the gateway / `TaskClassRouter`. | `S1N1Skill` (`cipher.trf.mcp_servers.llm_gateway.router.get_router`), DevNex orchestrator nodes. |
| **MKF** | Retrieval (hybrid RAG) and four-tier memory services. | DevNex assistant for context recall and artefact lookup. |
| **PKL** | Event bus (NATS) for agent-to-agent notifications and LangGraph workflow checkpointing. | DevNex orchestrator state transitions. |
| **GCL** | Cross-cutting policy gate — every agent action passes through OPA + audit journal. | All agents (enforced by ARE/GCL, not by the agent itself). |
| **Core** | Shared Pydantic schemas (`TaskContract`, `TaskResult`, `AgentCard`) and OTel tracing decorator (`@traced`). | All agents. |

AAL has **no horizontal coupling** between its own subpackages — `devnex/`
does not import from `planner/`, etc. Inter-agent communication goes through
A2A task contracts, not Python imports.

---

## §6 Quality Attributes

| Attribute | How AAL achieves it |
|---|---|
| **Plugin isolation** | Each agent lives in its own subpackage. Adding a new agent requires no edits to other agents — only a `loader.register(...)` call in the bootstrap (currently `run_poc.py`). |
| **Contract compliance** | All skills must implement the `Skill` Protocol (`skill_id` + `async execute(task) -> TaskResult`). Non-compliant agents fail at `loader.register()` static-typing time. |
| **Observability** | Every skill execution is wrapped with `@traced(name=..., attributes={"layer": "aal"})` — see `cipher/agents/devnex/adapter.py` and `.../vcycle_s1n1/skill.py`. |
| **Deployment-independence** | Agents call TRF, MKF, and PKL through their layer APIs only — never reach into DRS containers directly. This is what allows the same agent code to run on Compose today and Nomad/K8s later. |
| **Replaceability** | A stub agent (e.g. `memory_agent/`) can be promoted to a real implementation without touching ARE, TRF, or the GUI — only its own subpackage and the bootstrap registration line change. |

---

## §7 Open Questions

1. **AgentCard auto-publishing.** Each agent currently exposes `skill_id` only.
   How and where will every agent's full `AgentCard` (with `SkillDescriptor`
   lists, V-cycle stages, task classes) be assembled and served from the A2A
   `/agents` endpoint?
2. **Shared base class.** There is no `BaseAgent` / `BaseSkill` abstract class
   today — only a `Skill` Protocol in ARE. Is duck typing sufficient long-term,
   or should AAL ship a common base that pre-wires tracing, GCL policy checks,
   and error → `TaskResult(status=FAILED)` mapping? (See AAL LLD §3.)
3. **Stub promotion order.** The 8 stub agents are tracked here as one bucket.
   Which subset is in scope for Phase 2, and what is the dependency order
   (e.g. `memory_agent` likely precedes `research`)?
4. **DevNex split.** `devnex/` (A2A adapter + S1N1 skill) and
   `devnex_assistant/` (full V-cycle engine) are two separate subpackages of
   the same agent. Should they be unified, or does the adapter/engine split
   remain the long-term shape?
5. **Per-agent doc index.** The links in §4 point at
   `docs/agents/<agent>.md` files that are being authored in parallel.
   A consolidated index page may be needed once those land.
