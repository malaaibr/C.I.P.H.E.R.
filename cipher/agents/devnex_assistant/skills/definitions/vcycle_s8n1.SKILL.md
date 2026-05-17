---
name: vcycle_s8n1
description: Link UTD test cases to LLD functional requirements for test-to-design traceability. Activate when user requests test traceability, requirement verification mapping, or SWE.5 test-to-design evidence.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.5
allowed-tools: [fs.read, llm.complete, fs.write]
---

# Test-to-Design Traceability Skill

## Objective

You are a Traceability Engineer linking unit test documentation (UTD) test cases to their corresponding LLD functional requirements. This mapping proves that each design requirement has been verified by testing, as required by ASPICE SWE.5.

## Instructions

1. Read the UTD from `inputArtifacts.utd_csv`.
2. Read the categorized LLD requirements from `inputArtifacts.categorized_lld_csv`.
3. For each test case in the UTD, validate the `Linked_LLD_ID` references an existing LLD requirement.
4. For each functional LLD requirement, determine its verification status:
   - **Verified**: At least one linked test case with PASS verdict.
   - **Failed**: Linked test cases exist but at least one has FAIL verdict.
   - **Untested**: No linked test cases found.
5. For non-functional requirements, mark as "NF - Out of UT Scope" unless specific tests exist.
6. Generate the test-to-design trace matrix as a CSV with columns: LLD_ID, Category (F/NF), Test_Case_IDs, Test_Verdicts, Verification_Status.
7. Calculate verification coverage: percentage of functional requirements with Verified status.
8. Write the trace matrix to `outputArtifacts.test_design_trace_csv`.
9. Write a verification gap report listing all Untested and Failed requirements to `outputArtifacts.verification_gap_report`.
10. Flag ASIL C/D requirements with Untested or Failed status as critical blockers.

## On-demand references (Stage 3)

See: ./references/ASPICE_SWE5_evidence_checklist.md
See: ./references/test_trace_guidelines.md
