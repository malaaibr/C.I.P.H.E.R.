# DevNex Assistant Low-Level Design

## 1. Class Catalog

### `NodeResult`

- File: `devnex_assistant/core/orchestrator.py:23-28`
- Type: dataclass
- Responsibility: Carries a node execution result.
- Attributes:
  - `node_id: str`
  - `status: str`
  - `output: str`
  - `artifacts: list[str]`
  - `errors: list[str]`

### `DevNexOrchestrator`

- File: `devnex_assistant/core/orchestrator.py:31-532`
- Responsibility: Coordinates V-cycle node execution.
- Stateful attributes:
  - `run_context`
  - `on_log`
  - `on_node_started`
  - `on_node_complete`
  - `on_human_review`
  - `progress_callback`
  - `state_store`
  - `config_store`
  - `config`
  - `_gca_invoker`
  - `_artifacts_dir`
- Key methods:
  - `__init__()` loads config and prepares artifact directory.
  - `gca_invoker` lazily creates `DevNexGCAInvoker`.
  - `_trace()` writes structured console and GUI callback logs.
  - `run_node(node_id)` validates node ID, dispatches handler, persists node status.
  - `run_all(progress_callback)` executes all supported nodes sequentially.
  - `_run_s1n1()` builds LLD generation prompt, embeds input file contents, invokes GCA, writes LLD CSV.
  - `_run_s1n2_review()` waits for Requirements Management upload approval.
  - `_run_s1n3_review()` waits for ID extraction approval.
  - `_run_s1n4()` categorizes LLD requirements and writes functional requirements CSV.
  - `_run_s2n1()` embeds requirement references into source and writes annotated source.
  - `_run_s2n2_review()` waits for annotated source review.
  - `_run_s3n1()` creates LLD-to-code traceability CSV.
  - `_run_s4n1()` creates HLD-to-LLD links JSON.
  - `_run_s5n1()` creates downstream HLD/LLD/code matrix.
  - `_run_s6n1()` creates test artifacts and waits for test execution approval.
  - `_run_s7n1()` parses `.tst` files through GCA and writes UTD markdown.
  - `_run_s8n1()` links UTD test cases to LLD requirements.
  - `_run_s9n1()` creates final full traceability matrix.
  - `_validate_config()` raises `ConfigValidationError` if keys are missing.
  - `_load_prompt()` reads prompt templates or returns fallback text.
  - `_render_prompt()` replaces `{{KEY}}` placeholders.
  - `_default_human_review()` blocks for CLI input.
- Side effects: file reads/writes, state writes, console logs, GCA calls, CLI input.

### `DevNexRunContext`

- File: `devnex_assistant/core/run_context.py:12-32`
- Type: Pydantic `BaseModel`
- Responsibility: Stores run ID, start time, SWC name, workspace path, and run artifact root.
- Methods:
  - `set_default_run_dir()` sets `~/.devnex/runs` when `run_dir` is missing.
  - `get_artifacts_path()` returns `run_dir / run_id`.

### `WorkflowEngine`

- File: `devnex_assistant/core/workflow_engine.py:18-154`
- Responsibility: Executes AF.json workflow graphs.
- Methods:
  - `execute(workflow_path, inputs)` loads JSON, topologically sorts nodes, executes each node by `serviceId`, returns last LLM response.
  - `_topological_sort(graph)` applies Kahn's algorithm to `sourceHandle == "next"` edges.
  - `_resolve_templates(data, outputs, inputs)` replaces `{{node.output.port}}` references.
  - `_default_human_review()` uses CLI input.
- Side effects: reads workflow JSON, runs subprocesses, calls GCA bridge, prompts user.

### Context and Intent Classes

- `WorkingContext`, `core/context_manager.py:17-23`: dataclass containing workflow state, config, workspace path, interface type, active file, and selection.
- `ContextManager`, `core/context_manager.py:26-52`: loads `StateStore` and `ConfigStore`, builds `WorkingContext`.
- `ParsedIntent`, `core/intent_classifier.py:16-21`: dataclass containing intent type, stage, skill ID, entities, and confidence.
- `IntentClassifier`, `core/intent_classifier.py:49-85`: regex-based classifier over `_RULES`.
- `SkillRegistry`, `core/skill_registry.py:13-49`: mutable registry of skill IDs to skill instances.

### Persistence Classes

