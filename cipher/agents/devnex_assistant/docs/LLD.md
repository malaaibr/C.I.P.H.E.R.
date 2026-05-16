# DevNex Assistant Low-Level Design

> **Document revision:** Sprint 0 complete (2026-05-16) — incorporates gap fixes F-001 … F-010,
> UC 3.1 ASIL Code Review, UC 4.1 Standards Q&A, UC 4.4 RAM Overlap Detection,
> and all supporting infrastructure changes.

---

## 1. Class Catalog

### 1.1 Core — Orchestration

#### `NodeResult`
- **File:** `core/orchestrator.py`
- **Type:** `dataclass`
- **Responsibility:** Immutable result record emitted by every node handler.
- **Attributes:**
  - `node_id: str` — V-cycle node identifier (e.g. `"S1N1"`)
  - `status: str` — `"complete"` | `"aborted"` | `"error"`
  - `output: str` — raw LLM response or human-review message
  - `artifacts: list[str]` — paths of files written by this node
  - `errors: list[str]` — non-fatal warnings collected during execution

#### `DevNexOrchestrator`
- **File:** `core/orchestrator.py`
- **Responsibility:** Central V-cycle pipeline coordinator. Owns all 13 node handlers plus UC extensions.
- **Stateful attributes:**

  | Attribute | Type | Initialised | Purpose |
  |---|---|---|---|
  | `run_context` | `DevNexRunContext` | `__init__` | Run metadata and artifact root |
  | `on_log` | `Callable` | `__init__` | Callback for structured log lines |
  | `on_node_started` | `Callable` | `__init__` | Callback fired before each node |
  | `on_node_complete` | `Callable` | `__init__` | Callback fired after each node |
  | `on_human_review` | `Callable` | `__init__` | Callback/gate for human approval |
  | `progress_callback` | `Callable\|None` | `__init__` | Optional progress reporting |
  | `state_store` | `StateStore` | `__init__` | Persists node statuses |
  | `config_store` | `ConfigStore` | `__init__` | Reads/writes project config |
  | `config` | `dict` | `__init__` via `ConfigStore.load()` | Active config snapshot |
  | `_gca_invoker` | `DevNexGCAInvoker\|None` | Lazy — first `gca_invoker` access | GCA/VS Code bridge |
  | `_artifacts_dir` | `Path` | `__init__` | Root for all node output files |
  | `_ruleset` | `dict\|None` | `_load_ruleset()` on demand | Critical-glob and gate config |

- **Key methods (Sprint 0 additions shown with ★):**

  | Method | Description |
  |---|---|
  | `gca_invoker` (property) | Lazy-creates `DevNexGCAInvoker`; pre-seed `_gca_invoker` in tests to bypass WebSocket import |
  | `run_node(node_id)` | Dispatches to `_run_s*N*()` handler; raises `NodeExecutionError` for unknown IDs |
  | `run_all(progress_callback)` | Sequential S1N1→S9N1 pipeline |
  | `run_workflow(workflow_path, inputs)` ★ | F-008 — bridges `WorkflowEngine` for AF.json graph execution |
  | `_invoke_with_retry(prompt, files, node_id)` ★ | F-002 — retries GCA up to `config["max_gca_retries"]` (default 3); raises `NodeExecutionError` after all attempts |
  | `_run_s1n1()` | LLD generation; validates config (F-010 workspace check); raises `ArtifactMissingError` if any input file absent (F-005) |
  | `_run_s1n2_review()` | Human gate — RM upload approval |
  | `_run_s1n3_review()` | Human gate — ID extraction approval |
  | `_run_s1n4()` | Requirement categorisation; loads `categorize_reqs_v1.md` (F-006); raises `ArtifactMissingError` if `SWC_nameInspBaseLLD` missing (F-005) |
  | `_run_s2n1()` | Code-linking stage |
  | `_run_s2n2_review()` | Human gate — annotated source review |
  | `_run_s3n1()` | Writes **`LLD_Code_Trace_Matrix.csv`** (F-001); loads `lld_code_trace_v1.md` (F-007) |
  | `_run_s4n1()` | Writes **`HLD_LLD_Trace_Matrix.csv`** (F-001); loads `hld_lld_links_v1.md` (F-007) |
  | `_run_s5n1()` | Writes **`Full_Downstream_Trace.csv`** (F-001) |
  | `_run_s6n1()` through `_run_s9n1()` | Testing, UTD, final traceability nodes |
  | `_load_ruleset()` ★ | F-009 — reads `configs/ruleset.yaml`; returns empty dict on missing file |
  | `_enforce_critical_globs()` ★ | F-009 — warns (does not raise) when workspace lacks files matching `critical_globs` patterns; uses `pattern.removeprefix("**/")` to extract the rglob suffix correctly |
  | `_validate_config(keys)` | Raises `ConfigValidationError` on empty/missing keys |
  | `_load_prompt(filename)` | Reads `prompts/{filename}`; returns `[not found]` fallback |
  | `_render_prompt(template, context)` | Replaces `{{KEY}}` placeholders |
  | `_default_human_review(node_id, message)` | Blocks on `input()` for CLI; catches `EOFError` and returns `False` |

