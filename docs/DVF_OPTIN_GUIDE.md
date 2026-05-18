---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# DVF Opt-In Guide (S2N1 … S9N1 and beyond)

After Sprint 8, every LLM-touching orchestrator node can opt into the
Draft-Verify-Finalize loop with a **3-line change** plus a **single v2 prompt file**.

## Mechanism

[`DevNexOrchestrator._maybe_invoke_via_dvf`](../cipher/agents/devnex_assistant/core/orchestrator.py)
is a generic helper that:

1. Checks `config["enable_dvf"]` and the optional `config["dvf_nodes"]` allowlist.
2. Loads the v2 (citation-aware) prompt for the node.
3. Runs `run_with_dvf(...)` → validated CRC + IssueReports.
4. Calls a node-specific renderer to produce the artifact text.
5. Returns a `NodeResult` to the caller. On any failure the helper returns
   `None`, so the node falls back to its legacy `_invoke_with_retry` path —
   opt-in **never** regresses legacy behaviour.

## To opt-in a node (worked example for S2N1)

### 1. Create the v2 prompt

Put a CRC-producing prompt at:

```
cipher/agents/devnex_assistant/prompts/code_link_v2.md
```

It should instruct the LLM to emit a `cipher.cap.crc.v1` chain whose steps cite
URIs from the attached input files. Use `lld_gen_v2.md` as the canonical model.

### 2. (Optional) Write a tailored renderer

If the node's artifact isn't a generic JSON dump of the CRC, add a renderer:

```python
def render_annotated_c_from_crc(crc, swc: str) -> str:
    # Walk crc.steps and emit annotated C source.
    ...
```

If you skip this, `_render_crc_as_json` is the default — fine for trace
matrices, debug dumps, anything JSON-shaped.

### 3. Add 3 lines at the top of the node method

```python
def _run_s2n1(self) -> NodeResult:
    ...
    out_path = self._artifacts_dir / f"updated_{swc}.c"

    dvf_result = self._maybe_invoke_via_dvf(
        node_id="S2N1",
        base_prompt=prompt,
        attached_files=[source_file, func_req_file],
        swc=swc,
        out_path=out_path,
        v2_prompt_basename="code_link_v2.md",
        v2_template_context=path_context_with_content(self.config, content_sections),
        render_artifact=render_annotated_c_from_crc,  # or omit for default
    )
    if dvf_result is not None:
        return dvf_result

    # ... existing legacy path unchanged ...
```

### 4. Enable it in config

```json
{
  "enable_dvf": true,
  "dvf_nodes": ["S1N1", "S2N1"],     // omit this key to enable for ALL nodes
  "max_revisions": 3,
  "domain_pack": "iso26262_asil_b"
}
```

## Status today (post-Sprint 8)

| Node | v2 prompt | Custom renderer | Opted-in |
|------|-----------|-----------------|----------|
| S1N1 | ✅ `lld_gen_v2.md` | ✅ `render_csv_from_crc` | ✅ |
| S1N4 | ⬜ `categorize_reqs_v2.md` (TODO) | ⬜ | ⬜ |
| S2N1 | ⬜ `code_link_v2.md` (TODO) | ⬜ | ⬜ |
| S3N1 | ⬜ `lld_code_trace_v2.md` (TODO) | ⬜ | ⬜ |
| S4N1 | ⬜ `hld_lld_links_v2.md` (TODO) | ⬜ | ⬜ |
| S5N1 | ⬜ `full_trace_v2.md` (TODO) | ⬜ | ⬜ |
| S6N1 | ⬜ — | ⬜ | ⬜ |
| S7N1 | ⬜ — | ⬜ | ⬜ |
| S8N1 | ⬜ — | ⬜ | ⬜ |
| S9N1 | ⬜ — | ⬜ | ⬜ |

The **wiring** is complete; turning each row green is a prompt-engineering
task, not a code task.

## Why not just enable everywhere now?

The v2 prompts have to be authored carefully — each node has a different
output shape (CSV, annotated C, trace matrix, test specs, …) and different
ASPICE-phase claim-kind constraints. Shipping mediocre v2 prompts would
trigger needless HITL escalations and harm trust in DVF. Keep the legacy
path until each prompt is ready.

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
