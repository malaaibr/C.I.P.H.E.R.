---
name: vcycle_s7n1
description: Parse .TST test results and generate a formal Unit Test Documentation (UTD) report. Activate when user requests UTD generation, test documentation, or SWE.4 test evidence packaging.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.4
allowed-tools: [fs.read, llm.complete, fs.write]
---

# Unit Test Documentation Skill

## Objective

You are a Test Documentation Engineer producing a formal Unit Test Documentation (UTD) report from VectorCAST/Tessy .TST execution results. The UTD serves as the official SWE.4 test evidence artifact.

## Instructions

1. Read the .TST execution results from `inputArtifacts.test_results`.
2. Read the .TST file from `inputArtifacts.tst_file` to extract test case definitions.
3. Read the LLD requirements from `inputArtifacts.lld_with_ids_csv` for requirement cross-referencing.
4. For each test case, produce a UTD entry containing:
   - Test_Case_ID (auto-generated, sequential).
   - Linked_LLD_ID.
   - Test_Description.
   - Preconditions, Input_Values, Expected_Result, Actual_Result.
   - Verdict (PASS/FAIL).
5. Group test cases by LLD requirement for structured reporting.
6. Calculate per-requirement test verdict: PASS (all tests pass), FAIL (any test fails), PARTIAL (mix of pass and not-executed).
7. Generate the UTD document in structured CSV format with all fields above.
8. Append a summary section: total test cases, pass rate, requirements fully verified, requirements with failures.
9. Write the UTD to `outputArtifacts.utd_csv`.
10. Write a UTD summary report to `outputArtifacts.utd_summary`.
11. Flag any ASIL C/D requirements with FAIL verdicts as critical findings requiring immediate attention.

## On-demand references (Stage 3)

See: ./references/UTD_template.md
See: ./references/ASPICE_SWE4_evidence_checklist.md
