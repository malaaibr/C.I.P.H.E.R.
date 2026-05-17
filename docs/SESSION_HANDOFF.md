# CIPHER Project — Session Handoff Document

**Date**: 2026-05-17
**Project Root**: `C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo`
**Purpose**: Complete context for the next Claude session to continue seamlessly.

---

## 1. PROJECT IDENTITY

**CIPHER** = Cognitive Intelligent Platform for Holistic Embedded R&D Automation
- Multi-agent AI platform for automotive SDLC (V-Cycle) automation
- 7-layer architecture: DRS, GCL, PKL, MKF, TRF, ARE, AAL + GUI + Core
- Desktop app: PyQt6 with JARVIS blue HUD theme
- Entry point: `python run_poc.py`
- Main agent: DevNex Assistant (93+ files, 13 V-cycle nodes)

---

## 2. WHAT WAS ACCOMPLISHED (GOOD THINGS)

### 2.1 GUI Unification — COMPLETE
Two separate GUIs merged into one unified PyQt6 app:
- **Mode 0**: CIPHER HUD dashboard (3-column: nav + center views + system status)
- **Mode 1**: DevNex workspace (sidebar + 5 panels + voice + log tail)
- Mode switching via `QStackedWidget` — instant, no widget recreation

### 2.2 Files Created Successfully
| File | Purpose | Status |
|------|---------|--------|
| `cipher/gui/theme.py` | JARVIS blue HUD QSS theme | WORKING |
| `cipher/gui/splash.py` | Animated boot splash (particles, rings, boot log) | WORKING |
| `cipher/gui/app.py` | QApplication factory + launch sequence | WORKING |
| `cipher/gui/main_window.py` | Unified main window (704 lines) | WORKING |
| `cipher/gui/panels/cipher_dashboard.py` | 3-column HUD dashboard | WORKING |
| `cipher/gui/panels/voice_panel.py` | Voice interface with ArcReactor + Waveform | WORKING |
| `cipher/gui/widgets/arc_reactor.py` | QPainter animated reactor widget (4 states) | WORKING |
| `cipher/gui/widgets/waveform.py` | 16-bar audio waveform visualizer | WORKING |
| `cipher/gui/widgets/voice_orb.py` | Pulsing concentric circle orb | WORKING |
| `cipher/core/orchestrator.py` | CipherOrchestrator mother node | WORKING |
| `run_poc.py` | POC entry point (servers + GUI) | WORKING |

### 2.3 DevNex Orchestrator Wiring — COMPLETE
- `main_window.py` fully wires DevNex orchestrator as child of CIPHER
- `_get_orchestrator()` lazy init with config from ConfigPanel
- `NodeWorker` / `FullRunWorker` QThread creation + signal wiring
- Human review gates via `threading.Event` pattern
- All 5 real DevNex panels load (WorkflowPanel, TracePanel, ReviewPanel, OutputLogPanel, ConfigPanel)
- `sys.path.insert(0, devnex_assistant/)` enables internal imports

### 2.4 Smoke Tests PASSED
```
CipherMainWindow constructed OK
  _workflow_panel type: WorkflowPanel  (real, not placeholder)
  _step_indicator available: True
  Orchestrator: DevNexOrchestrator
  Config keys: ['SWC_name', 'G_SWDD_TEMP', 'SWC_name_C', ...]
  NodeWorker created and wired successfully
```

### 2.5 Config Panel Enhancement — COMPLETE
- Added "Import Config" button to `devnex_assistant/.../config_panel.py`
- Opens file dialog filtered to `*.json`, populates form fields from imported file

### 2.6 Documentation — COMPLETE
| Document | Location | Size |
|----------|----------|------|
| Code Changes Guide (for junior engineers) | `docs/CODE_CHANGES_GUIDE.md` | 16 KB |
| Full Low-Level Design (all layers + agents) | `docs/CIPHER_LLD.md` | 56 KB |
| Training Course Prompt (20-module curriculum) | `docs/COURSE_PROMPT.md` | 13 KB |
| This handoff document | `docs/SESSION_HANDOFF.md` | — |

---

## 3. ISSUES ENCOUNTERED AND FIXED

