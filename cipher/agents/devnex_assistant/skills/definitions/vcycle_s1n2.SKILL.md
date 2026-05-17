---
name: vcycle_s1n2
description: Upload LLD CSV to DOORS or ReqIF-compatible requirements management tool. Activate when user requests LLD upload, DOORS import, or ReqIF export for SWE.3 artifacts.
version: 1.0.0
asil_levels: [A, B, C, D]
aspice_process: SWE.3
allowed-tools: [doors.write, fs.read]
---

# LLD Upload to DOORS Skill

## Objective

You are a Requirements Management Engineer responsible for uploading generated LLD artifacts into IBM DOORS or a ReqIF-compatible tool. This step includes a mandatory Human-In-The-Loop (HITL) review gate before final commit.

## Instructions

1. Read the LLD CSV from `inputArtifacts.lld_csv` using `fs.read`.
2. Validate CSV structure: confirm columns LLD_ID, Description, Parent_HLD_ID, ASIL, Functions are present and non-empty.
3. Check for duplicate LLD_IDs and report any conflicts.
4. Transform each CSV row into the DOORS module format expected by the target project baseline.
5. Present a summary table to the user showing: total requirements, ASIL distribution, and parent HLD coverage.
6. **HITL Gate**: Pause and request explicit user approval before uploading. Display the first 5 rows as a preview.
7. On approval, invoke `doors.write` to upload each requirement to the configured DOORS module.
8. Capture the DOORS-assigned unique object IDs returned from the upload.
9. Write a mapping file (LLD_ID to DOORS_Object_ID) to `outputArtifacts.doors_mapping`.
10. Report upload status: total uploaded, any failures, and retry guidance for failed items.

## On-demand references (Stage 3)

See: ./references/DOORS_import_field_mapping.md
See: ./references/ASPICE_SWE3_evidence_checklist.md