- **Bug fix in Sprint 0:**
  `_enforce_critical_globs` previously called `workspace.rglob(pattern.lstrip("**/"))`.
  `str.lstrip` treats its argument as a *character set*, so `"**/*.c".lstrip("**/")` stripped
  `*`, `/` characters producing `".c"` — matching nothing.
  Fixed to `pattern.removeprefix("**/")` which strips the two-char-slash prefix as a string,
  yielding `"*.c"`.

---

#### `DevNexRunContext`
- **File:** `core/run_context.py`
- **Type:** Pydantic `BaseModel`
- **Attributes:** `run_id`, `start_time`, `swc_name`, `workspace_path`, `run_dir`
- **Methods:**
  - `set_default_run_dir()` — sets `~/.devnex/runs` when `run_dir` is absent
  - `get_artifacts_path()` — returns `run_dir / run_id`
  - `validate_workspace()` ★ — F-010: raises `ConfigValidationError` if `workspace_path`
    does not exist or is not a directory; called from `_run_s1n1()`
- **Python 3.10 compat note:** `datetime.UTC` was introduced in Python 3.11.
  Module uses `try: from datetime import UTC except ImportError: UTC = timezone.utc`.

---

#### `WorkflowEngine`
- **File:** `core/workflow_engine.py`
- **Responsibility:** AF.json graph executor.
- **Supported `serviceId` values:**

  | serviceId | Behaviour |
  |---|---|
  | `logic.internal` | no-op (start/end nodes) |
  | `extension.llm.sendPrompt` | calls `gca_bridge.send_prompt(prompt, files)` |
  | `atomic.executionService` | `subprocess.run([script] + args)` |
  | `logic.humanReview` | calls `on_human_review(node_id, data)`; raises `WorkflowAbortedError` on rejection |

- **Methods:**
  - `execute(workflow_path, inputs)` — topological-sort → dispatch → return last LLM response
  - `_topological_sort(graph)` — Kahn's algorithm on `sourceHandle == "next"` edges
  - `_resolve_templates(data, outputs, inputs)` — replaces `{{nodeId.output.portId}}`
  - `_default_human_review(node_id, data)` — CLI `input()` fallback

---

### 1.2 Core — Context and Intent

#### `ParsedIntent`
- **File:** `core/intent_classifier.py`
- **Type:** `dataclass`
- **Attributes:** `intent_type`, `vcycle_stage`, `skill_id`, `entities: list[str]`, `confidence: float`

#### `IntentClassifier`
- **File:** `core/intent_classifier.py`
- **Sprint 0 fixes (F-003, F-004):**
  - `S1N[23]` combined regex split into two separate rules so `S1N3` maps to `vcycle_stage="S1N3"` not `"S1N2"`.
  - Added `free_form` fallback rule (skill_id `"free_form"`, type `FREE_FORM`).
  - Added `asil_review` trigger: `r"asil\s+review|code\s+review.*asil|uc\s*3\.1"`.
  - Added `standards_qa` trigger: `r"standards?\s+q|iso\s+262|misra|uc\s*4\.1"`.
  - Added `uc4_4` trigger: `r"uc\s*4\.4|memory\s+overlap|semantic\s+conflict"`.

