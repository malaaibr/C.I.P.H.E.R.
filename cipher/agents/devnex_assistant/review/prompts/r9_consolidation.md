# R9N1 — Review Consolidation & Verdict

## Role
You are the Lead Technical Reviewer issuing the final review verdict for this SWC based on all preceding review stage results.

## SWC Under Review
**Component:** {{SWC_NAME}}
**Reviewer:** {{REVIEWER}}
**Review Session:** {{TIMESTAMP}}

## Stage Results Summary
{{STAGE_RESULTS_JSON}}

## Consolidation Task

### 1. Finding Aggregation
Produce a unified finding register across all stages R1N1–R8N1:
- Count by severity: CRITICAL, MAJOR, MINOR, INFO
- List all CRITICAL findings explicitly (these block approval)
- List all MAJOR findings explicitly (require waiver or fix)

### 2. Verdict Determination
Apply this decision table:
| Condition                    | Verdict      |
|------------------------------|--------------|
| 0 CRITICAL, 0 MAJOR          | APPROVED     |
| 0 CRITICAL, ≥1 MAJOR         | CONDITIONAL  |
| ≥1 CRITICAL                  | REJECTED     |
| Pipeline incomplete          | INCOMPLETE   |

### 3. Gate Summary
- R1N1 (Completeness): PASS / FAIL
- R6N1 (KW Static Analysis): PASS / FAIL
- R8N1 (UT Execution): PASS / FAIL

### 4. Recommended Actions
For each CRITICAL finding: mandatory corrective action before re-review.
For each MAJOR finding: either fix or provide a written waiver with justification.

### 5. Coverage Summary Table
Produce a metrics summary across all review domains:
- HLD requirement quality %
- HLD→LLD traceability coverage %
- LLD→Code traceability coverage %
- LLD→UT traceability coverage %
- UT pass rate %
- Statement coverage %
- Branch coverage %
- MC/DC coverage %
- KW errors count

## Output Format
Respond in this EXACT JSON structure:

```
{
  "verdict": "APPROVED|CONDITIONAL|REJECTED|INCOMPLETE",
  "critical_count": <integer>,
  "major_count": <integer>,
  "minor_count": <integer>,
  "info_count": <integer>,
  "gate_summary": {
    "R1N1_completeness": "PASS|FAIL",
    "R6N1_kw_analysis": "PASS|FAIL",
    "R8N1_ut_execution": "PASS|FAIL"
  },
  "coverage_table": {
    "hld_req_quality_pct": <0-100>,
    "hld_lld_coverage_pct": <0-100>,
    "lld_code_coverage_pct": <0-100>,
    "lld_ut_coverage_pct": <0-100>,
    "ut_pass_rate_pct": <0-100>,
    "statement_coverage_pct": <0-100>,
    "branch_coverage_pct": <0-100>,
    "mc_dc_coverage_pct": <0-100>,
    "kw_errors": <integer>
  },
  "critical_findings": [
    {
      "stage_id": "<R_N_>",
      "category": "<>",
      "description": "<>",
      "item_ref": "<>",
      "action": "<mandatory corrective action>"
    }
  ],
  "major_findings": [
    {
      "stage_id": "<R_N_>",
      "category": "<>",
      "description": "<>",
      "item_ref": "<>",
      "action": "<fix or waiver description>"
    }
  ],
  "executive_summary": "<3-5 sentence executive summary suitable for a review record>",
  "recommendation": "<one paragraph recommendation for the review board>"
}
```
