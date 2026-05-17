---
doc_id: AGENT-TEST-001
agent_name: test_agent
status: STUB
role: Unit test generation + execution agent (planned)
layer: AAL
phase_target: Phase 2 (post-MVP)
last_updated: 2026-05-17
---

# test_agent — Agent Documentation

## 1. Role & Capabilities (Planned)

The `test_agent` corresponds to the **CIPHER QA-TEST** role defined in `docs/ASDLC.md` §2.3 (Tester). Its planned responsibilities are:

- Generate `pytest` test suites covering unit behavior for newly implemented modules.
- Author edge-case and negative-path tests (boundary values, malformed inputs).
- Enforce **ASIL gate** assertions in test cases (verify that ASIL ≥ B modules raise `SemanticConflictError` / `HOLD` as specified by `AsilGate.evaluate()`).
- Validate **artifact contracts** — JSON schema conformance and required Markdown sections per UC.
- Orchestrate test execution and collect coverage evidence for the Test Gate.
- Block "module-done" status until the corresponding test class is 100% green (per ASDLC §2.3 closure rule).

## 2. Current State — STUB

This agent is **not yet implemented**. The implementation directory contains only a README placeholder.

Actual files under `CIPHER_Repo/cipher/agents/test_agent/`:

| File | Purpose |
|------|---------|
| `README.md` | One-line stub: "Phase 2 stub for unit-test generation, execution coordination, and coverage evidence handling." |

No `__init__.py`, no skill module, no AgentCard registration, no orchestrator node, no A2A skill binding exists at this time. The AAL roll-up classifies this agent as **README-only**.

## 3. Reference to ASDLC

- **ASDLC §2.3 — Tester (CIPHER QA-TEST):** defines the role; tests produced are `tests/test_<module>.py` plus test run reports; "no module is considered done until its test class passes 100%".
- **ASDLC §5.2 — Test Gate:** the CI command `python -m pytest tests/ -v --tb=short` (run from `cipher/agents/devnex_assistant`) is the gate this agent must satisfy before any feature branch is merged.
- **ASDLC §3 — Phase Gates G1 / G2:** TESTER is the named actor producing regression tests for Sprint 0 fixes (F-001..F-010) and UC-specific test classes in Sprint 1+.

## 4. Planned UC Mapping

The agent supports the cross-cutting "tests written alongside" pattern that every UC in the CIPHER catalog inherits. There is no single UC owned by `test_agent`; instead it consumes the output of each DEV-implemented UC and emits paired test artifacts.

| UC family | test_agent contribution |
|-----------|--------------------------|
| UC 1.x (Requirements → HLD) | Schema conformance tests for HLD JSON artifacts. |
| UC 2.x (LLD → Code) | Unit tests for generated skill modules; mocked LLM adapter tests. |
| UC 3.x (Safety / ASIL) | Tests for ASIL gate behavior at QM/A/B/C/D levels; `SemanticConflictError` raising. |
| UC 4.x (Integration) | Post-merge regression suite; UC 4.4 RAM-overlap test wiring. |
| UC 5.x (Traceability) | Tests asserting unbroken HLD→LLD→Code→Test trace links. |

## 5. Inputs / Outputs (Planned)

**Inputs**

- Source code module(s) under `cipher/agents/<agent_name>/` or `cipher/<layer>/`.
- The corresponding LLD section (consumed via `devnex_assistant`).
- UC identifier and ASIL level (for gate assertion templates).
- Artifact contract schema (from ASDLC §4.1).

**Outputs**

- `tests/test_<module>.py` — pytest test class with unit, edge-case, and ASIL assertions.
- Test run report (pytest `--junitxml` or equivalent) for the G1/G2 gate evidence.
- Coverage delta for the affected module.

## 6. Dependencies (Planned)

- **TRF (LLM Gateway, port 8200):** consumed for LLM-driven test scaffolding; routed via `TaskClassRouter` as a code-generation task class.
- **devnex_assistant:** primary upstream — supplies the LLD section and the implemented module path so test_agent knows what surface to cover.
- **ARE / A2A Server (port 8100):** future skill registration via `SkillLoader` so test_agent can be invoked over A2A.
- **GCL (OPA + audit journal):** test runs and gate outcomes recorded in the SQLite audit journal.
- **Core schemas:** `TaskContract`, `AgentCard` for registration.

## 7. Open Items

- **Not yet implemented.** No code, no `__init__.py`, no AgentCard, no orchestrator node, no skill registration.
- Test-generation prompt templates not authored.
- Coverage threshold policy (per ASIL level) not defined.
- ASIL-gate assertion helper library not designed.
- Integration with `devnex_assistant` orchestrator (which node triggers test_agent) is undefined.
- No tests-for-the-tester strategy decided (meta-testing of generated suites).

Tracking: scheduled for **Phase 2 (post-MVP)** per the stub README. No owner assigned in the AAL roll-up.
