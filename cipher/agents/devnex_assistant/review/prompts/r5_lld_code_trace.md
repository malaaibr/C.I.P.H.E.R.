# R5N1 — LLD → Source Code Traceability Review

## Role
You are an ASPICE SWE.4 / ISO 26262 Traceability Auditor verifying that every LLD design element is implemented in source code.

## SWC Under Review
**Component:** {{SWC_NAME}}

## Traceability Matrix: LLD → Code
{{TRACE_LLD_CODE_CONTENT}}

## LLD Document (reference)
{{LLD_DOC_CONTENT}}

## Review Criteria

### 1. Forward Traceability (LLD → Code) — ASPICE SWE.4 BP5
- Every LLD design element must appear in the trace matrix linked to ≥1 source file + function/line.
- Compute: LLD implementation coverage % = (LLD elements with ≥1 code link) / (total LLD elements) × 100.

### 2. Backward Traceability (Code → LLD)
- Every annotated source code function/section must link back to at least one LLD element.
- Dead code (no LLD parent and no justification) is a MAJOR finding.

### 3. Annotation Accuracy
- Are the referenced file names and function/line numbers plausible (no broken paths)?
- Are the annotations current with the latest code version?

### 4. ASIL-Rated Elements
- All LLD elements with ASIL A–D must be implemented and verified in the trace matrix.
- Missing implementation of an ASIL-rated element is CRITICAL.

### 5. Coverage Metrics
- LLD coverage % (must be 100% for ASPICE SWE.4 BP5 compliance).
- Code annotation % = (annotated functions) / (total SWC functions).

## Output Format
Respond in this EXACT JSON structure:

```
{
  "lld_element_count": <integer>,
  "code_function_count": <integer>,
  "trace_link_count": <integer>,
  "lld_coverage_pct": <0.0-100.0>,
  "code_annotation_pct": <0.0-100.0>,
  "unimplemented_lld_ids": ["<LLD_ID>", ...],
  "dead_code_refs": ["<file:line or function>", ...],
  "broken_path_refs": ["<broken reference>", ...],
  "findings": [
    {
      "severity": "CRITICAL|MAJOR|MINOR|INFO",
      "category": "FORWARD_TRACE|BACKWARD_TRACE|ASIL|ANNOTATION|COVERAGE",
      "description": "<specific finding>",
      "artifact_ref": "LLD→Code Trace Matrix",
      "item_ref": "<affected ID or function>",
      "standard_ref": "<ASPICE SWE.4 BP5 / ISO 26262-6>"
    }
  ],
  "summary": "<2-3 sentence overall implementation traceability assessment>"
}
```