#### `SkillRegistry`
- **File:** `core/skill_registry.py`
- **Sprint 0 (F-004):** `build_default()` now registers:
  - `"explain"` → `ExplainSkill`
  - `"free_form"` → `FreeFormSkill`
  - `"asil_review"` → `AsilReviewSkill`
  - `"standards_qa"` → `StandardsQASkill`
  - (plus the original 5 stage-mapped skills)

---

### 1.3 Core — Errors

**File:** `core/errors.py`

| Exception | Inherits | Raised When |
|---|---|---|
| `DevNexError` | `Exception` | Base class |
| `NodeExecutionError` | `DevNexError` | Unknown node ID; GCA exhausted all retries (F-002) |
| `WorkflowAbortedError` | `DevNexError` | Human review rejected |
| `ConfigValidationError` | `DevNexError` | Missing/empty required config key; invalid workspace path (F-010) |
| `ArtifactMissingError` | `DevNexError` | Required input file absent at node start (F-005) |
| `SemanticConflictError` | `DevNexError` | ASIL-D hard block — critical violations in code review (UC 3.1) |

---

### 1.4 Core — Logging

**File:** `core/console_logging.py`

- `utc_timestamp()` — UTC string `YYYY-MM-DDTHH:MM:SSZ`
- `format_console_log(module, level, message, timestamp, function_name)` — ANSI-coloured structured log line; degrades gracefully when stdout is not a TTY
- `_supports_color()` — checks `NO_COLOR` / `FORCE_COLOR` env vars and Windows VT mode
- **Python 3.10 compat:** `try: from datetime import UTC except ImportError: UTC = timezone.utc`

---

### 1.5 Persistence

#### `ConfigStore` — `persistence/config_store.py`
- `load()` — reads `generated_artifacts/config.json`; merges over `DEFAULT_CONFIG`; returns defaults on missing/invalid JSON
- `save(config)` — creates parent dirs and writes JSON

#### `StateStore` — `persistence/state_store.py`
- `load()` / `save(state)` — JSON at `~/.devnex/workflow_state.json`
- `set_node_status(node_id, status)` — unlocked read-modify-write (known risk: no file lock)
- `get_node_statuses()`, `reset()`

#### `ArtifactWriter` — `persistence/artifact_writer.py`
- Generic `write_text()`, `write_json()`, `read_text()` helpers
- Note: orchestrator writes artifacts directly rather than through this helper

---

### 1.6 GCA Integration

#### `DevNexBridge` — `gca/bridge.py`
- `send_prompt(prompt, attached_files)` → `POST http://127.0.0.1:37778/sendPrompt`
- `is_available()` → `GET /health`
- Raises `GCANotAvailableError` on connection failure; `GCABridgeError` on HTTP/empty/timeout errors

#### `GCAInvocationResult` — `gca/vscode_invoker.py`
- `raw_response: str`, `is_response_valid: bool`, `started_vscode_window: bool`

#### `_DirectGCAClient` — `gca/vscode_invoker.py`
- Owns WebSocket lifecycle
- Commands: `gca.resetChat`, `vscode.closeAllFiles`, `vscode.openFile`, `gca.addFileToContext`, `gca.sendPrompt`

#### `DevNexGCAInvoker` — `gca/vscode_invoker.py`
- Creates isolated temp VS Code workspace
- Polls `~/.gca_instances.json`; connects WebSocket
- Falls back to HTTP bridge on registry/WebSocket failure
- **Test note:** lazy import of `websocket` module occurs in `gca_invoker` property.
  In unit tests, pre-seed `orch._gca_invoker = MagicMock()` to bypass the import.

---

### 1.7 Skills Layer

#### Base

| Class | File | Description |
|---|---|---|
| `ISkill` | `skills/base_skill.py` | Abstract base; injected `orchestrator` |
| `TaskResult` | per-skill | Dataclass carrying `success`, `output`, `artifacts` |

#### Original V-Cycle Skills

| Skill | Maps To Nodes |
|---|---|
| `LLDGenSkill` | S1N1, S1N2, S1N3, S1N4 |
| `CodeLinkSkill` | S2N1, S2N2 |
| `TraceReportSkill` | S3N1, S4N1, S5N1 |
| `TestGenSkill` | S6N1, S7N1, S8N1 |
| `FullTraceSkill` | S9N1 |

