---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# devnex-assistant

AI-assisted V-cycle automation for embedded SWC workflows. The current implementation provides a local Click CLI and PyQt6 GUI that orchestrate LLD generation, requirement categorization, LLD-to-code linking, traceability report generation, test artifact generation, UTD generation, and final HLD/LLD/code/test traceability through GCA.

## Supported Workflow

| Node | Purpose | Output |
| --- | --- | --- |
| `S1N1` | Generate updated LLD CSV from source, headers, HLD, and templates. | `<SWC>_TEMP_LLD_updated.csv` |
| `S1N2` | Human gate for requirements-management upload. | Approval status |
| `S1N3` | Human gate for extracting unique requirement IDs. | Approval status |
| `S1N4` | Categorize requirements. | `<SWC>_FUNC_req.csv` |
| `S2N1` | Embed LLD references into source code. | `updated_<SWC>.c` |
| `S2N2` | Human gate for annotated-code review. | Approval status |
| `S3N1` | Generate LLD-to-code traceability. | `LLD_Code_Trace_Report.csv` |
| `S4N1` | Link LLD requirements to HLD items. | `HLD_LLD_Links.json` |
| `S5N1` | Build downstream HLD/LLD/code trace matrix. | `HLD_LLD_Code_Trace_Matrix.csv` |
| `S6N1` | Generate VectorCAST/Tessy test artifacts and wait for `.tst`. | `test.bat` |
| `S7N1` | Generate UTD from `.tst` files. | `<SWC>_UTD.md` |
| `S8N1` | Link UTD cases to LLD requirements. | `UTD_LLD_Links.json` |
| `S9N1` | Generate final full traceability matrix. | `Full_Traceability_Matrix.csv` |

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install -r requirements.txt
```

## Launch GUI

```powershell
python main_gui.py
```

The GUI starts with a splash screen, then opens a configuration modal. Configuration is saved to `generated_artifacts/config.json`.

## CLI Usage

```powershell
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

## Runtime Storage

- Config: `generated_artifacts/config.json`
- Workflow state: `~/.devnex/workflow_state.json`
- Run artifacts: `~/.devnex/runs/<run_id>/`
- GUI settings: `~/.devnex/gui_settings.json`
- GCA registry: `~/.gca_instances.json`

## GCA Integration

DevNex first tries to invoke GCA through a fresh isolated VS Code workspace and WebSocket connection. If registry/WebSocket setup fails, it falls back to the DevNex Bridge VSIX HTTP relay at `http://127.0.0.1:37778`.

Required external pieces:

- VS Code CLI available as `code` or `code.cmd`.
- Active GCA communication layer or DevNex Bridge VSIX.
- Source/HLD/LLD/template files configured in the GUI or config JSON.

## Tests

```powershell
python -m pytest
```

Current tests cover config persistence, workflow state persistence, bridge behavior, and selected orchestrator paths.

## Design Documents

- [HLD.md](docs/HLD.md)
- [LLD.md](docs/LLD.md)
