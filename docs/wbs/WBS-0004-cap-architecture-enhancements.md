---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# WBS-0004 — Citation-Aware Prompting & Architecture Enhancements

**Status**: Active  
**Created**: 2026-05-17  
**Sources**:
- Citation-Aware Prompting for Grounded, Production-Grade LLM Agents (v3.0, May 2026)
- CIPHER Architecture HLD R3.0 (CIPHER-HLD-001, May 2026)

**Scope**: Apply concrete, code-level enhancements derived from both reference documents to the CIPHER platform, prioritized by impact on production readiness.

---

## Priority 1 — Core Schemas & Contracts (Foundation)

All subsequent enhancements depend on these typed objects existing.

### E-001: CRC Schema (`cipher.cap.crc.v1`)
- **Layer**: Core (cipher/core/schemas/)
- **File**: `crc.py` (new)
- **What**: Pydantic models for Cited Reasoning Chain — `CRCChain`, `CRCStep`, `Citation`, `Claim`, `EvidenceType` enum, `ClaimKind` enum
- **Source**: CAP §II.D + §V.A — CRC = ⟨τ₁…τₙ⟩ where τᵢ = (Tᵢ, Cᵢ, Kᵢ)
- **Why**: Every CAP component (validator, metrics, prompt, loop) consumes/produces CRC objects

### E-002: IssueReport Schema
- **Layer**: Core (cipher/core/schemas/)
- **File**: `issue_report.py` (new)
- **What**: Pydantic model for typed validator feedback — `IssueReport`, `WellFormednessViolation`, `ViolationType` enum (UNCITED, UNRESOLVED, TYPE_MISMATCH, ASIL_DOWNCAST, PHASE_VIOLATION, FIELD_MISMATCH)
- **Source**: CAP §V.B + §V.E — validator returns typed IssueReport naming exact step and failed WF condition
- **Why**: Draft-Verify-Finalize loop requires typed feedback, not free-text retry

### E-003: ArtifactRelation Enhancements
- **Layer**: Core (cipher/core/schemas/artifact_relation.py)
- **File**: existing — extend
- **What**: Add `GENERATED_BY`, `APPROVED_BY`, `VIOLATES`, `CONFORMS_TO` to RelationType enum; add `valid_from`, `valid_to` (temporal edges), `confidence` float field
- **Source**: HLD §7.3 ArtifactRelation Model + CAP §VI.F KG subgraph
- **Why**: Current 6 relation types miss agent provenance and temporal validity that both docs require

### E-004: AgentCard Trust Tier
- **Layer**: Core (cipher/core/schemas/agent_card.py)
- **File**: existing — extend
- **What**: Add `TrustTier` enum (T0, T1, T2) and `trust_tier` field to AgentCard; add `asil_levels` list field to SkillDescriptor
- **Source**: HLD §9 — T0=always-on elevated, T1=advisory read-only, T2=can mutate + requires HITL
- **Why**: Trust enforcement is prerequisite for policy-gated agent actions

### E-005: ContextManifest Schema
- **Layer**: Core (cipher/core/schemas/)
- **File**: `context_manifest.py` (new)
- **What**: Pydantic model listing all evidence provided to the LLM — `ContextManifest` with `evidence_items` list (uri, hash, artifact_type, asil_level)
- **Source**: CAP §V.A — the manifest is the closed set the model is allowed to cite from
- **Why**: Validator needs a bounded evidence set to check citations against

---

## Priority 2 — CAP Validator & Governance (Safety Gate)

### E-006: CAP Validator Module
- **Layer**: GCL (cipher/gcl/)
- **File**: `cap_validator/validator.py` (new)
- **What**: Implement 6 well-formedness predicates:
  - WF₁: Every step has ≥1 citation
  - WF₂: Every citation URI resolves (via MKF lookup or manifest check)
  - WF₃: Evidence type is permitted for claim kind
  - WF₄: ASIL coherence (cited ≥ claim)
  - WF₅: Phase appropriateness (claim kind valid for current ASPICE phase)
  - WF₆: Structured field consistency (shared fields must agree within tolerance)
