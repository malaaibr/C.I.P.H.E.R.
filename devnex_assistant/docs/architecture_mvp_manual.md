# DevNex Assistant MVP Architecture

## Overview

`devnex-assistant` is a local Python orchestrator with a PyQt6 desktop GUI and Click CLI.
It drives the full V-Cycle AI automation pipeline for embedded SWC development:
LLD generation → Code linking → Traceability → Unit Test documentation → Full matrix.

GCA (Google Code Assist) is invoked for every AI step via isolated VS Code workspaces.
Human review gates pause execution and require explicit user confirmation before proceeding.

## Component Diagram

```mermaid
flowchart LR
  User[Engineer] --> GUI[PyQt6 MainWindow]
  User --> CLI[devnex CLI]
  GUI --> WP[WorkflowPanel]
  WP --> Orch[DevNexOrchestrator]
  CLI --> Orch
  Orch --> GCA[DevNexGCAInvoker]
  GCA --> Bridge[DevNex Bridge :37778]
  GCA --> ADP[ADP GeminiController]
  Bridge --> VSCode[VS Code Extension]
  Orch --> SS[StateStore ~/.devnex/]
  Orch --> CS[ConfigStore generated_artifacts/]
  Orch --> AW[ArtifactWriter]
  Orch --> HRG[Human Review Gate]
  HRG --> RD[ReviewDialog QDialog]
  RD --> User
```

## V-Cycle Stage Sequence

```mermaid
sequenceDiagram
  participant E as Engineer
  participant G as GUI
  participant O as Orchestrator
  participant GCA as GCA Invoker
  participant RM as Req Mgmt Tool

  E->>G: Fill Config, click Run All
  G->>O: run_all()

  Note over O,GCA: S1N1 — LLD Generation
  O->>GCA: invoke_prompt(lld_gen_v1.md, [.c, .h, templates])
  GCA-->>O: LLD CSV

  Note over O,E: S1N2 — Human Review Gate
  O->>E: ReviewDialog — upload LLD to DOORS/ReqIF
  E->>RM: upload CSV, assign IDs
  E->>G: click Continue

  Note over O,E: S1N3 — Human Review Gate
  O->>E: ReviewDialog — extract LLD with IDs
  E->>RM: export updated LLD
  E->>G: click Continue

  Note over O,GCA: S1N4 — Categorize Requirements
  O->>GCA: invoke_prompt(categorize, [InspBaseLLD])
  GCA-->>O: FUNC_req.csv

  Note over O,GCA: S2N1 — Embed LLD in Code
  O->>GCA: invoke_prompt(code_link_v1.md, [.c, FUNC_req])
  GCA-->>O: updated_SWC.c

  Note over O,E: S2N2 — Developer Review Gate
  O->>E: ReviewDialog — inspect annotated source
  E->>G: click Continue

  Note over O,GCA: S3N1–S5N1 — Traceability
  O->>GCA: LLD→Code report, HLD→LLD links, downstream matrix

  Note over O,E: S6N1 — VectorCAST Gate
  O->>GCA: generate test.bat artifacts
  O->>E: ReviewDialog — run VectorCAST, wait for .TST
  E->>G: click Continue

  Note over O,GCA: S7N1–S9N1 — UTD + Full Matrix
  O->>GCA: parse .TST → UTD, link UTD→LLD, build Full_Traceability_Matrix
  G->>E: Trace tab updated
```

## Run Artifacts

```
generated_artifacts/
  config.json                         — SWC project file paths
  workflow_state.json                 — node completion states
  runs/<run_id>/
    <SWC>_TEMP_LLD_updated.csv        — S1N1 output
    <SWC>_FUNC_req.csv                — S1N4 output
    updated_<SWC>.c                   — S2N1 output
    LLD_Code_Trace_Report.csv         — S3N1 output
    HLD_LLD_Links.json                — S4N1 output
    HLD_LLD_Code_Trace_Matrix.csv     — S5N1 output
    test.bat                          — S6N1 output
    <SWC>_UTD.md                      — S7N1 output
    UTD_LLD_Links.json                — S8N1 output
    Full_Traceability_Matrix.csv      — S9N1 output
```

## GCA Invocation

Every GCA call uses an isolated temporary workspace:

```python
ws = tempfile.mkdtemp(prefix="devnex_ws_")
# opens VS Code in that workspace
# prevents GeminiController latching to wrong window
```

Fallback chain:
1. Try `ADP.gca_comm_layer.gemini_controller.GeminiController` (if ADP installed).
2. Fall back to `DevNexBridge` HTTP client → `POST http://localhost:37778/prompt`.

## Human Review Threading Model

```
QThread (NodeWorker / FullRunWorker)
  │
  ├─ emit review_needed(node_id, message)   # cross-thread signal
  └─ threading.Event.wait()                 # blocks worker thread only

Main thread (GUI)
  ├─ slot: show ReviewDialog (modal)
  └─ on dialog close: worker.resume(approved)
                      → Event.set()         # unblocks worker thread
```

## State Persistence

| Store | Path | Content |
|---|---|---|
| `ConfigStore` | `generated_artifacts/config.json` | SWC file paths |
| `StateStore` | `~/.devnex/workflow_state.json` | node statuses |
| `SettingsManager` | `~/.devnex/gui_settings.json` | GUI geometry / preferences |
