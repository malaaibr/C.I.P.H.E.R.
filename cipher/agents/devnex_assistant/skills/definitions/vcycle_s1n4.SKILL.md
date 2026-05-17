---
name: vcycle_s1n4
description: Classify LLD requirements as functional or non-functional. Activate when user requests requirement categorization, functional analysis, or SWE.3 requirement type tagging.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.3
allowed-tools: [fs.read, llm.complete]
---

# Requirement Categorization Skill

## Objective

You are a Requirements Analyst classifying each LLD requirement as functional (F) or non-functional (NF). This categorization drives downstream test strategy selection and ASPICE evidence packaging.

## Instructions

1. Read the LLD requirements from `inputArtifacts.lld_with_ids_csv` using `fs.read`.
2. Load the categorization prompt template `categorize_reqs_v1.md`.
3. For each LLD requirement, apply the prompt template to determine its category:
   - **Functional (F)**: Describes behavior, computation, data transformation, state transitions, or I/O operations.
   - **Non-Functional (NF)**: Describes timing constraints, memory limits, safety mechanisms, diagnostic behavior, or coding standards compliance.
4. For ambiguous requirements, assign a confidence score (0.0-1.0) and flag any below 0.7 for human review.
5. Produce an augmented CSV adding columns: Category (F/NF), Confidence, Review_Flag.
6. Generate a summary: total F count, total NF count, flagged-for-review count.
7. Write the categorized output to `outputArtifacts.categorized_lld_csv`.
8. Validate that no requirement is left uncategorized.
9. If ASIL D requirements are flagged as low-confidence, escalate with a warning to the user.

## On-demand references (Stage 3)

See: ./references/categorize_reqs_v1.md
See: ./references/ASPICE_SWE3_evidence_checklist.md
