---
doc_id: AGENT-TRACE-001
agent_name: traceability
status: STUB
role: End-to-end traceability matrix agent (planned)
layer: AAL (Application / Agent Layer)
implementation_path: cipher/agents/traceability/
owner_uc: UC 1.4, UC 4.1
last_reviewed: 2026-05-17
---

# Traceability Agent

## 1. Role & Capabilities (Planned)

The Traceability Agent is planned as the **dedicated owner of end-to-end SDLC
traceability** within CIPHER. Its responsibilities, as derived from the HLD/archi
roll-up and ASDLC contracts, are:

- **UC 1.4 owner**: Generate and maintain the canonical `Full_Traceability_Matrix.csv`
  (S9N1 stage output) joining HLD ↔ LLD ↔ Code ↔ Test artifacts.
- **Symbol resolution**: Resolve CODE_FUNCTION → FILE/LINE entries against the
  firmware `.map` file and source tree, producing accurate code anchors.
- **Cross-stage join**: Consume the upstream per-stage trace CSVs (S3N1, S4N1,
  S5N1, S8N1) and merge them into the unified S9N1 matrix.
- **Impact analysis** (planned): Answer "what tests are at risk if I change
  function X?" via graph traversal of the `IMPLEMENTS → VERIFIES` chain
  (`CIPHER_archi.md` §"Bidirectional traceability").
- **UC 4.1 grounding**: Serve as the trace-aware retrieval surface for
  Q&A queries that must be grounded in the traceability matrix.
- **Tier**: T1 (advisory) per `CIPHER_archi.md` — `AGT-010` in the agent
  registry, "Graph algorithms over Memgraph/Neo4j".

## 2. Current State

**STATUS: STUB.** The agent directory is README-only.

Actual files under `cipher/agents/traceability/`:

| File | Purpose |
|------|---------|
| `README.md` | One-line stub: "Phase 2 stub for maintaining bidirectional requirement-design-code-test links and impact analysis." |

No `__init__.py`, no skill module, no AgentCard, no SkillLoader entry.

**Where trace work lives today:** The traceability functionality is currently
implemented **inside the primary DevNex agent** at
`cipher/agents/devnex_assistant/core/trace_loader.py`. That module owns the
`_CSV_MAP` table covering the canonical S3N1/S4N1/S5N1/S8N1/S9N1 filenames
(per ASDLC §4.2) and assembles trace artifacts as part of the V-cycle pipeline.
Extracting this responsibility into the standalone `traceability` agent is a
future refactor.

## 3. Reference to ASDLC

This stub maps to two ASDLC anchors:

- **§4.1 — Per-UC Mandatory Artifacts**: UC 1.4 requires
  `Full_Traceability_Matrix.csv` with schema
  `HLD_ID, LLD_ID, CODE_FUNCTION, FILE, LINE`. This agent owns that contract.
- **§3 — PHASE 4: Integration & Traceability**: Gate G4 ("full traceability
  matrix reviewed") and the post-merge QA-PROC verification that the
  HLD→LLD→Code→Test chain is unbroken are the operational checkpoints this
  agent must satisfy.
- **§4.2 — Filename Alignment (F-001 fix)**: The canonical S3N1/S4N1/S5N1/S8N1/S9N1
  filenames are the inputs/output of this agent.

## 4. Planned UC Mapping

| UC | Description | Role of Traceability Agent |
|----|-------------|----------------------------|
| **UC 1.4** | Full traceability matrix generation | **Owner** — produces `Full_Traceability_Matrix.csv` |
| **UC 4.1** | Q&A grounded in trace data | **Provider** — exposes trace-matrix retrieval for grounded answers |
| UC 4.4 | Post-merge no-regression check | **Contributor** — supplies trace deltas for the integration check |

## 5. Inputs / Outputs (Planned)

**Inputs (per-stage CSVs produced by the V-cycle pipeline):**

| Stage | Filename | Source |
|-------|----------|--------|
| S3N1 | `LLD_Code_Trace_Matrix.csv` | LLD ↔ code link stage |
| S4N1 | `HLD_LLD_Trace_Matrix.csv` | HLD ↔ LLD decomposition stage |
| S5N1 | `Full_Downstream_Trace.csv` | Downstream consolidation |
| S8N1 | `UTD_LLD_Links.json` | Test ↔ LLD link stage |
| (aux) | `firmware.map` | Symbol → address/file resolution |

**Output:**

- `Full_Traceability_Matrix.csv` (S9N1) — schema:
  `HLD_ID, LLD_ID, CODE_FUNCTION, FILE, LINE` (ASDLC §4.1).
- Persisted to MinIO and registered as an ArtifactRelation graph entry in MKF.

## 6. Dependencies (Planned)

- **devnex_assistant** — produces the per-stage trace artifacts (S3N1, S4N1,
  S5N1, S8N1) that feed S9N1. Until the refactor, the trace agent will likely
  call into or replace `devnex_assistant.core.trace_loader`.
- **MKF** — graph backend (Memgraph/Neo4j) for ArtifactRelation storage and
  Cypher-based bidirectional traversal (per `CIPHER_archi.md` §"Knowledge Graph").
- **GCL** — audit trail for matrix generation events and Gate G4 decisions.
- **TRF/LLM Gateway** — only if LLM-assisted reconciliation is needed for
  ambiguous symbol resolution; baseline path is deterministic.

## 7. Open Items

- **Not implemented.** No code, no AgentCard, no SkillLoader registration.
- Trace functionality is **embedded in `devnex_assistant`** today
  (`core/trace_loader.py`). Extraction into this standalone agent is a planned
  refactor with no scheduled date.
- No skill contract or A2A endpoint defined yet.
- Impact-analysis Cypher queries (the "what breaks if I change X?" workflow)
  exist conceptually in `CIPHER_archi.md` but have no skill implementation here.
- Decision pending: keep trace assembly inside `devnex_assistant` (status quo)
  or split into this dedicated agent (current planned direction).

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
