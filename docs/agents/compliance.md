---
doc_id: AGENT-COMPL-001
agent_id: AGT-004
name: Compliance Agent
status: STUB
role: ASPICE / regulatory compliance audit agent (planned)
layer: AAL
port: 7004
owner: CIPHER QA-PROC
governs: ASDLC §4 Artifact Contracts, ASDLC §7 MISRA-C:2012 Mandatory Rules
---

# Compliance Agent — Doc AGENT-COMPL-001

> **STATUS: STUB.** This document describes the *planned* behaviour of the
> Compliance Agent. The on-disk implementation is currently a scaffold
> (`README.md` + empty `__init__.py`). No executable logic, skills, or A2A
> endpoint exist yet.

---

## 1. Role & Capabilities (Planned)

The Compliance Agent is CIPHER's **deterministic regulatory audit gate**. Where
the ASIL Review Agent applies LLM-based rubric judgement, Compliance is the
reproducible, evidence-grade checker whose findings must hold up in an ISO
26262 Part 8 audit and an ASPICE Level-2/3 assessment.

Planned capability surface (per `CIPHER_HLD.md` §6.5 and `CIPHER_archi.md`
§3.5):

- **ASPICE SWE.x checklist enforcement** — verify BP/GP coverage for SWE.1
  through SWE.6 work products (requirements, architecture, detailed design,
  unit construction, unit verification, integration).
- **MISRA-C rule audit** — wrap PC-lint Plus / cppcheck / Polyspace through
  TRF, parse rule violations, and write `ArtifactRelation(VIOLATES)` edges
  into the MKF knowledge graph. Rule set is governed by **ASDLC §7 MISRA-C:2012
  Mandatory Rules** in the local MVP and will extend to MISRA-C:2025 in Phase 2.
- **ISO 26262 work-product completeness checks** — confirm every safety-relevant
  artifact has the parent requirement, ASIL classification, and verification
  evidence the standard demands before status can advance to `APPROVED`.
- **AUTOSAR coding-guideline checks** — secondary checker class once MVP MISRA
  pipeline is stable.

---

## 2. Current State

**STUB.** Inventory of `CIPHER_Repo/cipher/agents/compliance/`:

```
compliance/
├── README.md        # 11-line stub describing planned MVP responsibility
└── __init__.py      # docstring only: "Compliance agent scaffold for the local MVP."
```

No skills, no orchestrator, no A2A card, no rubrics directory, no tool
wrappers. The directory is reserved namespace only.

---

## 3. Reference to ASDLC

`docs/ASDLC.md` is the **normative source** for the rules this agent must one
day audit. Two sections are load-bearing for Compliance:

- **ASDLC §4 — Artifact Contracts.** Defines the per-UC mandatory artifacts
  (JSON schema + Markdown sections) and the filename-alignment fix (F-001)
  that the Compliance Agent must verify before an artifact bundle can pass a
  phase gate.
- **ASDLC §7 — MISRA-C:2012 Mandatory Rules.** The deterministic rule table
  this agent must enforce on every C source artifact. A Mandatory-rule
  violation is a hard `REJECT`; Required-rule violations are gated findings.

The agent does not author rules — it executes them. Rule authorship belongs to
CIPHER QA-PROC (ASDLC §2.4).

---

## 4. Planned UC Mapping

Per ASDLC §2.4, the Compliance Agent is the runtime embodiment of the
**QA-PROC (QA Process Engineer)** role. Expected UC touchpoints:

- **UC artifact-contract gate** — verifies JSON schema / Markdown section
  contracts at every phase boundary (ASDLC §4.1, §4.2).
- **UC post-merge hook** — invoked by CI/CD per ASDLC §5.1 to re-audit merged
  artifacts and write violation edges into MKF.
- **UC HLD→LLD→Code→Test traceability** — confirms the chain is unbroken
  (ASDLC §2.4 bullet 4) before final phase sign-off.

---

## 5. Inputs / Outputs (Planned)

**Input.** An *artifact bundle* — a set of MKF graph URIs covering the source
file(s) under audit plus any companion artifacts (requirements, LLD, test
specs) required by the relevant SWE.x or ASIL checklist.

**Output.**

- A structured **`ComplianceReport` JSON** — violation counts by severity, by
  rule category (MISRA / AUTOSAR / ASPICE / ISO-26262), and per-artifact
  pass/fail verdict. Schema lives alongside other A2A skill schemas once
  authored.
- **Audit findings** written to MKF as `ArtifactRelation(VIOLATES)` edges from
  each violating artifact to the rule node it breaks — making findings
  queryable, traceable, and reportable as formal compliance evidence.

---

## 6. Dependencies (Planned)

- **GCL (Governance & Compliance Layer)** — every report invocation must
  `audit.record()` into the SQLite audit journal so the audit trail is
  complete and tamper-evident (CIPHER_archi §3.5).
- **MKF (Memory & Knowledge Fabric)** — RAG retrieval over the bundled ASPICE,
  MISRA-C, AUTOSAR, and ISO 26262 reference corpora; graph reads for the input
  bundle and graph writes for the violation edges.
- **TRF (Tool & Resource Fabric)** — MCP wrappers for PC-lint Plus, cppcheck,
  and Polyspace are the deterministic engines under the agent's hood.
- **ARE (A2A)** — skill `compliance_check` (planned, not yet registered).
- **Lateral A2A peer** — ASIL Review Agent (AGT-003); the HLD permits this
  lateral pair (CIPHER_HLD §11, "Permitted lateral pairs").

---

## 7. Open Items

- **Not yet implemented.** Beyond the empty package, nothing exists.
- Skill schema for `compliance_check` is unwritten.
- `ComplianceReport` JSON schema is unwritten.
- No rubrics directory (`cipher/agents/compliance/rubrics/`) exists despite
  being referenced in `CIPHER_archi §12.4`.
- No TRF wrappers for PC-lint Plus / cppcheck / Polyspace.
- No A2A card at `:7004`.
- No OPA policy bindings for `cipher.compliance.*` decision points.
- ASDLC §7 currently scopes MISRA-C:2012; HLD §6.5 references MISRA-C:2025 —
  version target must be reconciled by QA-PROC before implementation begins.

---

*Doc AGENT-COMPL-001 — Compliance Agent (STUB) — generated for CIPHER agent
catalog, 2026-05-17.*

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