#### Sprint 0 New Skills

##### `ExplainSkill` — `skills/explain_skill.py`
- Intent trigger: `EXPLAIN`
- Builds a one-shot GCA prompt: "Explain `{target}` in the context of SWC `{swc}`"
- Returns `GCAInvocationResult.raw_response`

##### `FreeFormSkill` — `skills/free_form_skill.py`
- Intent trigger: `FREE_FORM` (fallback for unmatched input)
- Prepends a CIPHER DevNex system header then forwards the raw prompt to GCA

##### `AsilReviewSkill` — `skills/automotive/asil_review_skill.py` (UC 3.1)
- **Three-phase pipeline:** Ollama TRIAGE → Gemini CLI PLAN → GCA CODE_GEN
- **Key dataclasses:**
  - `AsilViolation`: `file`, `line`, `rule`, `severity` (CRITICAL|MAJOR|MINOR), `description`, `fix_hint`, `fixed: bool`
  - `AsilReviewReport`: `source_file`, `asil_target`, `total_violations`, `critical_count`, `major_count`, `minor_count`, `violations`, `fix_diffs`, `gate_decision`, `compliance_badge`, `rationale`
- **MISRA-C:2012 mandatory rules enforced:** R1.3, R11.3, R11.8, R14.4, R15.5, R17.7, R21.3
- **ASIL gate decisions:**

  | ASIL | Has Criticals | Decision | Gate |
  |---|---|---|---|
  | D | Yes | `HARD_BLOCK` — raises `SemanticConflictError` | G5 |
  | C | Yes | `HOLD` | G5 |
  | B | Yes | `HOLD` | G4 |
  | A / QM | Any | `WARN` | G3 |
  | Any | No | `PASS` | — |

- **Artifacts written:** `asil_review_{stem}.json`, `asil_review_{stem}.md`
- **GCA response parsing:** splits on `"---DIFF---"` separator for fix diffs

##### `StandardsQASkill` — `skills/automotive/standards_qa_skill.py` (UC 4.1)
- **Hybrid RAG:** BM25 (sparse) + Qdrant (dense)
- **`HybridRetriever`:**
  - `_bm25_search(query)` — `rank_bm25.BM25Okapi` or naive TF fallback
  - `_dense_search(query)` — Qdrant REST `/collections/{index}/points/search`
  - `_embed_query(query)` — Ollama `/api/embeddings` (model: `nomic-embed-text`)
  - `retrieve(query, index_key, top_k)` — merges by `doc_id`; `hybrid_score = alpha×dense + (1-alpha)×bm25`; `DEFAULT_ALPHA = 0.7`, `DEFAULT_TOP_K = 5`
  - `_qdrant_ok: bool | None` — tracks availability; falls back gracefully to BM25-only
- **`SourceChunk`:** `doc_id`, `text`, `source`, `dense_score`, `bm25_score`, `hybrid_score`
- **`QAAnswer`:** `question`, `answer`, `sources: list[SourceChunk]`, `index_used`, `top_k`
- **Supported index keys:** `"iso26262"`, `"misra_c"`, `"autosar"`, `"codebase"`
- **`answer(question, scope_filter)` flow:** retrieve chunks → build context → Ollama `/api/generate` → `QAAnswer`; `_fallback_answer()` when no docs indexed

---

### 1.8 UC 4.4 — RAM Overlap Detection

All files under `skills/uc4_4/`.

#### `MapAnalyzer` — `map_analyzer.py`
- Parses GNU linker `.map` files into `SectionLayout` records: `name`, `vma`, `lma`, `size`, `alignment`
- `parse(map_path)` → `list[SectionLayout]`
- `write_json(sections, out_path)` — atomic write via temp-file + rename
- `get_ram_sections()` — filters to sections with RAM-range VMAs

