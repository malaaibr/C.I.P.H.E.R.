---
name: vcycle_s9n1
description: Generate complete traceability matrix spanning HLD, LLD, Code, Test, and UTD. Activate when user requests full traceability matrix, ASPICE compliance package, SWE.6 verification evidence, or V-cycle completion report.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.6
allowed-tools: [fs.read, llm.complete, fs.write, kg.upsert_node]
---

# Full Traceability Matrix Skill

## Objective

You are a Quality Assurance Engineer assembling the complete V-cycle traceability matrix spanning all artifact layers: HLD -> LLD -> Code -> Test -> UTD. This matrix serves as the definitive ASPICE compliance evidence package for SWE.6.

## Instructions

1. Read all upstream trace artifacts:
   - HLD-to-LLD trace from `inputArtifacts.hld_lld_trace_csv`.
   - LLD-to-Code trace from `inputArtifacts.lld_code_trace_csv`.
   - Test-to-Design trace from `inputArtifacts.test_design_trace_csv`.
   - UTD summary from `inputArtifacts.utd_csv`.
2. Join all matrices on their shared keys (HLD_ID, LLD_ID, Function_Name, Test_Case_ID) to produce a single unified matrix.
3. For each row in the unified matrix, determine the end-to-end chain status:
   - **Complete**: HLD -> LLD -> Code -> Test -> UTD, all links valid, test PASS.
   - **Partial**: One or more links present but chain is broken at some stage.
   - **Missing**: HLD item with no downstream artifacts.
4. Generate the full matrix CSV with columns: HLD_ID, HLD_Desc, LLD_ID, LLD_Desc, ASIL, Function, File, Line, Test_Case_ID, Test_Verdict, Chain_Status.
5. Calculate overall metrics: total chains, complete %, partial %, missing %.
6. Per ASIL level, calculate compliance rates and flag non-compliant ASIL C/D items.
7. Upsert the full matrix as a `TRACE_MATRIX` node in the knowledge graph via `kg.upsert_node`.
8. Write the full matrix to `outputArtifacts.full_trace_matrix_csv`.
9. Write the ASPICE compliance summary to `outputArtifacts.aspice_compliance_report`.
10. Generate a final assessment: PASS (all ASIL items complete), CONDITIONAL (non-safety items incomplete), or FAIL (any ASIL C/D chain broken).

## On-demand references (Stage 3)

See: ./references/ASPICE_SWE6_evidence_checklist.md
See: ./references/full_trace_v1.md
See: ./references/compliance_scoring_rules.md
