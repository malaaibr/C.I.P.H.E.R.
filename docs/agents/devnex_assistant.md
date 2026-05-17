# DevNex Assistant — Agent Specification

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | AGENT-DEVNEX-001 |
| Version | 1.0 |
| ASPICE Scope | SWE.3 (Software Detailed Design) + SWE.4 (Software Unit Verification) |
| Agent Name | `devnex_assistant` |
| Role | Primary V-cycle automation agent |
| Status | IMPLEMENTED (primary agent; non-stub) |
| Date | 2026-05-17 |
| Owner | CIPHER AAL Layer |
| Implementation Root | `cipher/agents/devnex_assistant/` |

---

## §1 Role & Capabilities

DevNex Assistant is the **only fully-implemented agent** in CIPHER's AAL layer (the other nine
slots are stubs per `docs/SESSION_HANDOFF.md` §1). It automates the embedded automotive
V-cycle from Software Detailed Design (SWE.3) through Software Unit Verification (SWE.4),
producing the ISO 26262 / ASPICE traceability chain `HLD → LLD → CODE → TEST → UTD`.

Concretely DevNex automates:

1. **LLD generation** from C/H sources, HLD inputs, and SWDD templates (S1N1).
2. **Requirement categorization** (Functional vs Non-Functional) from inspected LLD (S1N4).
3. **LLD-to-code linking** — embeds requirement references directly in `.c` sources (S2N1).
4. **Traceability matrix generation** — LLD→Code, HLD→LLD, downstream, and final (S3N1, S4N1, S5N1, S9N1).
5. **Test artifact generation** — VectorCAST `test.bat` scaffolding and UTD authoring (S6N1, S7N1, S8N1).
6. **ASIL code review** — UC 3.1 Phase 1–4 LLM-backed safety review (`test_asil_review.py`).
7. **Standards Q&A** — UC 4.1 hybrid RAG over IEC/ISO standards (`test_standards_qa.py`).
8. **Post-merge semantic memory-map overlap check** — UC 4.4 (`orchestrator.run_uc4_4_semantic_check`).
9. **Human review gates** — S1N2, S1N3, S2N2, S6N1 block via `threading.Event` until a
   reviewer approves in the GUI, preserving ASPICE's "joint review" expectation.

ASDLC reference: `docs/ASDLC.md` defines V-cycle phases that DevNex realises; `docs/CIPHER_LLD.md`
documents the AAL-layer contract DevNex implements via `TaskContract` / `TaskResult`.

---

## §2 V-cycle Node Mapping

The 13 nodes are dispatched by `DevNexOrchestrator.run_node()` (see
`core/orchestrator.py:214-242`). Status reflects what is wired and executable today.

| Node ID | UC Mapped | Input Artifact | Output Artifact | Status |
|---|---|---|---|---|
| S1N1 | LLD Generation (SWE.3) | `SWC_name_C`, `SWC_name_H`, `G_SWDD_TEMP`, `SWC_name_TEMP_LLD`, `SWC_name_HLD`, `lds_file`, `map_file` | `<SWC>_TEMP_LLD_updated.csv` | Implemented |
| S1N2 | Joint Review — upload to DOORS/ReqIF | LLD CSV (manual upload) | Approval flag | Implemented (human gate) |
| S1N3 | Joint Review — extract IDs from Req Mgmt | `<SWC>_LLD_withIDs.csv` (manual) | Approval flag | Implemented (human gate) |
| S1N4 | Requirement Categorization (SWE.3) | `SWC_nameInspBaseLLD` | `<SWC>_FUNC_req.csv` | Implemented |
| S2N1 | Code Annotation (SWE.3 → SWE.4 link) | `SWC_name_C`, `<SWC>_FUNC_req.csv` | `updated_<SWC>.c` | Implemented |
| S2N2 | Joint Review — annotated source inspection | `updated_<SWC>.c` | Approval flag | Implemented (human gate) |
| S3N1 | LLD→Code Traceability (SWE.3.BP6) | `updated_<SWC>.c`, `<SWC>_FUNC_req.csv` | `LLD_Code_Trace_Matrix.csv` | Implemented |
| S4N1 | HLD→LLD Linking (SWE.2/SWE.3 link) | `SWC_name_HLD`, `<SWC>_FUNC_req.csv` | `HLD_LLD_Links.json` + `HLD_LLD_Trace_Matrix.csv` | Implemented |
| S5N1 | Downstream Trace Matrix | `LLD_Code_Trace_Matrix.csv`, `HLD_LLD_Links.json` | `Full_Downstream_Trace.csv` | Implemented |
| S6N1 | Test Generation (SWE.4) | `updated_<SWC>.c`, `<SWC>_FUNC_req.csv` | `test.bat` + .TST wait gate | Partial — prompt is inline (no template), VectorCAST gate not E2E-tested |
| S7N1 | UTD Authoring (SWE.4) | `*.tst` files from workspace | `<SWC>_UTD.md` | Partial — inline prompt, depends on external VectorCAST output |
| S8N1 | UTD→LLD Linking (SWE.4.BP7) | `<SWC>_UTD.md`, `<SWC>_FUNC_req.csv` | `UTD_LLD_Links.json` | Partial — inline prompt, no dedicated template |
| S9N1 | Full Traceability Consolidation | `Full_Downstream_Trace.csv`, `UTD_LLD_Links.json` | `Full_Traceability_Matrix.csv` | Implemented (reuses `full_trace_v1.md`) |

