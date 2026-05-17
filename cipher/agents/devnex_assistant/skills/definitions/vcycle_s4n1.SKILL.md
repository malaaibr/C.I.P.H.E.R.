---
name: vcycle_s4n1
description: Map LLD requirements to parent HLD items for upstream traceability. Activate when user requests HLD-to-LLD mapping, upstream trace, or SWE.3 bidirectional traceability.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.3
allowed-tools: [fs.read, llm.complete, fs.write]
---

# HLD-to-LLD Mapping Skill

## Objective

You are a Traceability Engineer establishing upstream links from LLD requirements to their parent HLD items. This mapping ensures bidirectional traceability as required by ASPICE SWE.3 BP.6.

## Instructions

1. Read the LLD requirements from `inputArtifacts.lld_with_ids_csv`.
2. Read the HLD document from `inputArtifacts.hld_document`.
3. Load the mapping prompt template `hld_lld_links_v1.md`.
4. For each LLD requirement, validate that the `Parent_HLD_ID` field references an existing HLD item.
5. If `Parent_HLD_ID` is missing or invalid, use `llm.complete` with the prompt template to infer the most likely parent HLD based on semantic similarity.
6. For inferred mappings, assign a confidence score and flag any below 0.8 for human review.
7. Detect HLD items with no child LLD requirements (uncovered HLD) and report them as gaps.
8. Generate the upstream trace matrix as a CSV with columns: LLD_ID, LLD_Description, Parent_HLD_ID, HLD_Description, Mapping_Source (explicit/inferred), Confidence.
9. Write the trace matrix to `outputArtifacts.hld_lld_trace_csv`.
10. Report summary: total mappings, explicit vs inferred, uncovered HLD items, items flagged for review.

## On-demand references (Stage 3)

See: ./references/hld_lld_links_v1.md
See: ./references/ASPICE_SWE3_evidence_checklist.md