### Issue 1: Window Disappears After Splash Screen (FIXED)
- **Symptom**: Splash plays, then app exits silently — no main window
- **Root Cause**: Qt's `quitOnLastWindowClosed=True` (default). When splash closes, Qt thinks last window closed and kills event loop.
- **Fix Applied**: Set `app.setQuitOnLastWindowClosed(False)` in `create_app()`, then `True` in `_on_splash_done()` after `window.show()`.
- **Files Changed**: `cipher/gui/app.py` (line 26), `run_poc.py` (line 74)

### Issue 2: DevNex Panels Show Placeholder Text (FIXED)
- **Symptom**: Switching to DevNex workspace shows "Workflow Panel" text instead of real UI
- **Root Cause**: DevNex panels use internal imports like `from interfaces.gui.styles import palette` — these fail without `devnex_assistant/` on `sys.path`
- **Fix Applied**: `sys.path.insert(0, str(_DEVNEX_ROOT))` at top of `main_window.py` line 34-35
- **Files Changed**: `cipher/gui/main_window.py`

### Issue 3: DevNex Backend Not Executing (FIXED)
- **Symptom**: Clicking "Run" on nodes only logged "Node run requested: S1N1" but nothing happened
- **Root Cause**: `_on_node_run()` only called `self.append_log()` — no worker creation, no orchestrator wiring
- **Fix Applied**: Full rewrite of `main_window.py` with lazy `_get_orchestrator()`, `NodeWorker`/`FullRunWorker` creation, complete signal wiring via `_wire_worker()`, all signal handlers
- **Files Changed**: `cipher/gui/main_window.py` (rewritten 3 times)

### Issue 4: Window Not Visible After Splash on Windows (FIXED)
- **Symptom**: Window created and `show()` called but appears behind other windows
- **Fix Applied**: Added `window.raise_()` and `window.activateWindow()` after `window.show()` in `_on_splash_done()`
- **Files Changed**: `run_poc.py` (line 71-72)

### Issue 5: Server Port Conflicts on Re-run (FIXED)
- **Symptom**: Restarting `run_poc.py` crashes because ports 8100/8200 still bound from previous run
- **Fix Applied**: Wrapped `start_server()` in try/except so port bind errors don't crash the process
- **Files Changed**: `run_poc.py` (lines 31-37)

---

## 4. KNOWN ISSUES / NOT YET TESTED

### 4.1 Actual Node Execution Through GCA
- The orchestrator wiring is verified (smoke test), but **actual node execution** (clicking Run on S1N1 with real workspace files) has NOT been tested end-to-end
- Requires: workspace with actual SWC files (DLT.c, DLT.h, etc.) + either GCA (VS Code extension) running or Ollama as fallback
- The orchestrator should initialize, load config, and attempt execution — errors will surface in the log tail

### 4.2 Voice System Not Connected
- Voice UI widgets are rendered (ArcReactor, Waveform, VoiceOrb, VoicePanel)
- Voice pipeline (TTS/STT) is NOT connected — buttons exist but no backend
- This is expected for MVP — voice is visual-only placeholder

### 4.3 CipherOrchestrator Not Wired as Parent
- `CipherOrchestrator` is created in `run_poc.py` but NOT passed to `CipherMainWindow`
- DevNex orchestrator is created independently inside `main_window.py`
- To complete the parent-child relationship, pass `CipherOrchestrator` to the window and register DevNex as `orchestrator.register_child("devnex", devnex_orch)`

