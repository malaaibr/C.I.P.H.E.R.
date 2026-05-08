# DevNex Assistant

DevNex Assistant is a local CLI and PyQt6 desktop tool for AI-assisted embedded software V-cycle automation. The current implementation focuses on an SWC workflow that uses GCA through VS Code to generate LLD artifacts, link requirements to code, build traceability outputs, and support test/UTD generation with human review gates.

## Currently Supported Features

- GUI workflow runner with an animated V-cycle canvas.
- CLI commands for running one stage, running the full pipeline, viewing state, and checking config.
- Project configuration stored in `devnex_assistant/generated_artifacts/config.json`.
- Workflow state stored in `~/.devnex/workflow_state.json`.
- Run artifacts stored under `~/.devnex/runs/<run_id>/`.
- GCA invocation through an isolated VS Code workspace and WebSocket connection.
- HTTP fallback through the DevNex Bridge VSIX at `http://127.0.0.1:37778`.
- Human-in-the-loop review gates for requirement-management upload, ID extraction, annotated-code review, and external test execution.
- Pytest/unittest coverage for config persistence, workflow state persistence, bridge behavior, and selected orchestrator paths.

## Supported V-Cycle Nodes

| Node | Purpose | Output |
| --- | --- | --- |
| `S1N1` | Generate updated LLD CSV from SWC source, headers, HLD, and templates. | `<SWC>_TEMP_LLD_updated.csv` |
| `S1N2` | Human gate for uploading generated LLD to a requirements-management tool. | Approval status |
| `S1N3` | Human gate for extracting LLD with unique IDs. | Approval status |
| `S1N4` | Categorize LLD requirements into functional/non-functional classes. | `<SWC>_FUNC_req.csv` |
| `S2N1` | Embed LLD requirement references into source code. | `updated_<SWC>.c` |
| `S2N2` | Human gate for reviewing annotated source code. | Approval status |
| `S3N1` | Generate LLD-to-code traceability report. | `LLD_Code_Trace_Report.csv` |
| `S4N1` | Link LLD requirements to HLD items. | `HLD_LLD_Links.json` |
| `S5N1` | Build downstream HLD/LLD/code traceability matrix. | `HLD_LLD_Code_Trace_Matrix.csv` |
| `S6N1` | Generate VectorCAST/Tessy test artifacts and wait for `.tst` files. | `test.bat` |
| `S7N1` | Generate Unit Test Documentation from `.tst` files. | `<SWC>_UTD.md` |
| `S8N1` | Link UTD test cases to LLD requirements. | `UTD_LLD_Links.json` |
| `S9N1` | Generate final full traceability matrix. | `Full_Traceability_Matrix.csv` |

## Repository Map

- `devnex_assistant/core/`: orchestration, workflow engine, run context, intent classification, errors, logging.
- `devnex_assistant/gca/`: VS Code/GCA WebSocket invoker and HTTP bridge client.
- `devnex_assistant/interfaces/cli/`: Click CLI commands.
- `devnex_assistant/interfaces/gui/`: PyQt6 desktop application.
- `devnex_assistant/persistence/`: config, state, and artifact helpers.
- `devnex_assistant/skills/`: intent-to-orchestrator adapters.
- `devnex_assistant/prompts/`: prompt templates used by orchestrator stages.
- `devnex_assistant/tests/`: pytest/unittest tests.
- `devnex_assistant/docs/HLD.md`: high-level architecture blueprint.
- `devnex_assistant/docs/LLD.md`: low-level design and call-flow blueprint.

## Install

```powershell
cd devnex_assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install -r requirements.txt
```

## Launch GUI

```powershell
cd devnex_assistant
python main_gui.py
```

On first launch, the GUI opens a configuration modal. Fill the SWC name, source/header files, HLD/LLD files, linker/map files, and workspace path before running nodes.

## CLI Usage

```powershell
cd devnex_assistant
python devnex.py run-stage S1N1
python devnex.py run-all
python devnex.py status
python devnex.py config --show
```

After installing the package, the `devnex` console command is also available:

```powershell
devnex run-stage S1N1
devnex run-all
devnex status
devnex config --show
```

## GCA / VS Code Requirements

For AI-backed stages, DevNex expects:

- VS Code command-line launcher available as `code` or `code.cmd`.
- GCA communication layer registering instances in `~/.gca_instances.json`.
- Optional HTTP bridge fallback active at `http://127.0.0.1:37778`.

Each GCA request creates an isolated temporary VS Code workspace named `devnex_ws_*` to avoid binding to an unrelated existing VS Code window.

## Tests

```powershell
cd devnex_assistant
python -m pytest
```

The current test suite covers persistence, HTTP bridge behavior, and selected orchestrator paths. GUI, WebSocket/VS Code integration, and most pipeline stages are not yet covered.

## Design Documents

- [HLD.md](devnex_assistant/docs/HLD.md)
- [LLD.md](devnex_assistant/docs/LLD.md)