#### `RamOverlapDetector` — `ram_overlap_detector.py`
- `detect(sections)` → `list[OverlapResult]` — interval-intersection algorithm
- `OverlapResult`: `section_a`, `section_b`, `overlap_start`, `overlap_end`, `overlap_bytes`, `asil_level`, `action`
- **ASIL action table:**

  | ASIL | Action |
  |---|---|
  | D | `HARD_BLOCK` — raises `SemanticConflictError` via `AsilGate.enforce()` |
  | C | `HOLD` |
  | B | `HOLD` |
  | A / QM | `WARN` |

#### `LinkerScriptParser` — `linker_script_parser.py`
- Parses GNU `.ld` linker scripts for `MEMORY { }` regions
- `MemoryRegion`: `name`, `origin`, `length`, `attrs`
- `is_ram(region)`, `is_flash(region)` — attribute-based classification

#### `AsilGate` — `asil_gate.py`
- `evaluate(asil_level, has_overlap)` → `GateDecision`: `decision` (HARD_BLOCK/HOLD/WARN/PASS), `gate` (G1–G5), `requires_safety_engineer: bool`
- `enforce(asil_level, overlap_results)` — raises `SemanticConflictError` for ASIL-D with overlaps
- Gate G5 assigned to ASIL-D; G4 to ASIL-C; G3 to ASIL-A/B/QM

---

### 1.9 Configuration

#### `configs/ruleset.yaml` ★ (F-009)
```yaml
version: "1.0"
critical_globs:
  - "**/*.c"
  - "**/*.h"
  - "**/*.ld"
  - "**/*.map"
exempt_patterns:
  - "generated_artifacts/**"
  - "build/**"
  - ".venv/**"
asil_gated_nodes:
  - S1N1
  - S6N1
  - S9N1
  - UC4_4
max_gca_retries: 3
```

---

### 1.10 Prompt Templates

| File | Used By | Sprint |
|---|---|---|
| `prompts/lld_gen_v1.md` | S1N1 | Pre-Sprint 0 |
| `prompts/code_link_v1.md` | S2N1 | Pre-Sprint 0 |
| `prompts/full_trace_v1.md` | S9N1 | Pre-Sprint 0 |
| `prompts/categorize_reqs_v1.md` ★ | S1N4 (F-006) | Sprint 0 |
| `prompts/lld_code_trace_v1.md` ★ | S3N1 (F-007) | Sprint 0 |
| `prompts/hld_lld_links_v1.md` ★ | S4N1 (F-007) | Sprint 0 |

---

## 2. Standalone Function Catalog

| Function | File | Role |
|---|---|---|
| `cli()` | `devnex.py` | Click root command |
| `main()` | `main_gui.py` | PyQt6 entry point |
| `utc_timestamp()` | `core/console_logging.py` | UTC timestamp string |
| `format_console_log()` | `core/console_logging.py` | Structured ANSI log line |
| `_try_enable_windows_vt_mode()` | `core/console_logging.py` | Windows ANSI console enable |
| `load_trace_graph(artifacts_dir)` | `core/trace_loader.py` | Builds `TraceGraph` from JSON or CSVs |
| `emit_trace_json(artifacts_dir)` | `core/trace_loader.py` | Writes `trace_graph.json` atomically |
| `_make_orchestrator()` | `interfaces/cli/cli_commands.py` | Creates `DevNexRunContext` + orchestrator |
| `build_cli()` | `interfaces/cli/cli_commands.py` | Builds Click command group |
| `launch_app()` | `interfaces/gui/app.py` | GUI bootstrap sequence |

---

## 3. Artifact Filename Contract (F-001)

The canonical output names are enforced so `trace_loader._CSV_MAP` can locate them without config:

| Node | Old (pre-Sprint 0) | Canonical (Sprint 0) |
|---|---|---|
| S3N1 | `LLD_Code_Trace_Report.csv` | **`LLD_Code_Trace_Matrix.csv`** |
| S4N1 | `HLD_LLD_Links.json` | **`HLD_LLD_Trace_Matrix.csv`** |
| S5N1 | `HLD_LLD_Code_Trace_Matrix.csv` | **`Full_Downstream_Trace.csv`** |

`trace_loader._CSV_MAP` keys match these canonical names exactly.

---

## 4. Main Call Graphs

