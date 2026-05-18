---
doc-id: AGENT-PLAN-001
agent: planner
layer: AAL
status: STUB
role: Sprint planning / WBS decomposition agent (planned)
implementation_path: cipher/agents/planner/
agent_id: AGT-002
planned_port: 7002
last-updated: 2026-05-17
---

# Planner Agent (AGENT-PLAN-001)

> **Status: STUB.** The `cipher/agents/planner/` directory is a Phase 2 advisory-agent
> scaffold. Only a `README.md` exists; there is no implementation, no A2A server,
> no skills, and no orchestrator wiring. This document captures the *planned* role
> per the HLD agent registry and the ASDLC Tech Lead specification.

---

## 1. Role & Capabilities (Planned)

The Planner Agent (`AGT-002`) is intended to fulfil the **CIPHER ARCHITECT / Tech
Lead** role defined in `ASDLC.md §2.1`. Planned responsibilities:

- Read user/CI requests and decompose them into UC-mapped sprint plans.
- Produce three artifact classes:
  - **UC catalog** entries (interactive artifact, ASPICE SWE.1 coverage).
  - **ADR documents** for architectural decisions (Wrap / Refactor / Rewrite).
  - **Sprint WBS** files (`docs/wbs/WBS-NNNN-*.md`).
- Drive **Gate G0** — sprint plan approval before any DEV (DevNex) work begins
  (ASDLC §3, Phase 0).
- Serve as an *advisory* agent in the orchestrator graph: emits plans/WBS for
  human + QA-PROC review; does **not** mutate code or runtime state.

---

## 2. Current State

Implementation directory `cipher/agents/planner/` contains:

| File | Purpose |
|------|---------|
| `README.md` | One-line note: *"Phase 2 advisory-agent stub. Orchestrator contracts will eventually route through it, but it is not part of the mutating Phase 1 runtime."* |

There is **no** `__init__.py`, no `agent.py`, no `skills/`, no `card.json`, and
no FastAPI/A2A server. The agent is **not** registered with the running
`SkillLoader` or `Orchestrator` in `run_poc.py`.

Per HLD Appendix A (line 1445), the planned A2A port is `:7002`.

---

## 3. Reference to ASDLC

The planner's role is fully described in:

- **`docs/ASDLC.md` §2.1 — Tech Lead (CIPHER ARCHITECT)**: *"Responsible for the
  platform UC catalog, sprint planning, and architectural decisions. Produces:
  UC catalog (interactive artifact), ADR documents, sprint WBS. Gate authority:
  approves sprint plan before DEV work begins."*
- **`docs/ASDLC.md` §3 — Phase 0**: Tech Lead produces UC catalog + sprint plan,
  then Gate G0 must pass before DevNex (AGT-001) can start Sprint 0.
- **`docs/CIPHER_HLD.md` §3.1 (line 101)**: *Intent and planning — Convert user
  requests or CI/CD events into structured tasks, plans, and sub-plans.*

When implemented, the Planner Agent is the executable embodiment of these
responsibilities.

---

## 4. Planned UC Mapping

The Planner is expected to *read* the platform UC catalog (per the ASDLC
PROC-001 process — "UC catalog read-through" is the entry activity for Phase 0)
and *produce* the following artifacts:

| Output | Format | Consumer |
|---|---|---|
| UC catalog deltas | Markdown table rows + JSON | QA-PROC for SWE.1 review |
| ADR documents | `docs/adrs/ADR-NNNN-*.md` | Reviewer agent + human Tech Lead |
| Sprint WBS | `docs/wbs/WBS-NNNN-*.md` | DevNex (AGT-001), QA-PROC |
| Gate G0 packet | structured JSON | Orchestrator + GCL audit |

The Planner does **not** implement UCs; it allocates them.

---

## 5. Inputs / Outputs (Planned)

**Inputs**
- High-level user request (TaskContract from orchestrator).
- Current UC catalog state.
- Backlog of open ADRs and pending WBS items.

**Outputs**
- TaskContract responses carrying `plan_artifact` blobs (ADR, WBS, UC deltas).
- A2A events on `:7002` consumed by the Orchestrator and DevNex.

---

## 6. Dependencies (Planned)

- **TRF — LLM Gateway (:8200)**: planning prompts routed via `TaskClassRouter`,
  likely the `planning` / `architecture` task class (slower, larger model).
- **GCL — Policy + audit**: Gate G0 approval recorded via the audit journal;
  ADR sign-off requires OPA policy check before DEV may proceed.
- **MKF**: read-only access to existing UC catalog and ADRs via the hybrid RAG
  retriever for context grounding.
- **ARE**: registers an `AgentCard` and exposes A2A on `:7002`.

---

## 7. Open Items

- **Not yet implemented.** Only a README stub exists.
- No `AgentCard`, no skill modules, no orchestrator route.
- UC catalog interactive artifact format is not yet specified.
- ADR template directory `docs/adrs/` does not yet exist.
- Gate G0 acceptance criteria are described in ASDLC §3 but have no executable
  check in the GCL policy bundle.
- Decision pending: should the Planner reuse the DevNex LangGraph runtime or
  run as a lighter advisory-only A2A service?

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