- **Source**: CAP §V.B — six formal predicates, each O(1) per citation
- **Returns**: `ValidationResult` with pass/fail + list of `WellFormednessViolation`

### E-007: Domain Pack Structure (iso26262-asil-b)
- **Layer**: GCL (cipher/gcl/domain_packs/)
- **File**: `iso26262_asil_b/` directory (new)
- **What**: Create domain pack with:
  - `pack.yaml` — metadata, ASIL level, applicable standards
  - `policies/cap_policy.rego` — OPA policy for CAP enforcement
  - `schemas/permitted_types.json` — ClaimKind → allowed EvidenceType mapping
  - `schemas/phase_kinds.json` — ASPICE phase → allowed ClaimKinds
- **Source**: HLD §5 GCL Domain Pack Loader + CAP §V.B WF₃/WF₅ mappings
- **Why**: Externalizes safety rules from code into auditable config

### E-008: Budget Enforcer
- **Layer**: ARE (cipher/are/)
- **File**: `budget_enforcer/enforcer.py` (new)
- **What**: Token cap + wall-clock limit + LLM call count per task. Returns BUDGET_EXCEEDED on breach. Integrates with TaskContract.timeout_s
- **Source**: HLD §6 ARE — Budget Enforcer module
- **Why**: Prevents runaway CAP revision loops from consuming unbounded resources

---

## Priority 3 — Enhanced Prompting (Production Prompt)

### E-009: Citation-Aware S1N1 Prompt (lld_gen_v2.md)
- **Layer**: AAL (cipher/agents/devnex_assistant/prompts/)
- **File**: `lld_gen_v2.md` (new — v1 preserved as baseline)
- **What**: Rewrite S1N1 prompt to enforce citation-aware contract:
  - §1 Persona: Expert Senior Automotive Embedded SW Architect
  - §2 Evidence-only constraint: "do not infer or invent…all assertions must cite [HLD-row], [source:Lnn-Lnn], or [map:symbol]"
  - §3 Internal CoT/ReAct loop with CRC step emission
  - §4 Output as CRC JSON (cipher.cap.crc.v1 schema), NOT free-form CSV
  - Explicit abstention instruction: refuse with reason when evidence insufficient
- **Source**: CAP §VI.C — production prompt reproduced in paper
- **Diff from v1**: v1 asks for internal reasoning + CSV output; v2 asks for CRC JSON with machine-checkable citations per step

### E-010: Draft-Verify-Finalize Loop in DevNex Orchestrator
- **Layer**: AAL (cipher/agents/devnex_assistant/core/orchestrator.py)
- **File**: existing — extend `_run_s1n1`
- **What**: Wrap S1N1 execution in 3-state machine:
  1. DRAFT: Generate CRC via lld_gen_v2.md prompt
  2. VERIFY: Pass CRC to CAP Validator (E-006)
  3. On failure: REVISE with IssueReport (max 3 iterations)
  4. On pass: FINALIZE — render CSV from validated CRC, persist ArtifactRelation edges
  5. On R_max exceeded: escalate to HITL gate
- **Source**: CAP §V.E — draft-verify-finalize state machine
- **Why**: The validator is a hard gate; the model cannot bypass it

---

## Priority 4 — Skill Architecture (Progressive Disclosure)

### E-011: SKILL.md Files for DevNex V-Cycle Skills
- **Layer**: AAL (cipher/agents/devnex_assistant/skills/definitions/)
- **Files**: 13 SKILL.md files (one per V-cycle node)
- **What**: Create versioned SKILL.md with YAML frontmatter (name, description, version, asil_levels, aspice_process, allowed-tools) + markdown instruction body
- **Source**: HLD §8.1 — SKILL.md format with frontmatter + progressive disclosure
- **Priority skill**: `vcycle_s1n1.SKILL.md` (LLD generation) — references lld_gen_v2.md prompt

### E-012: Enhanced Skill Loader (3-Stage Progressive Disclosure)
- **Layer**: ARE (cipher/are/skill_loader/)
- **File**: existing `loader.py` — extend
- **What**: Implement 3-stage loading:
  - Stage 1 (Discovery): Parse YAML frontmatter only (~5 tokens per skill)
  - Stage 2 (Activation): Load full SKILL.md body when Orchestrator selects skill
  - Stage 3 (Execution): Load bundled reference files on demand