### CLI Single Stage
```
devnex.cli() → build_cli() → run_stage()
  → _make_orchestrator() [DevNexRunContext + DevNexOrchestrator]
  → DevNexOrchestrator.run_node(stage)
    → run_context.validate_workspace()        [F-010]
    → _load_ruleset() + _enforce_critical_globs()  [F-009]
    → selected _run_s*N*() handler
      → _invoke_with_retry(prompt, files, node_id)  [F-002]
        → gca_invoker.invoke_prompt()
    → StateStore.set_node_status()
```

### AF.json Workflow Bridge (F-008)
```
DevNexOrchestrator.run_workflow(workflow_path, inputs)
  → WorkflowEngine(gca_bridge=self.gca_invoker, ...)
  → WorkflowEngine.execute(workflow_path, inputs)
    → _topological_sort()
    → for node in ordered:
        _resolve_templates()
        dispatch by serviceId
```

### UC 3.1 ASIL Review Pipeline
```
AsilReviewSkill.run(source_file, asil_level)
  → Phase 1: Ollama TRIAGE  → violation JSON list
  → Phase 2: Gemini CLI PLAN → fix plan per violation
  → Phase 3: GCA CODE_GEN   → fix diffs (split on "---DIFF---")
  → AsilGate.enforce(asil_level, violations)
    → ASIL-D + criticals → raise SemanticConflictError
  → write asil_review_{stem}.json + asil_review_{stem}.md
```

### UC 4.1 Standards Q&A
```
StandardsQASkill.answer(question, scope_filter)
  → HybridRetriever.retrieve(query, index_key, top_k)
    → _embed_query() [Ollama nomic-embed-text]
    → _dense_search() [Qdrant REST] || _bm25_search() [BM25Okapi]
    → merge by doc_id, compute hybrid_score
  → _generate_answer(question, chunks) [Ollama /api/generate]
  → QAAnswer(question, answer, sources, ...)
```

### UC 4.4 RAM Overlap Detection
```
run_uc4_4_semantic_check(config)
  → MapAnalyzer.parse(map_path)
  → MapAnalyzer.get_ram_sections()
  → RamOverlapDetector.detect(sections)
  → AsilGate.enforce(asil_level, overlap_results)
    → ASIL-D + overlap → raise SemanticConflictError
  → write layout.json + overlap_report.json + gate_decision.json
```

---

## 5. Data Transformation Traces

### S1N1 — LLD Generation
Input config keys: `SWC_name`, `G_SWDD_TEMP`, `SWC_name_C`, `SWC_name_H`, `SWC_name_TEMP_LLD`, `SWC_name_HLD`, `lds_file`, `map_file`, `workspace_path`

1. `_validate_config()` checks all required keys
2. `run_context.validate_workspace()` ★ (F-010)
3. `_enforce_critical_globs()` ★ (F-009) — warns if `*.c`/`*.h`/`*.ld`/`*.map` absent
4. `_load_prompt("lld_gen_v1.md")` + `_render_prompt()`
5. Input files embedded or `[FILE NOT FOUND]`; raises `ArtifactMissingError` on first missing required file ★ (F-005)
6. `_invoke_with_retry()` ★ (F-002) → GCA
7. Writes `{SWC}_TEMP_LLD_updated.csv`

### S1N4 — Requirement Categorisation
1. Validate `SWC_name`, `SWC_nameInspBaseLLD`
2. Raise `ArtifactMissingError` if `SWC_nameInspBaseLLD` missing ★ (F-005)
3. `_load_prompt("categorize_reqs_v1.md")` ★ (F-006)
4. `_invoke_with_retry()` → GCA
5. Writes `{SWC}_FUNC_req.csv`

### S3N1 — LLD-to-Code Traceability ★ (F-001, F-007)
1. `_load_prompt("lld_code_trace_v1.md")`
2. Attaches `updated_{SWC}.c` + `{SWC}_FUNC_req.csv`
3. `_invoke_with_retry()` → GCA
4. Writes **`LLD_Code_Trace_Matrix.csv`** (was `LLD_Code_Trace_Report.csv`)

### S4N1 — HLD-to-LLD Links ★ (F-001, F-007)
1. `_load_prompt("hld_lld_links_v1.md")`
2. Attaches HLD file + `{SWC}_FUNC_req.csv`
3. `_invoke_with_retry()` → GCA
4. Writes **`HLD_LLD_Trace_Matrix.csv`** (was `HLD_LLD_Links.json`)

