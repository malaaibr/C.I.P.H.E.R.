---
doc_id: AGENT-ASILREV-001
agent_id: AGT-003
agent_name: asil_reviewer
status: STUB
role: ISO 26262 ASIL gate enforcement agent (planned)
layer: AAL
trust_tier: T2 (gated)
date: 2026-05-17
---

# asil_reviewer — ASIL Review Agent (Planned)

> **Honesty banner.** This agent is **not implemented**. The directory
> `cipher/agents/asil_reviewer/` currently contains only a 3-line README
> describing intent. There is no Python module, no `__init__.py`, no
> orchestrator wiring, no A2A AgentCard, and no test class. Nothing in
> this document describes runtime behavior that exists today.

## 1. Role and Capabilities (Planned)

Per `CIPHER_HLD.md` Appendix A (AGT-003) and `CIPHER_archi.md` §4.1, the
ASIL Review Agent is the **T2 gated verification critic** for ISO 26262
artifacts. Its planned responsibilities are:

- Execute **UC 3.1 — ASIL Review** on a target source/LLD artifact and
  produce both the machine-readable report and the human-readable summary:
  - `asil_review_<file>.json` — conforms to the `AsilReviewReport`
    dataclass (`ASDLC.md` §4.1, UC 3.1 row).
  - `asil_review_<file>.md` — the Safety Engineer–facing rendering of
    the same report.
- Drive the **PHASE 3 ASIL Gate Review** state transition described in
  `ASDLC.md` §3:
  - ASIL-D → raise `SemanticConflictError` and force **HARD_BLOCK** with
    mandatory G5 Safety Engineer sign-off (`ASDLC.md` §6 row "D").
  - ASIL-C → emit `HOLD`, merge blocked pending senior + safety review.
  - ASIL-B → emit `HOLD` advisory, peer review required.
  - ASIL-A / QM → log `WARN` / pass-through; no merge block.
- Write a `review_node` into the knowledge graph (the only mutation it
  is allowed — see §6 below).

## 2. Current State — STUB

Files actually present in `cipher/agents/asil_reviewer/`:

| File | Size | Content |
|---|---|---|
| `README.md` | 101 B | 3 lines: title + "Phase 2 gated-review stub for ISO 26262 and ASIL-oriented artifact review." |

Notably **absent**:

- `__init__.py` (the layer roll-up in `AAL_LLD.md` §3 explicitly notes
  this directory is a README-only stub with **no** `__init__.py`).
- Any Python module, prompt template, rubric YAML, or test file.
- Any registration in the A2A registry or orchestrator skill map.

## 3. Reference to ASDLC

The agent's contract is fully specified in `docs/ASDLC.md` even though
the code is not yet written:

- **§3 PHASE 3 — ASIL Gate Review** defines the four-branch gate logic
  (D / C / B / A) this agent must implement.
- **§4.1 Per-UC Mandatory Artifacts** — UC 3.1 row specifies the dual
  `asil_review_<file>.json` + `.md` output and names `AsilReviewReport`
  as the schema.
- **§6 ASIL-Aligned Review Checkpoints** is the source of the
  `HARD_BLOCK` semantics for ASIL-D and `HOLD` for B/C.
- **§3 Gate G3** — "ASIL gate decision documented in
  `asil_gate_decision.json`" — is the audit artifact this agent must
  produce before the gate can close.

## 4. Planned V-cycle Node Mapping

| Aspect | Mapping |
|---|---|
| Primary UC | UC 3.1 (ASIL Review) |
| Phase Gate contributed | G3 (ASIL Gate decision); G5 input on ASIL-D |
| Trust tier | T2 (gated) — `CIPHER_archi.md` §4.1 |
| AgentCard port (planned) | `:7003` — `CIPHER_HLD.md` Appendix A |

## 5. Inputs and Outputs (Planned)

**Inputs**

- Target artifact path (source file, LLD section, or trace row).
- Claimed ASIL level (`QM | A | B | C | D`).
- Optional: prior `asil_review_<file>.json` for incremental re-review.

**Outputs**

- `asil_review_<file>.json` — instance of `AsilReviewReport` (dataclass
  contract per `ASDLC.md` §4.1; the dataclass definition itself is
  pending implementation).
- `asil_review_<file>.md` — Safety Engineer–facing rendering.
- On ASIL-D conflict: a `SemanticConflictError` payload contributing to
  Gate G5 evidence.
- Graph mutation: a single `review_node` write (see §6).

## 6. Dependencies (Planned)

- **TRF — LLM Gateway** for rubric-based critique calls (`CIPHER_HLD.md`
  §9.3 routes "review" task class through `gca-standard`).
- **MKF — Hybrid RAG** for MISRA-C / ISO 26262-6 rule retrieval against
  the rubric pack at `cipher/governance/rubrics/`.
- **GCL — Audit Journal** for the immutable Gate G3 / G5 decision
  record and the agent_scopes enforcement.
- **Agent scope (locked-down)** per `CIPHER_HLD.md` §9.2 /
  `CIPHER_archi.md` §7.2:
  - `read: [fs:project/**, kg:read, doors:read]`
  - `write: [kg:write:review_node]`
  - `deny: [fs:write, git:write, doors:write, vectorcast:write]`

## 7. Open Items

- **Not yet implemented — Sprint TBD.** `WBS-0001-poc-spine.md` scopes
  the PoC spine around DevNex + Garvis + orchestrator; it does **not**
  schedule AGT-003. A future WBS entry must own:
  - Creating `__init__.py` and the agent module skeleton.
  - Authoring the `AsilReviewReport` dataclass in `cipher.core.schemas`.
  - Wiring an A2A AgentCard at `:7003`.
  - Defining the rubric YAMLs (`lld_review.yaml`, `code_review.yaml`,
    `test_coverage.yaml`) referenced in `CIPHER_HLD.md` §9.1.
  - Implementing the four-branch gate logic and the `SemanticConflictError`
    path for ASIL-D.
  - Adding the pytest class `test_asil_reviewer.py` per `ASDLC.md` §2.3
    ("no module is done until its test class passes 100%").
