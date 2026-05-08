# DevNex Assistant High-Level Design

## 1. System Overview

DevNex Assistant is a local desktop and CLI automation tool for embedded software V-cycle workflows. It supports AI-assisted Low-Level Design (LLD) generation, LLD requirement categorization, source-code linking, traceability reporting, VectorCAST/Tessy test artifact generation, Unit Test Documentation (UTD), and final HLD-to-LLD-to-code-to-test traceability. The primary users are developers and verification engineers working with SWC source, HLD/LLD files, requirement-management handoffs, and GCA/VS Code automation.

The system runs as:

- A Click CLI through `devnex_assistant/devnex.py` and `devnex_assistant/interfaces/cli/cli_commands.py`.
- A PyQt6 desktop app through `devnex_assistant/main_gui.py` and `devnex_assistant/interfaces/gui/app.py`.
- A local automation client that invokes GCA through VS Code WebSocket integration or an HTTP bridge.

## 2. Architectural Style

The codebase follows a layered orchestration style:

- Interface layer: CLI and PyQt6 GUI collect user actions.
- Orchestration layer: `DevNexOrchestrator` coordinates fixed V-cycle nodes.
- Integration layer: GCA/VS Code bridge and WebSocket invocation.
- Persistence layer: JSON-backed config, state, and artifacts.
- Skill layer: intent-to-node adapters for future conversational workflows.
- Utility/UI layer: logging, constants, styles, and custom widgets.

The main runtime path is a sequential pipeline from `S1N1` to `S9N1`, implemented in `DevNexOrchestrator.run_all()` at `devnex_assistant/core/orchestrator.py:148`. A separate graph executor exists in `devnex_assistant/core/workflow_engine.py`, but current CLI and GUI flows use the orchestrator directly.

## 3. Layer Map

| Layer | Files | Responsibility |
| --- | --- | --- |
| Entrypoints | `devnex.py`, `main_gui.py`, `generate_icon.py` | Start CLI, GUI, or icon generation scripts. |
| CLI | `interfaces/cli/cli_commands.py` | Defines `run-stage`, `run-all`, `status`, and `config`. |
| GUI | `interfaces/gui/**/*.py` | Presents workflow canvas, config, trace, output log, settings, splash, and review dialogs. |
| Orchestration | `core/orchestrator.py` | Dispatches V-cycle nodes, validates config, builds prompts, writes artifacts, updates state. |
| Workflow engine | `core/workflow_engine.py` | Executes AF.json-style graphs by topological order. |
| Context and intent | `core/context_manager.py`, `core/intent_classifier.py`, `core/skill_registry.py`, `skills/*.py` | Build request context, classify raw input, and route to skill adapters. |
| Data contracts | `core/run_context.py`, `core/orchestrator.py::NodeResult`, skill `TaskResult` dataclasses | Represent run metadata, node results, and skill results. |
| Persistence | `persistence/*.py` | Read/write config, workflow state, and artifacts. |
| GCA integration | `gca/bridge.py`, `gca/vscode_invoker.py` | Communicate with VS Code/GCA over WebSocket or HTTP. |
| Tests | `tests/*.py` | Cover selected persistence, bridge, and orchestrator behavior. |

Dependency direction is generally:

```text
CLI/GUI -> core.orchestrator -> gca + persistence
skills -> core.orchestrator
tests -> implementation modules
```

## 4. Module Responsibility Matrix

