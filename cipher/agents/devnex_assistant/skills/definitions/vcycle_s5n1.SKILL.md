---
name: vcycle_s5n1
description: Generate complete downstream trace matrix from HLD through LLD to Code. Activate when user requests full downstream traceability, end-to-end design trace, or SWE.5 downstream evidence.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.5
allowed-tools: [fs.read, llm.complete, fs.write]
---

# Full Downstream Trace Skill

## Objective

You are a Traceability Engineer assembling the complete downstream trace matrix from HLD through LLD to implementing code. This matrix provides the full design-to-implementation chain for ASPICE SWE.5 compliance.

## Instructions

1. Read the HLD-to-LLD trace from `inputArtifacts.hld_lld_trace_csv`.
2. Read the LLD-to-Code trace from `inputArtifacts.lld_code_trace_csv`.
3. Load the full trace prompt template `full_trace_v1.md`.
4. Join the two trace matrices on LLD_ID to produce a unified downstream chain: HLD_ID -> LLD_ID -> Function_Name -> File_Path -> Line_Number.
5. Identify and report any broken chains:
   - HLD items with LLD but no code implementation.
   - LLD items present in HLD trace but missing from code trace.
6. Calculate chain completeness: percentage of HLD items with a complete path to code.
7. Generate the full downstream trace matrix as a CSV with columns: HLD_ID, HLD_Description, LLD_ID, LLD_Description, Function_Name, File_Path, Line_Number, Chain_Status (complete/broken).
8. Write the matrix to `outputArtifacts.full_downstream_trace_csv`.
9. Write a gap analysis report to `outputArtifacts.downstream_gap_report`.
10. For ASIL C/D items, any broken chain is flagged as a blocking finding.

## On-demand references (Stage 3)

See: ./references/full_trace_v1.md
See: ./references/ASPICE_SWE5_evidence_checklist.md