- `ConfigStore`, `persistence/config_store.py:25-42`
  - `load()` reads JSON config, merges it over `DEFAULT_CONFIG`, returns defaults on missing file or invalid JSON.
  - `save(config)` creates parent directories and writes JSON.
- `StateStore`, `persistence/state_store.py:11-39`
  - `load()` reads workflow state JSON, returns `{}` on missing or invalid JSON.
  - `save(state)` writes JSON.
  - `set_node_status(node_id, status)` mutates `node_statuses`.
  - `get_node_statuses()` returns saved node status map.
  - `reset()` writes `{}`.
- `ArtifactWriter`, `persistence/artifact_writer.py:14-44`
  - `write_text()`, `write_json()`, `read_text()` are generic helpers. Current orchestrator writes artifacts directly instead.

### GCA Integration Classes

- `DevNexBridge`, `gca/bridge.py:20-88`
  - `send_prompt(prompt, attached_files)` posts to `http://127.0.0.1:37778/sendPrompt`.
  - `is_available()` checks `/health`.
  - Raises `GCANotAvailableError` for connection failure and `GCABridgeError` for HTTP/empty/timeout/general errors.
- `GCAInvocationResult`, `gca/vscode_invoker.py:38-44`
  - Fields: `raw_response`, `is_response_valid`, `started_vscode_window`.
- `_DirectGCAClient`, `gca/vscode_invoker.py:49-114`
  - Owns WebSocket connection.
  - Sends commands: `gca.resetChat`, `vscode.closeAllFiles`, `vscode.openFile`, `gca.addFileToContext`, `gca.sendPrompt`.
  - Retries prompt sends and raises `RuntimeError` when no response is returned.
- `DevNexGCAInvoker`, `gca/vscode_invoker.py:169-331`
  - Creates isolated temporary VS Code workspace.
  - Launches VS Code.
  - Polls `~/.gca_instances.json`.
  - Connects WebSocket.
  - Falls back to HTTP bridge if registry/WebSocket flow fails.

### Skill Classes

- `ISkill`, `skills/base_skill.py:8-28`: abstract base with injected `orchestrator`.
- `LLDGenSkill`, `skills/lld_gen_skill.py:25-52`: maps Stage 1 intents to `S1N1`, `S1N2`, `S1N3`, or `S1N4`.
- `CodeLinkSkill`, `skills/code_link_skill.py:25-51`: maps Stage 2 intents to `S2N1` or `S2N2`.
- `TraceReportSkill`, `skills/trace_report_skill.py:25-51`: maps Stage 3-5 intents to `S3N1`, `S4N1`, or `S5N1`.
- `TestGenSkill`, `skills/test_gen_skill.py:25-51`: maps Stage 6-8 intents to `S6N1`, `S7N1`, or `S8N1`.
- `FullTraceSkill`, `skills/full_trace_skill.py:25-49`: always runs `S9N1`.
- Each concrete skill returns its local `TaskResult` dataclass.

### GUI Classes

- `MainWindow`, `interfaces/gui/main_window.py:61-356`: primary window, lazy orchestrator owner, worker coordinator, log mirror, status updater.
- `ConfigInitModal`, `interfaces/gui/config_init_modal.py:47-399`: first-run/returning-user configuration modal.
- `SettingsManager`, `interfaces/gui/settings_manager.py:10-68`: JSON settings storage at `~/.devnex/gui_settings.json`.
- `SettingsDialog`, `interfaces/gui/settings_dialog.py:26-273`: settings and navigation dialog.
- `SplashScreen`, `interfaces/gui/splash.py:45-363`: animated splash screen.
- `StepIndicator`, `interfaces/gui/step_indicator.py:42-169`: stage state visualization.
- `ConfigPanel`, `interfaces/gui/panels/config_panel.py:29-142`: config form bound to `ConfigStore`.
- `OutputLogPanel`, `interfaces/gui/panels/output_log.py:11-65`: read-only colored log tab.
- `TracePanel`, `interfaces/gui/panels/trace_panel.py:25-120`: traceability tree UI and latest artifact lookup.
- `VCycleCanvas`, `interfaces/gui/panels/workflow_panel.py:150-608`: custom-painted V-cycle canvas.
- `WorkflowPanel`, `interfaces/gui/panels/workflow_panel.py:615-949`: workflow sidebar/detail strip, emits node/run/reset signals.
- `ReviewDialog`, `interfaces/gui/panels/workflow_panel.py:956-1046`: modal Continue/Abort gate.
- `BaseWorker`, `interfaces/gui/workers/base_worker.py:9-55`: generic QThread execution template.
- `NodeWorker`, `interfaces/gui/workers/node_worker.py:13-66`: runs one node in a worker thread.
- `FullRunWorker`, `interfaces/gui/workers/full_run_worker.py:13-65`: runs full pipeline in a worker thread.