**Aggregate:** 9 Implemented · 3 Partial (S6N1/S7N1/S8N1 — functional but inline-prompt and not E2E-validated) · 1 Implemented-with-caveat (S9N1 reuses S5N1's prompt template).
End-to-end execution against a real SWC has **not been validated** (see `SESSION_HANDOFF.md` §4.1).

### Cross-cutting orchestrator behaviours

The 13 node handlers share four resilience layers, all in `core/orchestrator.py`:

- **F-002 retry wrapper** (`_invoke_with_retry`, lines 136-166): every GCA call is retried up
  to `max_gca_retries` (default 3, read from config) on invalid response or exception.
- **F-005 artifact presence** — S1N1 and S1N4 raise `ArtifactMissingError` early rather
  than silently embedding `[FILE NOT FOUND]`.
- **F-009 critical_globs warning** — `_enforce_critical_globs` consults
  `configs/ruleset.yaml` and logs (does not raise) when expected workspace patterns are
  absent. Exempt patterns are honoured.
- **F-010 workspace validation** — `run_context.validate_workspace()` runs before S1N1
  resolves any relative path.

`run_all()` aborts the loop the moment a node returns `aborted` or `error` status; partial
artifacts up to that node remain on disk under `~/.devnex/runs/<run_id>/`.

---

## §3 Inputs / Outputs

### Inputs — TaskContract (consumed at AAL boundary)

DevNex consumes the standard `cipher.core.schemas.TaskContract`. Key fields used:

| Field | Use |
|---|---|
| `task_id` | Threaded into `DevNexRunContext.run_id` when invoked via A2A |
| `params.SWC_name` | Drives all artifact filenames |
| `params.workspace_path` | Validated by `DevNexRunContext.validate_workspace()` (F-010) |
| `params.SWC_name_C/_H/_HLD/_TEMP_LLD` | File path inputs for S1N1 |
| `params.G_SWDD_TEMP`, `lds_file`, `map_file` | LLD template + linker scripts |
| `params.SWC_nameInspBaseLLD` | Required by S1N4 |
| `params.max_gca_retries` | Read by `_invoke_with_retry` (F-002, default 3) |
| `params.asil_level` | Used by UC 4.4 ASIL gate |

Direct CLI / GUI invocation bypasses `TaskContract` and reads `ConfigStore` (`generated_artifacts/config.json`).

### Outputs — TaskResult

Each node returns a `NodeResult` (`core/orchestrator.py:56-66`):

```
node_id: str          # e.g. "S1N1"
status:  str          # "complete" | "aborted" | "error"
output:  str          # raw LLM response or human-review message
artifacts: list[str]  # absolute paths to written files
errors:    list[str]
```

These are aggregated into a `TaskResult` for A2A return.

### `DevNexRunContext` fields (`core/run_context.py`)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `run_id` | `str` (uuid4) | auto | Per-run correlation ID |
| `start_time` | `datetime` (UTC) | auto | Run start timestamp |
| `swc_name` | `str` | `""` | SWC under analysis |
| `workspace_path` | `Path` | `cwd` | Validated dir for relative path resolution |
| `run_dir` | `Path \| None` | `~/.devnex/runs` | Parent of per-run artifact dirs |

Helpers: `validate_workspace()` (F-010) and `get_artifacts_path()` returning `run_dir / run_id`.

---

## §4 Prompts Catalog

Located in `cipher/agents/devnex_assistant/prompts/`. Loaded via `_load_prompt(filename)` and
substituted with `{{key}}` variables from `self.config` (`_render_prompt`).

| Prompt File | Consumed By Node | Purpose |
|---|---|---|
| `lld_gen_v1.md` | S1N1 | Generate updated LLD CSV from C/H + HLD + SWDD template |
| `categorize_reqs_v1.md` | S1N4 | Split LLD requirements into Functional vs Non-Functional (F-006) |
| `code_link_v1.md` | S2N1 | Embed `@req <ID>` annotations into source `.c` file |
| `lld_code_trace_v1.md` | S3N1 | Produce LLD→Code traceability matrix (F-007) |
| `hld_lld_links_v1.md` | S4N1 | Map LLD items to parent HLD requirements (F-007) |
| `full_trace_v1.md` | S5N1 **and** S9N1 | Consolidate downstream / full matrix (reused) |

**Gap:** No dedicated prompt templates for S6N1, S7N1, S8N1 — those nodes carry their prompts
inline in `orchestrator.py` (lines 552-556, 587-591, 607-610). Authoring `test_gen_v1.md`,
`utd_gen_v1.md`, `utd_lld_links_v1.md` is an open item (see §9).

---

## §5 GUI Integration

The DevNex workspace (Mode 1 in the unified main window) hosts **five panels** wired to the
orchestrator via the worker pattern described in `docs/layers/GUI_LLD.md` (QThread + signals;
not duplicated here).

| Panel (`interfaces/gui/panels/`) | Role | Orchestrator Wiring |
|---|---|---|
| `workflow_panel.py` | V-cycle canvas; Run / Run-All / Pause buttons per node | Creates `NodeWorker` / `FullRunWorker`; subscribes to `node_started`, `node_complete`, `progress` |
| `trace_panel.py` (+ `trace_filter_bar.py`, `trace_graph_canvas.py`, `trace_node_card.py`) | 5-column `HLD→LLD→CODE→TEST→UTD` graph; `QFileSystemWatcher` auto-reloads `trace_graph.json` | Read-only — consumes artifacts from `~/.devnex/runs/<run_id>/`. See `README_TRACE_PANEL.md` |
| `review_panel.py` | Renders human-review dialogs for S1N2, S1N3, S2N2, S6N1 | Calls `worker.resume(approved)` which releases the worker's `threading.Event` |
| `output_log.py` | Tail of `on_log(message, level)` events | Subscribes to `NodeWorker.log_line` |
| `config_panel.py` | SWC config editor; includes "Import Config" button (per `SESSION_HANDOFF.md` §2.4) | Persists via `ConfigStore`; orchestrator is lazily created on first `Run` so config is loaded |

**Workers (`interfaces/gui/workers/`):**

- `base_worker.py` — common QThread skeleton
- `node_worker.py` — single-node executor; emits `log_line`, `node_started`, `node_complete`, `review_needed`, `error_occurred`
- `full_run_worker.py` — runs all 13 nodes sequentially with progress signal
- `review_worker.py` — drives the separate UC 3.1 `TechReviewOrchestrator` (R1N1…R9N1 pipeline) — distinct from V-cycle nodes

Human-review gates use `threading.Event.wait()` on the worker QThread so the GUI thread
remains responsive (see `node_worker.py:41-46`).

---

## §6 Persistence

| Store | Location | Module | Purpose |
|---|---|---|---|
| `ConfigStore` | `generated_artifacts/config.json` | `persistence/config_store.py` | SWC paths, workspace path, retry counts, ASIL level |
| `StateStore` | `~/.devnex/workflow_state.json` | `persistence/state_store.py` | Per-node `status` (complete / aborted / error) across runs |
| Run artifacts | `~/.devnex/runs/<run_id>/` | `DevNexRunContext.get_artifacts_path()` | All node outputs for one V-cycle run |
| GUI settings | `~/.devnex/gui_settings.json` | (legacy direct file) | Window geometry, panel layout |
| GCA registry | `~/.gca_instances.json` | `gca/vscode_invoker.py` | Active GCA workspace instances |

All on-disk state is JSON — no DB. ConfigStore validation is gated by `_validate_config`
and `ConfigValidationError`.

---

## §7 Dependencies

| Layer | Component | Used For |
|---|---|---|
| **TRF** | LLM Gateway (`cipher.trf.gateway`) | DevNex first tries GCA via WebSocket, then falls back to DevNex Bridge HTTP (`:37778`), and ultimately to Ollama via TRF |
| **MKF** | Hybrid RAG retriever | UC 4.1 Standards Q&A (`test_standards_qa.py`) — BM25 + sentence-transformers fusion over IEC/ISO chunks |
| **GCL** | OPA + audit journal + `gcl.asil_gate` | UC 4.4 hard-block on `SemanticConflictError`; ASIL-D enforcement |
| **ARE** | A2A Server + `SkillLoader` | DevNex skills (UC 3.1, UC 4.1, UC 4.4) registered for A2A inbound invocation |
| **Core** | `cipher.core.schemas.TaskContract`, `AgentCard` | Inbound contract; adapters (Redis, Qdrant, MinIO) optional for artifact replication |
| **External** | VS Code CLI (`code`/`code.cmd`), DevNex Bridge VSIX | GCA invocation transport |

The `gca.vscode_invoker.DevNexGCAInvoker` is **lazy-initialised** (orchestrator property at
line 116-121) so smoke imports do not require VS Code.

---

## §8 Tests

Located in `cipher/agents/devnex_assistant/tests/`:

| Test File | Purpose |
|---|---|
| `test_config_store.py` | Round-trip JSON persistence and ConfigValidationError paths |
| `test_state_store.py` | Per-node status persistence across orchestrator instances |
| `test_gca_bridge.py` | DevNex Bridge HTTP relay behaviour (fallback path when WebSocket fails) |
| `test_orchestrator.py` | Selected orchestrator paths — node dispatch, prompt rendering, helpers |
| `test_trace_model.py` | CSV→TraceGraph happy paths, missing files, JSON round-trip, `emit_trace_json` |
| `test_asil_review.py` | UC 3.1: ASIL violation parsing, 4-phase review pipeline, gate enforcement, report writing |
| `test_standards_qa.py` | UC 4.1: hybrid retriever (BM25 + dense), score fusion, citation format |
| `test_uc4_4.py` | UC 4.4: post-merge memory-map overlap detection (DMA-buffer canonical scenario) |
| `test_sprint0_fixes.py` | Regression matrix for fixes F-001 through F-010 |

Run with `python -m pytest` from the agent root. No coverage target is currently asserted.

---

## §9 Open Items

Gaps surfaced from `docs/SESSION_HANDOFF.md` §4 and direct code reading:

1. **End-to-end V-cycle execution not validated** (`SESSION_HANDOFF.md` §4.1) — orchestrator
   wiring is smoke-tested but no node has been run against a real SWC workspace with live
   GCA/Ollama.
2. **S6N1/S7N1/S8N1 use inline prompts** — no `test_gen_v1.md`, `utd_gen_v1.md`,
   `utd_lld_links_v1.md`. Promote to template files for parity with S1–S5.
3. **S9N1 reuses `full_trace_v1.md`** — should have a dedicated `full_traceability_v1.md`
   that explicitly consumes both `Full_Downstream_Trace.csv` and `UTD_LLD_Links.json`.
4. **CipherOrchestrator not wired as parent** (`SESSION_HANDOFF.md` §4.3) — DevNex is
   created independently in `main_window.py` rather than via
   `CipherOrchestrator.register_child("devnex", devnex_orch)`.
5. **`cipher/agents/devnex/` adapter ambiguity** (`SESSION_HANDOFF.md` §4.4) — the legacy
   `DevNexAdapter` / `S1N1Skill` folder coexists with the canonical `devnex_assistant/`;
   intent is to keep it as the A2A bridge but ownership of `S1N1Skill` is unresolved.
6. **TaskContract round-trip incomplete** — CLI/GUI paths read `ConfigStore` directly;
   A2A inbound path needs a documented mapping `TaskContract.params → ConfigStore` so the
   two invocation modes converge.
7. **Voice integration absent** (`SESSION_HANDOFF.md` §4.2) — `voice_panel.py` widgets exist
   but no TTS/STT backend is wired (out of agent scope, but affects DevNex UX in Mode 1).
8. **`_default_human_review` falls back to `input()`** — acceptable for CLI, but a
   misconfigured GUI run could land on a stdin-blocked thread. Consider raising instead.
9. **Workflow engine bridge (`run_workflow`, F-008)** is wired but no AF.json graphs ship
   with the agent — feature is dormant until graph definitions are authored.
10. **No `__init__.py` audit** (`SESSION_HANDOFF.md` §4.5) — package imports work today
    only because of `sys.path` injection in `main_window.py`; converting to proper packages
    will require completing the `__init__.py` set.

---

*End of AGENT-DEVNEX-001.*