- **Source**: HLD §8.2 — progressive disclosure stages
- **Why**: Context-efficient skill loading regardless of installed skill count

---

## Priority 5 — Orchestrator Intelligence

### E-013: Runtime Prompt Contract Assembly
- **Layer**: AAL (cipher/core/orchestrator.py)
- **File**: existing — extend
- **What**: Implement 4-part delegation contract per HLD §6.1:
  - INSTRUCTION: Active skill's SKILL.md body
  - CONTEXT: Memory Agent RAG retrieval + user input
  - TOOLS: OPA scope policy filtered by task ASIL
  - MODEL: LLM Gateway tiering (haiku for triage, sonnet/opus for generation)
- **Source**: HLD §6.1 AORCHESTRA 4-tuple model

### E-014: Context Gap Detection
- **Layer**: AAL (cipher/core/orchestrator.py)
- **File**: existing — extend
- **What**: Before every task dispatch, execute 5-step enrichment:
  1. Parse intent (entities, skill match)
  2. Compute gaps (referenced but not provided)
  3. RAG retrieval via Memory Agent
  4. Confidence check (< 0.6 → escalate to Research Agent)
  5. Contract assembly
- **Source**: HLD §6.2 — 5-step context enrichment loop

---

## Priority 6 — Metrics & Observability

### E-015: CAP Metrics Module
- **Layer**: Core (cipher/core/)
- **File**: `cap_metrics.py` (new)
- **What**: Implement 8 metrics from CAP §VII.A:
  - Citation Coverage (CC)
  - Citation Support Rate (CSR)
  - Attribution Precision / Recall
  - Abstention Quality (F₁)
  - Determinism Score (DS) — pairwise Jaccard on triple sets
  - Provenance Determinism (PDS)
  - Hallucination Rate (auto + human)
  - ASPICE Evidence Completeness (AEC)
- **Source**: CAP §VII.A — formal metric definitions
- **Why**: "You can measure it" is the paper's core operational claim

---

## Implementation Order

```
Phase A (Foundation):    E-001 → E-002 → E-003 → E-004 → E-005
Phase B (Safety Gate):   E-006 → E-007 → E-008
Phase C (Prompt):        E-009 → E-010
Phase D (Skills):        E-011 → E-012
Phase E (Orchestrator):  E-013 → E-014
Phase F (Metrics):       E-015
```

Phases A-C are the minimum viable CAP pipeline. Phases D-F extend the architecture toward HLD R3.0 compliance.

---

## Open Questions

1. **MKF resolve()**: WF₂ requires URI resolution against the Knowledge Graph. Current MKF has Qdrant vector search + BM25 but no URI-based node lookup. Need to add `resolve(uri) → ArtifactNode | None` to Memgraph driver.
2. **Schema-constrained decoding**: CAP paper recommends constraining the decoder to emit only valid CRC JSON. Current Ollama driver doesn't support structured output mode. May need `format: json_schema` parameter in Ollama API or use Outlines.
3. **CRC → CSV rendering**: After CRC validation, the final LLD CSV is rendered deterministically from validated claims — not LLM-generated. Need a `crc_to_csv_renderer.py` utility.
4. **Existing S1N1 consumers**: v1 prompt outputs CSV directly. v2 outputs CRC JSON. DevNex GUI panels that parse CSV will need an adapter, or we render CSV as a post-CRC step and keep the GUI contract unchanged.

---

## Test Plan

- `tests/unit/test_crc_schema.py` — CRC model validation, serialization round-trip
- `tests/unit/test_cap_validator.py` — WF₁–WF₆ with pass/fail fixtures
- `tests/unit/test_issue_report.py` — IssueReport construction and serialization
- `tests/unit/test_artifact_relation.py` — new relation types + temporal fields
- `tests/unit/test_budget_enforcer.py` — token/time/call limits
- `tests/unit/test_cap_metrics.py` — metric computation on synthetic CRCs
- `tests/integration/test_dvf_loop.py` — Draft-Verify-Finalize end-to-end with mock LLM
