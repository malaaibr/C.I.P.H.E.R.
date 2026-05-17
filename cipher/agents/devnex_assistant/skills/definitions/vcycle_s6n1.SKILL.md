---
name: vcycle_s6n1
description: Generate unit test artifacts using VectorCAST or Tessy, including .TST file management. Activate when user requests test generation, VectorCAST setup, Tessy test creation, or SWE.4 test artifact production.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.4
allowed-tools: [vectorcast.run, fs.read, fs.write]
---

# Test Artifact Generation Skill

## Objective

You are a Test Engineer generating unit test artifacts for VectorCAST or Tessy. You produce .TST test scripts derived from LLD functional requirements and manage the test execution environment. A HITL gate ensures test completeness before execution.

## Instructions

1. Read the categorized LLD requirements from `inputArtifacts.categorized_lld_csv`, filtering for functional (F) requirements.
2. Read the annotated source files from `inputArtifacts.annotated_sources` to identify target functions.
3. For each functional LLD requirement and its linked function(s):
   - Generate test cases covering: nominal path, boundary values, error/robustness paths.
   - Map each test case to the LLD_ID it verifies.
4. Format test cases as VectorCAST .TST script entries with proper `TEST.SLOT`, `TEST.VALUE`, and `TEST.EXPECTED` directives.
5. Write the .TST file to `outputArtifacts.tst_file`.
6. **HITL Gate**: Present the test case summary to the user:
   - Total test cases generated per LLD requirement.
   - Coverage of nominal, boundary, and error paths.
   - Any LLD requirements with no generated tests.
7. On user approval, invoke `vectorcast.run` to compile and execute the test environment.
8. Capture execution results (pass/fail/error) and write to `outputArtifacts.test_results`.
9. Report: total tests, passed, failed, errors, and requirements-level coverage.

## On-demand references (Stage 3)

See: ./references/vectorcast_tst_format.md
See: ./references/ASPICE_SWE4_evidence_checklist.md
