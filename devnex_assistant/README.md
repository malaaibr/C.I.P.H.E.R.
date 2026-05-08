# devnex-assistant

AI-powered V-Cycle automation tool for embedded software engineering (AUTOSAR / MISRA-C / ISO 26262).
Drives the full LLD → Code → Test → UTD → Traceability pipeline using GCA (Google Code Assist) with HITL review gates.

## What It Does

- **S1** — Generates Low-Level Design (LLD) from source code, HLD, and templates via GCA.
- **S1 Review** — HITL gates for Requirements Management tool upload and ID extraction.
- **S2** — Embeds LLD requirement references as structured comments in source code.
- **S3** — Generates LLD → Code traceability report (REQ_ID → function → line).
- **S4** — Links LLD requirements to parent HLD items.
- **S5** — Builds full downstream Code → LLD → HLD traceability matrix.
- **S6** — Generates VectorCAST/Tessy test artifacts and waits for `.TST` output (HITL gate).
- **S7** — Parses `.TST` results and generates formal Unit Test Documentation (UTD).
- **S8** — Maps UTD test cases to LLD requirements.
- **S9** — Consolidates full V-cycle traceability matrix: HLD → LLD → Code → Test → UTD.

## Install (Local)

```bash
cd devnex-assistant
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install pytest
```

## Launch GUI

```bash
python main_gui.py
```

## CLI Commands

```bash
devnex run-stage --node S1N1
devnex run-all
devnex status
devnex config --set SWC_name=TSYN
devnex config --show
```

## End-to-End Flow

1. **Fill Config tab** — set SWC name, source files, HLD, LLD templates, workspace path. Click Save Config.

2. **Run All** — click ▶ Run All in the Workflow tab to execute S1N1 → S9N1 sequentially.

3. **Human Review gates** — the workflow pauses at S1N2, S1N3, S2N2, S6N1 for manual steps:
   - S1N2: upload generated LLD to DOORS / ReqIF and assign unique IDs.
   - S1N3: extract updated LLD with IDs from Req Mgmt tool.
   - S2N2: review LLD-annotated source code.
   - S6N1: run VectorCAST/Tessy and wait for `.TST` files.

4. **Trace tab** — view HLD → LLD → Code → Test hierarchy after S9N1 completes.

5. **Output tab** — full GCA log for all invocations.

## Artifacts

All run artifacts are written to:

```
generated_artifacts/
  config.json
  workflow_state.json
  runs/<run_id>/
    <SWC>_TEMP_LLD_updated.csv
    <SWC>_FUNC_req.csv
    updated_<SWC>.c
    LLD_Code_Trace_Report.csv
    HLD_LLD_Links.json
    HLD_LLD_Code_Trace_Matrix.csv
    test.bat
    <SWC>_UTD.md
    UTD_LLD_Links.json
    Full_Traceability_Matrix.csv
```

## GCA Bridge

DevNex calls GCA via the **DevNex Bridge VSIX** — a TypeScript HTTP relay on `:37778`.

- Bridge must be installed in VS Code and active before running nodes.
- Bridge status is shown in the sidebar (● Bridge :37778 active / ● Bridge unavailable).
- Alternatively, if the `ADP` package is installed, DevNex uses `GeminiController` directly.

Each GCA invocation uses an isolated temporary VS Code workspace (`devnex_ws_*`) to avoid the GeminiController latching to the wrong existing window.

## Human Review Gates

Review gates use `threading.Event` so the worker thread blocks while the GUI remains fully responsive. The `ReviewDialog` modal shows the instruction message and Continue / Abort buttons.

## Tests

```bash
pytest
```
