---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CIPHER AI Software Development Lifecycle (ASDLC)

| Field | Value |
|-------|-------|
| Document ID | PROC-001 |
| Version | 1.0 |
| ASPICE | MAN.3 — Project Management / SUP.1 — Quality Assurance |
| ASIL Applicability | QM through ASIL-D |
| Author | CIPHER QA Engineer (AI-assisted, human-reviewed) |
| Date | 2026-05-16 |
| Status | ACTIVE |

---

## 1. Purpose and Scope

This document defines the AI Software Development Lifecycle (ASDLC) process for the CIPHER DevNex platform. It governs how AI-generated artifacts are produced, reviewed, tested, and promoted within an ISO 26262-compliant automotive embedded software project.

The ASDLC applies to all CIPHER use cases (UC 1.1–5.5) and aligns with ASPICE Level 2 process outcomes for SWE.1–SWE.6, MAN.3, and SUP.1.

---

## 2. Agent Roles and Responsibilities

### 2.1 Tech Lead (CIPHER ARCHITECT)

Responsible for the platform UC catalog, sprint planning, and architectural decisions. Produces: UC catalog (interactive artifact), ADR documents, sprint WBS. Gate authority: approves sprint plan before DEV work begins.

### 2.2 Senior Developer (CIPHER DEV)

Implements modules according to the Tech Lead's UC plan and the sprint backlog. Must follow Wrap-First discipline: WRAP (adapter) by default, REFACTOR (targeted edits) when justified, REWRITE only with explicit ADR sign-off. Produces: Python skill modules, orchestrator patches, prompt templates.

### 2.3 Tester (CIPHER QA-TEST)

Creates pytest test suites covering unit behavior, edge cases, ASIL gate enforcement, and artifact contracts. Tests are written alongside or immediately after each module. No module is considered "done" until its test class passes 100%. Produces: `tests/test_<module>.py` files, test run reports.

### 2.4 QA Process Engineer (CIPHER QA-PROC)

Defines and enforces the ASDLC process itself. Reviews artifact completeness against ASPICE SWE.x checklists, monitors ASIL gate decisions, and maintains this document. Gate authority: signs off on phase transitions.

---

## 3. ASDLC Phase Gates

```
PHASE 0 — Architecture Review
  ├── Tech Lead produces UC catalog + sprint plan
  ├── QA-PROC reviews UC catalog for ASPICE SWE.1 coverage
  └── Gate G0: UC catalog approved → DEV sprint starts

PHASE 1 — Sprint 0: Foundation Fixes
  ├── DEV applies gap fixes (F-001..F-010) to MVP codebase
  ├── TESTER writes regression tests for each fix
  ├── CI: pytest tests/ -v must pass 100%
  └── Gate G1: all F-00x tests green → Sprint 1 starts

PHASE 2 — Sprint 1: Core UC Implementation
  ├── DEV implements sprint-scoped UC modules
  ├── TESTER writes UC-specific test classes
  ├── QA-PROC checks artifact contracts (JSON schema, MD sections)
  ├── CI: no regression in existing tests
  └── Gate G2: sprint UC tests green → merge to main

PHASE 3 — ASIL Gate Review (per UC with ASIL >= B)
  ├── AsilGate.evaluate() runs automatically in the skill pipeline
  ├── ASIL-D: SemanticConflictError raised → Safety Engineer G5 review mandatory
  ├── ASIL-C: HOLD returned → Safety Engineer review required, merge blocked
  ├── ASIL-B: HOLD returned → standard review, merge advisory
  └── Gate G3: ASIL gate decision documented in asil_gate_decision.json

PHASE 4 — Integration & Traceability
  ├── S9N1 full traceability matrix generated
  ├── UC 4.4 post-merge check passes (no RAM overlap)
  ├── QA-PROC verifies HLD→LLD→Code→Test chain is unbroken
  └── Gate G4: full traceability matrix reviewed

PHASE 5 — Safety Engineer Sign-off (ASIL-D only)
  ├── Safety Engineer reviews semantic_conflict_report.md / asil_review_*.md
  ├── G5 gate checklist completed (see UC 3.1 report template)
  └── Gate G5: human sign-off recorded in gate_decision artifact
```

---

## 4. Artifact Contracts

### 4.1 Per-UC Mandatory Artifacts