| Module | Responsibility | Key Exports | Key Dependencies |
| --- | --- | --- | --- |
| `devnex.py` | Top-level Click wrapper. | `cli()` | `click`, `build_cli()` |
| `main_gui.py` | Creates `QApplication` and launches GUI. | `main()` | PyQt6, `launch_app()` |
| `generate_icon.py` | Generates GUI icon assets. | `_pixmap_to_pil()`, `generate()` | PyQt6, Pillow, `make_hex_pixmap()` |
| `core/orchestrator.py` | Central V-cycle pipeline. | `DevNexOrchestrator`, `NodeResult` | config/state stores, GCA invoker, errors |
| `core/workflow_engine.py` | AF.json graph executor. | `WorkflowEngine` | subprocess, JSON, GCA bridge-like object |
| `core/run_context.py` | Run metadata and artifact root. | `DevNexRunContext` | Pydantic |
| `core/errors.py` | Custom exception hierarchy. | `DevNexError` subclasses | none |
| `core/console_logging.py` | Structured console log formatting. | `format_console_log()`, `utc_timestamp()` | `ctypes`, env vars |
| `core/intent_classifier.py` | Rule-based input classifier. | `ParsedIntent`, `IntentClassifier` | regex, logging |
| `core/context_manager.py` | Builds runtime context from persisted state/config. | `WorkingContext`, `ContextManager` | state/config stores |
| `core/skill_registry.py` | Registers skill adapters. | `SkillRegistry` | concrete skill classes |
| `gca/bridge.py` | HTTP relay client for DevNex Bridge VSIX. | `DevNexBridge` | `requests`, custom errors |
| `gca/vscode_invoker.py` | VS Code/GCA WebSocket invocation with HTTP fallback. | `DevNexGCAInvoker`, `GCAInvocationResult` | `websocket`, subprocess, sockets |
| `persistence/config_store.py` | Project config JSON. | `ConfigStore`, `DEFAULT_CONFIG` | `json`, `Path` |
| `persistence/state_store.py` | Workflow state JSON. | `StateStore` | `json`, `Path.home()` |
| `persistence/artifact_writer.py` | Generic artifact helper. | `ArtifactWriter` | logging, JSON |
| `skills/*.py` | Thin adapters from intent to orchestrator node calls. | `ISkill`, concrete skills, `TaskResult` | orchestrator injection |
| `interfaces/cli/cli_commands.py` | CLI command group. | `build_cli()` | Click, orchestrator |
| `interfaces/gui/app.py` | GUI bootstrap sequence. | `launch_app()` | splash, main window, config modal |
| `interfaces/gui/main_window.py` | Primary GUI controller. | `MainWindow` | panels, workers, orchestrator |
| `interfaces/gui/workers/*.py` | Background execution threads. | `BaseWorker`, `NodeWorker`, `FullRunWorker` | Qt signals, orchestrator callbacks |
| `interfaces/gui/panels/*.py` | Workflow, config, trace, and output panels. | GUI widgets | PyQt6, stores |

## 5. System Data Flow

### CLI Single Stage

```text
devnex.py
  -> build_cli()
  -> run-stage STAGE
  -> _run_single(stage)
  -> DevNexOrchestrator.run_node(stage)
  -> selected _run_s*N* handler
  -> GCA invocation or human-review gate
  -> artifact write
  -> StateStore.set_node_status()
```

### GUI Single Stage

```text
WorkflowPanel node click
  -> MainWindow._on_node_run_requested()
  -> NodeWorker.start()
  -> NodeWorker.run()
  -> DevNexOrchestrator.run_node()
  -> worker signals update GUI status/log/review dialog
```

### Full V-Cycle Pipeline

`DevNexOrchestrator.run_all()` executes:

```text
S1N1 -> S1N2 -> S1N3 -> S1N4 -> S2N1 -> S2N2 ->
S3N1 -> S4N1 -> S5N1 -> S6N1 -> S7N1 -> S8N1 -> S9N1
```

Each node returns `NodeResult` and updates persisted workflow status.

### GCA Invocation

```text
orchestrator stage
  -> DevNexOrchestrator.gca_invoker
  -> DevNexGCAInvoker.invoke_prompt()
  -> temp VS Code workspace
  -> ~/.gca_instances.json polling
  -> WebSocket command sequence
  -> fallback DevNexBridge HTTP POST on timeout/error
```

## 6. Entry Points