## 2. Standalone Function Catalog

| Function | File | Role | Side Effects |
| --- | --- | --- | --- |
| `cli()` | `devnex.py:14` | Click root command. | CLI registration. |
| `_pixmap_to_pil()` | `generate_icon.py:23` | Converts Qt pixmap to PIL image. | Buffer operations. |
| `generate()` | `generate_icon.py:35` | Writes icon assets. | File writes under `assets/`. |
| `main()` | `main_gui.py:10` | GUI script entry. | Creates app, exits process. |
| `_try_enable_windows_vt_mode()` | `core/console_logging.py:25` | Enables ANSI mode on Windows. | `ctypes` console call. |
| `_supports_color()` | `core/console_logging.py:51` | Determines color support. | Reads env vars. |
| `_colorize_path_segments()` | `core/console_logging.py:66` | Adds ANSI color to quoted paths. | None. |
| `_level_color()` | `core/console_logging.py:85` | Maps level to color. | None. |
| `utc_timestamp()` | `core/console_logging.py:103` | Returns UTC timestamp. | None. |
| `format_console_log()` | `core/console_logging.py:112` | Formats structured log line. | None. |
| `_read_registry_ids()` | `gca/vscode_invoker.py:119` | Reads GCA registry IDs. | File read. |
| `_is_port_open()` | `gca/vscode_invoker.py:129` | Checks localhost port. | Socket connect. |
| `_wait_and_connect()` | `gca/vscode_invoker.py:139` | Polls registry and opens WebSocket. | File read, socket/WebSocket. |
| `_make_orchestrator()` | `interfaces/cli/cli_commands.py:13` | Creates run context and orchestrator. | Config/artifact initialization. |
| `build_cli()` | `interfaces/cli/cli_commands.py:20` | Builds Click group. | Defines nested commands. |
| `_run_single()` | `interfaces/cli/cli_commands.py:83` | Runs one node and prints result. | CLI output, process exit on error. |
| `launch_app()` | `interfaces/gui/app.py:6` | Starts GUI sequence. | UI creation/event loop. |
| `make_hex_pixmap()` | `interfaces/gui/icon.py:14` | Draws app icon pixmap. | Qt painting. |
| `_hex_path()` | `interfaces/gui/icon.py:72` | Draws hex path. | Qt painting. |
| `_infer_level()` | `interfaces/gui/main_window.py:47` | Infers log level from text. | None. |

## 3. Main Call Graphs

### CLI Single Stage

```text
devnex.cli()
  -> build_cli()
    -> run_stage(stage)
      -> _run_single(stage)
        -> _make_orchestrator()
          -> DevNexRunContext()
          -> DevNexOrchestrator.__init__()
            -> ConfigStore.load()
            -> DevNexRunContext.get_artifacts_path()
        -> DevNexOrchestrator.run_node(stage)
          -> selected _run_s*N*()
          -> StateStore.set_node_status()
```

### GUI Single Node

```text
WorkflowPanel.node_run_requested
  -> MainWindow._on_node_run_requested()
    -> MainWindow._get_orchestrator()
    -> NodeWorker.__init__()
    -> MainWindow._wire_worker()
    -> NodeWorker.start()
      -> NodeWorker.run()
        -> NodeWorker._execute()
          -> DevNexOrchestrator.run_node()
```

### GUI Full Run

```text
WorkflowPanel.run_all_requested
  -> MainWindow._on_run_all_requested()
    -> FullRunWorker.__init__()
    -> FullRunWorker.start()
      -> FullRunWorker.run()
        -> FullRunWorker._execute()
          -> DevNexOrchestrator.run_all()
            -> DevNexOrchestrator.run_node() for each supported node
```

### GCA Invocation

