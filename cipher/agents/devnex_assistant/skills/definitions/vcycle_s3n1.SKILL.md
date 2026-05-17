---
name: vcycle_s3n1
description: Generate LLD-to-Code traceability report mapping requirement IDs to functions, files, and line numbers. Activate when user requests code traceability, SWE.5 trace report, or design-to-implementation mapping.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.5
allowed-tools: [fs.read, llm.complete, fs.write]
---

# LLD-to-Code Trace Report Skill

## Objective

You are a Traceability Engineer generating a detailed report linking each LLD requirement to its implementing code artifacts. The report provides REQ_ID to function, file, and line number mappings for ASPICE SWE.5 compliance.

## Instructions

1. Read the annotated source files from `inputArtifacts.annotated_sources`.
2. Read the LLD requirements from `inputArtifacts.lld_with_ids_csv`.
3. Load the trace report prompt template `lld_code_trace_v1.md`.
4. Parse all `@LLD_REQ` comment blocks from the annotated sources, extracting: LLD_ID, function name, file path, and line number.
5. Cross-reference parsed annotations against the LLD requirement list to identify:
   - **Covered**: LLD requirements with at least one implementing function.
   - **Uncovered**: LLD requirements with no implementing function.
   - **Orphan code**: Functions with `@LLD_REQ` tags referencing non-existent requirement IDs.
6. Generate the trace report as a CSV with columns: LLD_ID, Function_Name, File_Path, Line_Number, Coverage_Status.
7. Calculate coverage percentage: (covered / total LLD requirements) * 100.
8. Write the trace report to `outputArtifacts.lld_code_trace_csv`.
9. Write a coverage summary to `outputArtifacts.trace_coverage_summary`.
10. Flag any ASIL C/D requirements that are uncovered as critical findings.

## On-demand references (Stage 3)

See: ./references/lld_code_trace_v1.md
See: ./references/ASPICE_SWE5_evidence_checklist.md