### S5N1 — Full Downstream Trace ★ (F-001)
- Consumes `LLD_Code_Trace_Matrix.csv` + `HLD_LLD_Trace_Matrix.csv`
- Writes **`Full_Downstream_Trace.csv`** (was `HLD_LLD_Code_Trace_Matrix.csv`)

---

## 6. State and Mutation Map

| Component | Initialised | Mutated | Risk |
|---|---|---|---|
| `DevNexOrchestrator.config` | `__init__` | Direct assignment in tests | Stale in long-lived GUI orchestrator |
| `DevNexOrchestrator._gca_invoker` | First `gca_invoker` access | Set once lazily | Pre-seed `_gca_invoker` in tests |
| `DevNexOrchestrator._ruleset` | `_load_ruleset()` | Read-only after load | None |
| `StateStore` JSON | `load()` | `set_node_status()`, `reset()` | No file lock |
| `ConfigStore` JSON | `load()` | `save()` | Invalid JSON silently replaced |
| `MainWindow._orchestrator` | `_get_orchestrator()` | Reset on config save/reset | Callbacks re-wired by workers |
| `HybridRetriever._qdrant_ok` | `None` | Set on first Qdrant call | Sticky failure — won't retry Qdrant this session |

---

## 7. Error and Exception Map

| Exception | Raised At | Trigger |
|---|---|---|
| `NodeExecutionError` | `run_node()` | Unknown node ID |
| `NodeExecutionError` ★ | `_invoke_with_retry()` | GCA exhausted all retry attempts (F-002) |
| `WorkflowAbortedError` | review gates, `WorkflowEngine` | Human rejected |
| `ConfigValidationError` | `_validate_config()` | Missing/empty config key |
| `ConfigValidationError` ★ | `validate_workspace()` | `workspace_path` absent or not a dir (F-010) |
| `ArtifactMissingError` ★ | `_run_s1n1()`, `_run_s1n4()` | Required input file not on disk (F-005) |
| `SemanticConflictError` ★ | `AsilGate.enforce()` | ASIL-D overlap or ASIL-D critical violation |
| `GCANotAvailableError` | `bridge.py` | Connection failure |
| `GCABridgeError` | `bridge.py` | HTTP/empty/timeout response |

---

## 8. Test Coverage Map

| Test File | Components Covered | Tests |
|---|---|---|
| `tests/test_config_store.py` | `ConfigStore` | 4 |
| `tests/test_state_store.py` | `StateStore` | 5 |
| `tests/test_gca_bridge.py` | `DevNexBridge` | 6 |
| `tests/test_orchestrator.py` | `DevNexOrchestrator` core paths | 9 |
| `tests/test_trace_model.py` | `TraceGraph`, `trace_loader`, `emit_trace_json` | 17 |
| `tests/test_sprint0_fixes.py` ★ | F-001…F-010 regressions | 21 |
| `tests/test_asil_review.py` ★ | `AsilReviewSkill`, `AsilGate` (UC 3.1) | 20 |
| `tests/test_standards_qa.py` ★ | `StandardsQASkill`, `HybridRetriever` (UC 4.1) | 23 |
| `tests/test_uc4_4.py` ★ | `MapAnalyzer`, `RamOverlapDetector`, `LinkerScriptParser`, `AsilGate` (UC 4.4) | 64 |
| **Total** | | **169 / 169 passing** |

---

## 9. Known Risks (Post Sprint 0)

| Risk | Severity | Mitigation |
|---|---|---|
| `StateStore` has no file lock | Medium | Single-process use; lock planned for Sprint 2 |
| `DevNexGCAInvoker` requires `websocket-client` package | Low | Guard with `try/except ImportError`; mock in tests |
| `rglob` on FUSE-mounted Windows paths may miss files | Low | `touch` modifies mtime; `removeprefix` fix removes char-set stripping |
| Qdrant optional — BM25 fallback only | Low | `_qdrant_ok` flag prevents repeated failed calls |
| `_default_human_review` blocks on `input()` in CI | Medium | Override `on_human_review` callback; CI passes `lambda: True` |