| UC | Artifact | Schema |
|----|---------|--------|
| All V-cycle | `section_layout.json` | SectionLayout dataclass |
| UC 1.1 | `<SWC>_TEMP_LLD_updated.csv` | REQ_ID, CATEGORY, DESCRIPTION |
| UC 1.4 | `Full_Traceability_Matrix.csv` | HLD_ID, LLD_ID, CODE_FUNCTION, FILE, LINE |
| UC 3.1 | `asil_review_<file>.json` + `.md` | AsilReviewReport dataclass |
| UC 4.1 | `QAAnswer` response object | question, answer, sources[] |
| UC 4.4 | `overlap_report.json` + `semantic_conflict_report.md` | OverlapReport dataclass |

### 4.2 Filename Alignment (F-001 fix)

The following filenames are canonical across the platform. Changing them breaks `trace_loader._CSV_MAP`.

| Stage | Canonical Filename |
|-------|-------------------|
| S3N1 | `LLD_Code_Trace_Matrix.csv` |
| S4N1 | `HLD_LLD_Trace_Matrix.csv` |
| S5N1 | `Full_Downstream_Trace.csv` |
| S8N1 | `UTD_LLD_Links.json` |
| S9N1 | `Full_Traceability_Matrix.csv` |

---

## 5. CI/CD Integration

### 5.1 Post-Merge Hook (UC 4.4)

After every `git merge` + build:
```bash
python -c "
from core.orchestrator import DevNexOrchestrator
from core.run_context import DevNexRunContext
ctx = DevNexRunContext(workspace_path='.')
orch = DevNexOrchestrator(ctx)
orch.run_uc4_4_semantic_check(map_file='build/firmware.map', lds_file='src/stm32h7xx_flash.ld', asil_level='D')
"
```
Exit code non-zero on `SemanticConflictError` — CI build fails with artifact links.

### 5.2 Test Gate

```bash
cd cipher/agents/devnex_assistant
python -m pytest tests/ -v --tb=short
```
All tests must pass before any feature branch is merged.

### 5.3 GCA Retry Configuration

`configs/ruleset.yaml` → `max_gca_retries: 3`. Override via `config.json` key `max_gca_retries`.

---

## 6. ASIL-Aligned Review Checkpoints

| ASIL Level | Minimum Review Actions |
|------------|----------------------|
| QM | Automated CI tests pass |
| A | CI pass + WARN logged, single developer review |
| B | CI pass + HOLD advisory, peer code review |
| C | CI pass + HOLD, senior engineer review, Safety Engineer advisory |
| D | CI pass + HARD_BLOCK, Safety Engineer G5 mandatory, asil_gate_decision.json archived |

---

## 7. MISRA-C:2012 Mandatory Rules

CIPHER enforces the following rules in all ASIL >= B components:

| Rule | Description | Enforcement |
|------|-------------|------------|
| R1.3 | No undefined behaviour | UC 3.1 Phase 1 TRIAGE |
| R11.3 | No pointer-type casting | UC 3.1 Phase 1 TRIAGE |
| R11.8 | No const/volatile cast removal | UC 4.4 + UC 3.1 |
| R14.4 | Boolean controlling expressions | UC 3.1 Phase 1 TRIAGE |
| R15.5 | Single exit point | UC 3.1 Phase 1 TRIAGE |
| R21.3 | No dynamic memory allocation | UC 3.1 Phase 1 TRIAGE |

---

## 8. Sprint Lifecycle Summary

| Sprint | Owner | Deliverables | Gate |
|--------|-------|-------------|------|
| Sprint 0 | DEV + TESTER | 10 gap fixes + regression tests | G1: 100% pass |
| Sprint 1 | DEV + TESTER | UC 3.1, UC 4.1 + test suites | G2: UC tests green |
| Sprint 2 | DEV + TESTER | UC 1.2, UC 2.1, UC 5.3 + tests | G2 |
| Sprint 3 | DEV + TESTER | UC 1.3, UC 2.2, UC 2.3 + tests | G2 |
| Sprint 4 | DEV + TESTER + QA | UC 1.5, UC 3.4, UC 3.5 + tests | G2 + G4 + G5 |

---

*CIPHER QA-PROC — ASDLC v1.0 — 2026-05-16*

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
