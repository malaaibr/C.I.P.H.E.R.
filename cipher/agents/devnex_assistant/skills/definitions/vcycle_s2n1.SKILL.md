---
name: vcycle_s2n1
description: Embed LLD requirement references into C source code as structured comments. Activate when user requests code annotation, requirement linking, traceability tagging, or ASPICE SWE.4 code-to-design linking.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.4
allowed-tools: [fs.read, fs.write, llm.complete]
---

# Code Annotation Skill

## Objective

You are a Software Engineer embedding LLD requirement traceability markers into C source code. Each function implementing an LLD requirement receives a structured comment block linking it to the corresponding requirement ID.

## Instructions

1. Read the LLD-to-function mapping from `inputArtifacts.lld_with_ids_csv`.
2. Read the target C source files from `inputArtifacts.source_files`.
3. Load the annotation prompt template `code_link_v1.md`.
4. For each function mapped to an LLD requirement, insert a structured comment block directly above the function definition:
   ```c
   /* @LLD_REQ: <LLD_ID>
    * @Description: <short description>
    * @ASIL: <asil_level>
    * @Parent_HLD: <parent_hld_id>
    */
   ```
5. If a function implements multiple LLD requirements, list all IDs in a single comment block.
6. Do not modify any executable code — only add or update comment blocks.
7. Preserve existing non-LLD comments unchanged.
8. Validate that every LLD requirement marked as functional has at least one annotated function.
9. Write the annotated source files to `outputArtifacts.annotated_sources`.
10. Generate a summary: total functions annotated, requirements with no code linkage, files modified.

## On-demand references (Stage 3)

See: ./references/code_link_v1.md
See: ./references/MISRA_C2023_deviations.md
See: ./references/ASPICE_SWE4_evidence_checklist.md
