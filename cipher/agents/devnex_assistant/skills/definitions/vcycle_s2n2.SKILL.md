---
name: vcycle_s2n2
description: Human-In-The-Loop gate for developer review of annotated source code. Activate when annotated code is ready for developer sign-off or SWE.4 review checkpoint is required.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.4
allowed-tools: [fs.read]
---

# Developer Review Gate Skill

## Objective

You are a Review Coordinator managing the HITL gate for developer approval of LLD-annotated source code. No downstream processing proceeds until the developer explicitly approves the annotations.

## Instructions

1. Read the annotated source files from `inputArtifacts.annotated_sources` using `fs.read`.
2. Read the annotation summary from `inputArtifacts.annotation_summary`.
3. Present the developer with a structured review package:
   - Total files modified and functions annotated.
   - List of any LLD requirements with no code linkage (gaps).
   - List of functions with no LLD linkage (orphans).
   - Diff summary showing only the added comment blocks (no code changes expected).
4. For each file, display the annotation comment blocks with surrounding context (3 lines above and below).
5. Ask the developer to confirm one of:
   - **APPROVE**: All annotations are correct. Proceed to downstream traceability.
   - **REVISE**: Specify corrections needed. List the LLD_IDs and functions requiring changes.
   - **REJECT**: Annotations are fundamentally incorrect. Return to vcycle_s2n1 for regeneration.
6. Record the review decision, reviewer identity, and timestamp.
7. If REVISE, capture the correction instructions and pass them back to vcycle_s2n1.
8. If APPROVE, write the signed-off status to `outputArtifacts.review_decision`.
9. Do not proceed to any downstream skill until APPROVE is received.

## On-demand references (Stage 3)

See: ./references/ASPICE_SWE4_evidence_checklist.md
See: ./references/review_gate_protocol.md