```text
DevNexOrchestrator._run_s*N*()
  -> DevNexOrchestrator.gca_invoker
    -> DevNexGCAInvoker(Path(workspace_path))
  -> DevNexGCAInvoker.invoke_prompt()
    -> _create_isolated_workspace()
    -> _read_registry_ids()
    -> _launch_vscode()
    -> _wait_and_connect()
      -> _is_port_open()
      -> _DirectGCAClient()
    -> _prepare_context()
      -> reset_chat()
      -> close_all_files()
      -> open_file()
      -> add_file_to_context()
    -> _DirectGCAClient.send_prompt()
    -> fallback _invoke_via_bridge()
      -> DevNexBridge.send_prompt()
```

### AF.json Workflow Engine

```text
WorkflowEngine.execute()
  -> json.loads(Path(workflow_path).read_text())
  -> _topological_sort()
  -> for each node:
       -> _resolve_templates()
       -> service dispatch:
            logic.internal: no-op
            extension.llm.sendPrompt: gca_bridge.send_prompt()
            atomic.executionService: subprocess.run()
            logic.humanReview: on_human_review()
```

## 4. Data Transformation Traces

### `S1N1`: LLD Generation

Input:

- Config keys: `SWC_name`, `G_SWDD_TEMP`, `SWC_name_C`, `SWC_name_H`, `SWC_name_TEMP_LLD`, `SWC_name_HLD`, `Linker File`, `map_file`, `workspace_path`.

Pipeline:

1. `_validate_config()` checks required keys.
2. Relative file paths are resolved against `workspace_path`.
3. `lld_gen_v1.md` is loaded.
4. `{{KEY}}` placeholders are replaced.
5. Input file contents are embedded into prompt when present; missing files are represented as `[FILE NOT FOUND]`.
6. GCA is invoked with prompt and file paths.
7. Raw response is written to `{SWC}_TEMP_LLD_updated.csv`.

Output:

- `NodeResult(node_id="S1N1", status="complete", output=<GCA response>, artifacts=[...])`

### `S1N4`: Requirement Categorization

1. Validate `SWC_name` and `SWC_nameInspBaseLLD`.
2. Read inspection-base LLD if it exists.
3. Build categorization prompt.
4. Invoke GCA.
5. Write `{SWC}_FUNC_req.csv`.

### `S2N1`: Code Linking

1. Validate `SWC_name` and `SWC_name_C`.
2. Load `code_link_v1.md`.
3. Render prompt from config.
4. Invoke GCA with source file and `{SWC}_FUNC_req.csv`.
5. Write `updated_{SWC}.c`.

### `S3N1` to `S5N1`: Traceability

- `S3N1`: `updated_{SWC}.c` + `{SWC}_FUNC_req.csv` -> `LLD_Code_Trace_Report.csv`.
- `S4N1`: HLD file + `{SWC}_FUNC_req.csv` -> `HLD_LLD_Links.json`.
- `S5N1`: `LLD_Code_Trace_Report.csv` + `HLD_LLD_Links.json` -> `HLD_LLD_Code_Trace_Matrix.csv`.

### `S6N1` to `S8N1`: Testing and UTD

- `S6N1`: source + functional requirements -> `test.bat`, then human gate for `.TST` generation.
- `S7N1`: workspace/artifact `.tst` files -> `{SWC}_UTD.md`.
- `S8N1`: UTD + functional requirements -> `UTD_LLD_Links.json`.

### `S9N1`: Final Traceability

1. Load `full_trace_v1.md`.
2. Render prompt from config.
3. Attach `HLD_LLD_Code_Trace_Matrix.csv` and `UTD_LLD_Links.json`.
4. Write `Full_Traceability_Matrix.csv`.

## 5. State and Mutation Map

| Component | Initialized | Mutated | Risk |
| --- | --- | --- | --- |
| `DevNexOrchestrator.config` | `__init__()` | Replaced directly in tests; not auto-reloaded after external config changes. | Stale config in long-lived GUI orchestrator. |
| `DevNexOrchestrator._gca_invoker` | First `gca_invoker` access | Set once lazily. | Workspace path changes require orchestrator reset. |
| `StateStore` JSON | `StateStore.load()` | `set_node_status()`, `reset()` | No file lock. |
| `ConfigStore` JSON | `ConfigStore.load()` | `save()` | Invalid JSON silently ignored. |
| `MainWindow._workers` | `__init__()` | Worker append only. | Keeps worker references for lifetime. |
| `MainWindow._orchestrator` | `_get_orchestrator()` | Reset on config save/reset. | Shared callbacks are reassigned by workers. |
| `NodeWorker._review_event` | `__init__()` | clear/wait/set around review gates. | Worker blocks until GUI resumes. |
| `FullRunWorker._review_event` | `__init__()` | clear/wait/set around review gates. | Same as single-node worker. |
| `SettingsManager._data` | `_load()` | `set()` and failed load reset. | Save errors are swallowed. |
| `VCycleCanvas._statuses` | `__init__()` | `set_node_status()`. | GUI-only state. |

