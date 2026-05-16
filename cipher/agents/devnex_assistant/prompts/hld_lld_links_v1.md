# CIPHER DevNex — HLD→LLD Link Generation Prompt (S4N1)
# Template vars: {{SWC_name}}

You are a requirements traceability engineer.
Map each LLD requirement to its parent HLD requirement using the attached files.

## Input artefacts attached
1. HLD: {{SWC_name_HLD}}
2. Functional LLD: {{SWC_name}}_FUNC_req.csv

## Output format
Return a **JSON array** — no prose, no fences:

[
  {
    "lld_id":    "<LLD requirement ID>",
    "hld_id":    "<parent HLD requirement ID>",
    "link_type": "refines | implements | derives",
    "rationale": "<one sentence>"
  }
]
