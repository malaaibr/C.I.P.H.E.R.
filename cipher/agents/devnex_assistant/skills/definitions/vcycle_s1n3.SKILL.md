---
name: vcycle_s1n3
description: Extract updated LLD requirements with unique IDs from the requirements management system. Activate when user needs to pull LLD with DOORS IDs, sync RM artifacts, or refresh local LLD baseline.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.3
allowed-tools: [doors.read, fs.write]
---

# Extract LLD with IDs Skill

## Objective

You are a Requirements Engineer extracting the authoritative LLD requirement set from the RM system (DOORS/ReqIF). The extracted data includes DOORS-assigned unique IDs that serve as the single source of truth for all downstream traceability.

## Instructions

1. Connect to the configured DOORS module using `doors.read` with the project baseline and module path from `inputArtifacts.doors_config`.
2. Query all LLD requirements matching the target SWC module filter.
3. For each requirement, extract: DOORS_Object_ID, LLD_ID, Description, Parent_HLD_ID, ASIL, Status, Last_Modified.
4. Validate that all returned objects have non-null DOORS_Object_IDs.
5. Compare against the previous local baseline (if available at `inputArtifacts.previous_baseline`) and flag additions, modifications, and deletions.
6. Write the extracted LLD set to `outputArtifacts.lld_with_ids_csv` in CSV format.
7. Write a delta report to `outputArtifacts.lld_delta_report` listing all changes since last extraction.
8. Report summary: total requirements extracted, new, modified, deleted, and any orphaned IDs.

## On-demand references (Stage 3)

See: ./references/DOORS_export_configuration.md
See: ./references/ASPICE_SWE3_evidence_checklist.md