## 6. Error and Exception Map

| Exception | Raised At | Trigger | Caught By |
| --- | --- | --- | --- |
| `NodeExecutionError` | `orchestrator.py:140` | Unknown node ID. | CLI generic catch, GUI worker catch, tests. |
| `NodeExecutionError` | `orchestrator.py:230,295,320` | Invalid GCA response for S1N1/S1N4/S2N1. | CLI generic catch, GUI worker catch. |
| `WorkflowAbortedError` | `orchestrator.py:252,267,341,436` | Human review rejected. | GUI worker catch; CLI generic catch. |
| `WorkflowAbortedError` | `workflow_engine.py:98` | Graph human review rejected. | Caller responsibility. |
| `ConfigValidationError` | `orchestrator.py:509` | Missing required config field. | CLI generic catch, GUI worker generic catch, tests. |
| `GCANotAvailableError` | `bridge.py:70` | Bridge connection failure. | CLI specific catch; otherwise caller. |
| `GCABridgeError` | `bridge.py:61,65,75,79` | HTTP error, empty response, timeout, unexpected bridge error. | Caller responsibility. |
| `RuntimeError` | `vscode_invoker.py:106,161` | GCA retries exhausted or registry timeout. | Registry timeout is caught for fallback; send failure falls into fallback path through generic catch. |
| `NotImplementedError` | `base_worker.py:50` | Base worker `_execute()` called directly. | `BaseWorker.run()` catches generic exception. |

Silent or swallowed errors:

- `_DirectGCAClient.reset_chat()`, `close_all_files()`, `open_file()`, `add_file_to_context()`, and `close()` swallow generic exceptions.
- `SettingsManager.save()` swallows all exceptions.
- `ConfigStore.load()` returns defaults for invalid JSON.
- `StateStore.load()` returns `{}` for invalid JSON.
- `DevNexBridge.is_available()` returns `False` for all exceptions.

## 7. Test Coverage Map

| Test File | Covered Components | Assertions |
| --- | --- | --- |
| `tests/test_config_store.py` | `ConfigStore` | Save/load roundtrip, default config on missing file, parent directory creation, overwrite behavior. |
| `tests/test_state_store.py` | `StateStore` | Node status save/read, multiple node statuses, reset, persistence across instances, missing file. |
| `tests/test_gca_bridge.py` | `DevNexBridge` | Health true/false, prompt success, HTTP error raises, connection error raises. |
| `tests/test_orchestrator.py` | `DevNexOrchestrator` | Unknown node error, S1N2/S1N3 human gate paths, config validation, prompt rendering, missing prompt fallback, S4 artifact write. |

Known untested areas:

- GUI widgets, dialogs, and workers.
- `DevNexGCAInvoker` WebSocket and VS Code launch behavior.
- `WorkflowEngine`.
- `IntentClassifier`, `ContextManager`, `SkillRegistry`, and skill adapters.
- Most orchestrator stages.
- `ArtifactWriter`, icon generation, console logging helpers.

## 8. High-Risk Functions

- `DevNexOrchestrator.run_node()` because every CLI, GUI, and skill node execution depends on it.
- `DevNexOrchestrator.run_all()` because it defines full pipeline order.
- `DevNexOrchestrator._run_s1n1()` because it performs config validation, path resolution, file embedding, GCA invocation, and artifact writing.
- `DevNexGCAInvoker.invoke_prompt()` because it owns the most fragile external integration path.
- `StateStore.set_node_status()` because it performs unlocked read-modify-write persistence.
- `MainWindow._wire_worker()` because GUI callbacks and worker signals pass through it.
- `NodeWorker._handle_human_review()` and `FullRunWorker._handle_human_review()` because they block background threads while waiting for GUI response.
