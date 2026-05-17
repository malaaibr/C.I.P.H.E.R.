# CIPHER Project — Claude Context

## Project Overview
CIPHER (Cognitive Intelligent Platform for Holistic Embedded R&D Automation) is a multi-agent AI desktop platform for automating automotive V-Cycle SDLC. Built with Python 3.11+, PyQt6, FastAPI, and a 7-layer architecture.

## Entry Point
```bash
python run_poc.py
```
Starts: LLM Gateway (:8200), A2A Server (:8100), PyQt6 GUI (splash → HUD → DevNex workspace).

## Architecture (7 Layers)
- **DRS**: Docker Compose infrastructure (Redis, Memgraph, Qdrant, MinIO, NATS, OPA, OTel)
- **GCL**: OPA policy engine + SQLite audit journal
- **PKL**: NATS event bus + LangGraph workflow engine
- **MKF**: Hybrid RAG (sentence-transformers + Qdrant + BM25)
- **TRF**: LLM Gateway (Ollama + GCA routing via TaskClassRouter)
- **ARE**: A2A Server (FastAPI + SSE) + SkillLoader registry
- **AAL**: Agent implementations (DevNex = primary agent, 9 stubs)
- **GUI**: PyQt6 — Mode 0 (3-column HUD) / Mode 1 (DevNex workspace)
- **Core**: Schemas (TaskContract, AgentCard), adapters (Redis, Qdrant, MinIO), OTel tracing

## Key Files
| File | What |
|------|------|
| `run_poc.py` | POC entry point |
| `cipher/gui/main_window.py` | Unified main window (THE critical file) |
| `cipher/gui/app.py` | QApplication factory |
| `cipher/gui/theme.py` | JARVIS blue HUD theme |
| `cipher/gui/splash.py` | Animated boot splash |
| `cipher/gui/panels/cipher_dashboard.py` | Mode 0: 3-column HUD |
| `cipher/core/orchestrator.py` | CipherOrchestrator (mother node) |
| `cipher/agents/devnex_assistant/core/orchestrator.py` | DevNexOrchestrator (13 V-cycle nodes) |
| `cipher/agents/devnex_assistant/interfaces/gui/panels/` | 5 DevNex panels |
| `cipher/agents/devnex_assistant/interfaces/gui/workers/` | NodeWorker, FullRunWorker (QThread) |
| `deploy/local/docker-compose.yml` | Full infra stack |

## Critical Design Decisions
1. **sys.path injection**: `main_window.py` adds `cipher/agents/devnex_assistant/` to `sys.path` so DevNex internal imports (`from interfaces.gui.panels...`) resolve without rewriting 90+ files
2. **Lazy orchestrator init**: `_get_orchestrator()` only creates `DevNexOrchestrator` on first node run, after ConfigPanel has been filled
3. **QThread + threading.Event**: Workers run in QThreads; human review gates block with `threading.Event.wait()` while GUI stays responsive
4. **quitOnLastWindowClosed**: Must be `False` during splash, `True` after main window shows — prevents premature Qt exit

## Security Rules
- NEVER commit `.env`, `__pycache__/`, `*.pyc` files
- `.gitignore` must cover these

## How to Run
```bash
cd deploy/local && docker compose up -d    # Infrastructure
ollama pull qwen2.5-coder:1.5b             # LLM model
python run_poc.py                           # Launch app
```

## Current State & Next Steps
See `docs/SESSION_HANDOFF.md` for complete status, issues fixed, known issues, and suggested next steps.

## Documentation
- `docs/CIPHER_archi.md` — Full architecture (102 KB)
- `docs/CIPHER_HLD.md` — High-level design (98 KB)
- `docs/CIPHER_LLD.md` — Low-level design (56 KB)
- `docs/CODE_CHANGES_GUIDE.md` — Code changes guide for junior engineers (16 KB)
- `docs/COURSE_PROMPT.md` — Training course prompt template (13 KB)
- `docs/SESSION_HANDOFF.md` — Session handoff with issues/fixes/next steps