### 4.4 cipher/agents/devnex/ Folder Question
- User asked to remove `cipher/agents/devnex/` (the A2A adapter folder)
- But it contains `DevNexAdapter` and `S1N1Skill` imported by `run_poc.py`
- **Decision needed**: Keep it (it's the CIPHER-layer A2A bridge) or move S1N1Skill into devnex_assistant

### 4.5 Missing __init__.py Files
- Some `cipher/gui/` sub-packages may be missing `__init__.py` — not caught because we use `sys.path` injection
- If converting to proper package imports later, ensure all `__init__.py` files exist

---

## 5. FILE MAP — WHAT TO READ FIRST

### Entry Points
```
run_poc.py                              ← Start here (launches everything)
cipher/gui/app.py                       ← QApplication factory
cipher/gui/main_window.py              ← THE critical file (704 lines, all wiring)
```

### GUI Layer
```
cipher/gui/theme.py                     ← JARVIS blue HUD QSS
cipher/gui/splash.py                    ← Animated boot splash
cipher/gui/panels/cipher_dashboard.py   ← Mode 0: 3-column HUD
cipher/gui/panels/voice_panel.py        ← Voice interface
cipher/gui/widgets/arc_reactor.py       ← Animated reactor widget
cipher/gui/widgets/waveform.py          ← Audio bars
cipher/gui/widgets/voice_orb.py         ← Pulsing orb
```

### DevNex Agent (under cipher/agents/devnex_assistant/)
```
core/orchestrator.py                    ← DevNexOrchestrator (750 lines, 13 nodes)
core/run_context.py                     ← DevNexRunContext (Pydantic)
core/errors.py                          ← Error hierarchy
interfaces/gui/panels/workflow_panel.py ← V-cycle canvas + node buttons
interfaces/gui/panels/config_panel.py   ← SWC config form (has Import button)
interfaces/gui/workers/node_worker.py   ← QThread single-node executor
interfaces/gui/workers/full_run_worker.py ← QThread all-nodes executor
persistence/config_store.py             ← JSON config persistence
persistence/state_store.py              ← JSON workflow state
```

### Core Platform
```
cipher/core/orchestrator.py             ← CipherOrchestrator (mother node)
cipher/core/schemas/task_contract.py    ← TaskContract, TaskResult, TaskStatus
cipher/core/adapters/                   ← Redis, Memgraph, Qdrant, MinIO, SQLite clients
cipher/trf/mcp_servers/llm_gateway/     ← LLM Gateway (Ollama + GCA routing)
cipher/are/a2a_server/server.py         ← A2A FastAPI server
cipher/are/skill_loader/loader.py       ← Skill plugin registry
```

### Infrastructure
```
deploy/local/docker-compose.yml         ← Full stack: Redis, Memgraph, Qdrant, MinIO, NATS, OPA, OTel
deploy/local/.env                       ← Environment variables
```

### Architecture Docs
```
docs/CIPHER_archi.md                    ← Full architecture reference (102 KB)
docs/CIPHER_HLD.md                      ← High-level design (98 KB)
docs/CIPHER_LLD.md                      ← Low-level design (56 KB, just created)
docs/CODE_CHANGES_GUIDE.md              ← Code changes explanation (16 KB, just created)
docs/COURSE_PROMPT.md                   ← Training course prompt (13 KB, just created)
```

---

## 6. SECURITY CONSTRAINTS

- **NEVER commit `.env` files** — contains MinIO credentials
- **NEVER commit `__pycache__/`** — cached Python bytecode
- **NEVER commit `*.pyc` files**
- `.gitignore` should cover these (verify before any commit)

---

## 7. HOW TO RUN

```bash
# 1. Start infrastructure
cd deploy/local
docker compose up -d

# 2. Ensure Ollama is running
ollama pull qwen2.5-coder:1.5b

# 3. Launch CIPHER
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo
python run_poc.py

# Splash screen plays ~7 seconds, then CIPHER HUD appears
# Click "OPEN DevNex WORKSPACE" to switch to DevNex mode
# Configure SWC in Config panel, then run nodes in Workflow panel
```

### Port Map
| Port | Service |
|------|---------|
| 4222 | NATS |
| 6333 | Qdrant |
| 6379 | Redis |
| 7687 | Memgraph |
| 8100 | A2A Server |
| 8181 | OPA |
| 8200 | LLM Gateway |
| 9000 | MinIO |
| 11434 | Ollama |

---

## 8. SUGGESTED NEXT STEPS

1. **Test actual node execution** — Configure a real SWC project in Config panel, click Run on S1N1, verify orchestrator executes through GCA/Ollama
2. **Wire CipherOrchestrator as parent** — Pass it to CipherMainWindow, register DevNex as child
3. **Connect voice pipeline** — Wire TTS/STT backend to VoicePanel
4. **Add more HUD dashboard views** — Currently 10 views in center QStackedWidget, most are placeholder
5. **System status live updates** — Dashboard right column shows static service status; wire health check polling
6. **Commit all changes** — Stage only code files (no .env, no __pycache__), write descriptive commit message