| Entry Point | File | Trigger | Initiates |
| --- | --- | --- | --- |
| `cli()` | `devnex_assistant/devnex.py:14` | `python devnex.py` | Click command group. |
| `build_cli()` | `interfaces/cli/cli_commands.py:20` | Imported by CLI wrapper | CLI command definitions. |
| `run_stage(stage)` | `interfaces/cli/cli_commands.py:29` | `devnex run-stage STAGE` | Single node execution. |
| `run_all()` | `interfaces/cli/cli_commands.py:34` | `devnex run-all` | Full pipeline execution. |
| `status()` | `interfaces/cli/cli_commands.py:51` | `devnex status` | Workflow state display. |
| `config_cmd(show)` | `interfaces/cli/cli_commands.py:66` | `devnex config --show` | Config display/validation. |
| `main()` | `devnex_assistant/main_gui.py:10` | `python main_gui.py` | PyQt6 GUI startup. |
| `launch_app(app)` | `interfaces/gui/app.py:6` | Called by `main()` | Splash, config modal, main window. |
| `generate()` | `devnex_assistant/generate_icon.py:35` | `python generate_icon.py` | Icon asset generation. |
| `WorkflowEngine.execute()` | `core/workflow_engine.py:49` | Programmatic use | AF.json workflow execution. |

## 7. External Boundaries

| Boundary | File/Function | Operation |
| --- | --- | --- |
| HTTP bridge | `gca/bridge.py:55` | `POST /sendPrompt` to `http://127.0.0.1:37778`. |
| HTTP health | `gca/bridge.py:85` | `GET /health`. |
| WebSocket | `gca/vscode_invoker.py:57-67` | Connect/send/receive GCA commands. |
| VS Code launch | `gca/vscode_invoker.py:218` | `subprocess.Popen()` with `code` or `code.cmd`. |
| VS Code availability | `gca/vscode_invoker.py:328` | `subprocess.run(["code", "--version"])`. |
| Workflow scripts | `core/workflow_engine.py:84` | `subprocess.run()` for graph script nodes. |
| Config file | `persistence/config_store.py` | `generated_artifacts/config.json`. |
| Workflow state | `persistence/state_store.py` | `~/.devnex/workflow_state.json`. |
| Run artifacts | `core/orchestrator.py` | `~/.devnex/runs/{run_id}/...`. |
| Prompt templates | `core/orchestrator.py:515` | `devnex_assistant/prompts/*.md`. |
| GCA registry | `gca/vscode_invoker.py:121,148` | `~/.gca_instances.json`. |
| GUI settings | `interfaces/gui/settings_manager.py` | `~/.devnex/gui_settings.json`. |
| Human input | `core/orchestrator.py:531` | CLI `input()` for review gates. |
| File chooser | `config_panel.py`, `config_init_modal.py` | User-selected config/source paths. |

## 8. Configuration and Initialization

Primary project config is stored in `generated_artifacts/config.json`, with defaults defined in `persistence/config_store.py`. Required keys include SWC name, source/header paths, LLD/HLD files, linker/map files, and workspace path.

GUI startup:

```text
main_gui.main()
  -> QApplication
  -> launch_app()
  -> MainWindow()
  -> SplashScreen()
  -> ConfigInitModal()
  -> MainWindow.show()
```

Orchestrator startup:

```text
DevNexOrchestrator.__init__()
  -> StateStore()
  -> ConfigStore()
  -> ConfigStore.load()
  -> run_context.get_artifacts_path()
  -> artifact directory creation
```

Deferred initialization:

- `DevNexOrchestrator.gca_invoker` creates `DevNexGCAInvoker` only on first GCA call.
- GUI creates the orchestrator lazily in `MainWindow._get_orchestrator()`.

## 9. Current Architectural Risks

- `core/orchestrator.py` owns validation, prompts, GCA calls, artifact naming, and state updates.
- Node IDs are duplicated across orchestrator, GUI constants, and workflow metadata.
- `StateStore.set_node_status()` is read-modify-write without locking, so parallel writers can overwrite each other.
- Config/state invalid JSON is silently replaced with defaults or empty state.
- `StateStore.set_node_status()` does read-modify-write without locking.
