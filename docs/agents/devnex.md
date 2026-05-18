---
doc_id: AGENT-DEVNEXADAPTER-001
title: DevNex A2A Adapter
status: IMPLEMENTED
layer: AAL
role: A2A adapter bridging devnex_assistant into ARE SkillLoader
owner: CIPHER Core
related:
  - docs/agents/devnex_assistant.md
  - docs/layers/AAL.md
  - docs/layers/ARE.md
source_root: cipher/agents/devnex/
---

# DevNex A2A Adapter

> NOTE: This document describes the **thin A2A adapter** under
> `cipher/agents/devnex/`. It is **not** the full DevNex V-cycle agent.
> For the underlying 13-node LangGraph orchestrator (panels, workers,
> backbone), see [`docs/agents/devnex_assistant.md`](./devnex_assistant.md).

## §1 Role & Capabilities

`DevNexAdapter` is a small bridge that exposes the DevNex agent's
V-cycle capabilities through CIPHER's A2A (Agent-to-Agent) surface.

Its single responsibility:

1. Accept an inbound A2A `TaskContract` from the ARE `SkillLoader`.
2. Dispatch it to the appropriate DevNex *skill* implementation
   (currently `S1N1Skill`).
3. Wrap the skill's response in a `TaskResult` and return it to ARE.

The adapter performs no orchestration of its own — it is the
contract-translation seam between the A2A protocol layer and the
internal DevNex execution graph. All real work (LLM routing, artifact
storage, V-cycle node logic) happens inside the skill or further down
in `devnex_assistant`.

OpenTelemetry tracing is applied at both adapter and skill level via
the `@traced` decorator (`layer=aal`).

## §2 Skills Exposed

The adapter package currently ships one skill, registered with the ARE
`SkillLoader` at process start:

| Skill ID     | Class       | TaskClass | Target V-cycle Stage | Source |
|--------------|-------------|-----------|----------------------|--------|
| `vcycle_s1n1` | `S1N1Skill` | `CODE_GEN` | S1N1 — LLD Generation | `cipher/agents/devnex/skills/vcycle_s1n1/skill.py` |

The adapter itself advertises `skill_id = "devnex_orchestrator"` (see
`adapter.py:21`) but at present `execute()` always delegates to
`S1N1Skill`. Additional V-cycle stages (S1N2…S4N3) are not yet exposed
as A2A skills; they live inside `devnex_assistant`'s LangGraph.

## §3 Inputs / Outputs

**Input** — `TaskContract` (from `cipher.core.schemas.task_contract`):

- `task_id` — used to key MinIO artifacts.
- `prompt` — passed as the HLD prompt to the LLM router.
- `context` — forwarded to `TaskClassRouter.route()`.

**Output** — `TaskResult`:

- `status` — `COMPLETED` or `FAILED`.
- `output.lld_content` — first 500 chars of generated LLD CSV.
- `output.artifact_key` — `lld/{task_id}.csv`.
- `output.backend` — backend ID returned by the LLM router.
- `artifact_refs` — `[f"minio://cipher-artifacts/{artifact_key}"]`.
- `duration_ms` — wall-clock execution time.
- `error_message` — populated on failure.

The skill calls `TaskClassRouter.route(prompt, TaskClass.CODE_GEN,
context)` (skill.py:30-33), uploads the result to MinIO under
`cipher-artifacts/lld/<task_id>.csv` (skill.py:39-45), and tolerates a
missing MinIO instance silently for unit-test contexts.

## §4 Registration

The adapter's skill is registered in `run_poc.py` at startup, before
any servers come online:

- `run_poc.py:18` — `from cipher.are.skill_loader.loader import get_skill_loader`
- `run_poc.py:19` — `from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill`
- `run_poc.py:43` — `loader = get_skill_loader()`
- `run_poc.py:44` — `loader.register(S1N1Skill())`
- `run_poc.py:45` — `print(f"[CIPHER] Registered skills: {loader.list_skills()}")`

`SkillLoader.register()` (`cipher/are/skill_loader/loader.py:25`) keys
the skill by its `skill_id` property (`"vcycle_s1n1"`). The A2A server
(`cipher/are/a2a_server/server.py`, started on port 8100) then dispatches
inbound A2A traffic to the registered skill.

Note: `DevNexAdapter` itself is **not** registered with the
SkillLoader in `run_poc.py` — only `S1N1Skill` is. The adapter class
exists for future use when multi-skill dispatch is needed.

## §5 Relationship to `devnex_assistant`

This package and `cipher/agents/devnex_assistant/` are distinct:

| Concern | `cipher/agents/devnex/` (this doc) | `cipher/agents/devnex_assistant/` |
|---------|------------------------------------|-----------------------------------|
| Purpose | A2A protocol adapter / skill shim | Full V-cycle agent (orchestrator, 13 nodes, GUI panels, workers) |
| Surface | `TaskContract → TaskResult` | LangGraph + PyQt6 workspace |
| Files | ~5 (`adapter.py`, `skills/vcycle_s1n1/skill.py`, three `__init__.py`) | Multi-package: `core/`, `interfaces/gui/`, `workflows/`, etc. |
| Owner of business logic | No — delegates to router/MinIO | Yes — LLM calls, human-in-the-loop gates, panel rendering |

For the underlying V-cycle agent, see
[`docs/agents/devnex_assistant.md`](./devnex_assistant.md).

The current `S1N1Skill` does not yet call into
`devnex_assistant.core.orchestrator.DevNexOrchestrator`; it talks
directly to the LLM Gateway. Wiring the skill to the full 13-node
orchestrator is tracked in **Open Items** below.

## §6 Dependencies

- **ARE / SkillLoader** — `cipher.are.skill_loader.loader.get_skill_loader` —
  registry the skill registers into; consumed by the A2A server.
- **Core / TaskContract** — `cipher.core.schemas.task_contract.TaskContract`,
  `TaskResult`, `TaskStatus`, `TaskClass` — the protocol DTOs.
- **Core / OTel** — `cipher.core.otel.traced` — tracing decorator.
- **TRF / LLM Gateway** — `cipher.trf.mcp_servers.llm_gateway.router.get_router` —
  routes the CODE_GEN prompt to the configured backend.
- **Core / MinIO adapter** — `cipher.core.adapters.minio_client.MinioStore` —
  optional artifact persistence (`cipher-artifacts` bucket).
- **devnex_assistant** — *not currently a runtime dependency*; intended
  integration point (see §7).

## §7 Open Items

1. **Bridge to `DevNexOrchestrator`** — `S1N1Skill.execute()` should
   invoke the V-cycle node sequence inside
   `cipher/agents/devnex_assistant/core/orchestrator.py` rather than
   calling the LLM Gateway directly. The S1N1 stage there contains the
   real HLD-to-LLD logic.
2. **Expose remaining V-cycle stages** — only `vcycle_s1n1` is
   registered. Stages S1N2 through S4N3 need their own skill classes
   and SkillLoader registrations in `run_poc.py`.
3. **Use the adapter** — `DevNexAdapter` (`adapter.py`) is currently
   dead code from a registration standpoint; either register it or
   remove it.
4. **Surface `TaskStatus` import** — `adapter.py:6` imports
   `TaskStatus` without using it (lint signal).
5. **MinIO failure visibility** — skill silently swallows MinIO upload
   failures (skill.py:44-45); consider logging at WARNING level.

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Marked superseded — merged into devnex_assistant agent. |
