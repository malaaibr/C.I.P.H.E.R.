# CIPHER VSCode Extension — Design

**Date**: 2026-05-18
**Status**: Approved for implementation (Sprint 1 active)
**Companion to**: `docs/SPRINT_PLAN.md`

---

## 1. Decision

**Option A — Webview + headless Python host.** VSCode extension (TypeScript) spawns `python run_poc.py --headless` as a child process; an in-editor `WebviewView` hosts the CIPHER UI as HTML/CSS/TS and communicates with the Python host via loopback HTTP (FastAPI) + SSE.

Option B (native window) rejected — does not match the user's "sub-window inside VSCode" requirement.

---

## 2. Architecture

```
┌─────────────────────────────── VSCode (Electron) ─────────────────────────────┐
│  ┌─ Activity Bar ─┐   ┌─────── WebviewView "CIPHER" ─────────────┐             │
│  │  [CIPHER icon]│──►│  HTML/CSS/TS bundle                       │             │
│  └────────────────┘   │  - Mode 0 HUD (canvas arc reactor)        │             │
│                       │  - Mode 1 DevNex panels                   │             │
│                       └────────────┬─────────────────────────────┘             │
│                                    │ postMessage  +  loopback HTTP/SSE         │
│  ┌──── Extension Host (Node) ──────▼─────────────────────────────┐             │
│  │  src/extension.ts — command: cipher.open                       │             │
│  │  src/pythonHost.ts — spawn run_poc.py --headless               │             │
│  └────────────────┬──────────────────────────────────────────────┘             │
└───────────────────┼───────────────────────────────────────────────────────────┘
                    │ HTTP + SSE (loopback 127.0.0.1)
┌───────────────────▼───────── Python host process ─────────────────────────────┐
│  run_poc.py --headless                                                        │
│  ├── A2A FastAPI :8100   (+ new /cipher/* + /events/sse)                      │
│  │     └── EventBridge  ◄── NodeWorker / FullRunWorker / ReviewWorker         │
│  │                          └── DevNexOrchestrator ─ child of CipherOrch.     │
│  └── LLM Gateway FastAPI :8200                                                │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Impact on existing code

### Reused unchanged
- `cipher/are/a2a_server/server.py` (gains a mount), `cipher/are/a2a_server/task_handler.py`
- `cipher/trf/mcp_servers/llm_gateway/server.py`
- `cipher/core/orchestrator.py` (CipherOrchestrator)
- `cipher/agents/devnex_assistant/core/orchestrator.py` (DevNexOrchestrator)
- `cipher/are/skill_loader/loader.py`, all skills
- Pydantic schemas, `persistence/state_store.py`

### Light refactor (separate logic from Qt)
- `cipher/agents/devnex_assistant/interfaces/gui/workers/node_worker.py`
- `cipher/agents/devnex_assistant/interfaces/gui/workers/full_run_worker.py`
  → `SignalAdapter` introduced: workers expose a non-Qt callback interface; pyqtSignal emission is only attached when running under QApplication.
- `cipher/agents/devnex_assistant/interfaces/gui/panels/*.py`
  → logic extracted to controllers (constants, state machines stay Python; QWidget rendering ported to TS in `extension/webview/`).
- `cipher/gui/main_window.py` — constructor accepts `parent_orchestrator: CipherOrchestrator | None = None`; on first `_get_orchestrator()` call, registers DevNex as child.
- `run_poc.py` — adds `--headless` flag.

### New
- `cipher/interfaces/web/__init__.py`
- `cipher/interfaces/web/event_bridge.py`
- `cipher/are/a2a_server/cipher_routes.py`
- `extension/` — full TS scaffold (see §5).

### Becomes legacy (kept importable but not the default surface)
- `cipher/gui/splash.py`, `cipher/gui/app.py`, `cipher/gui/panels/cipher_dashboard.py`, `cipher/gui/panels/voice_panel.py`, `cipher/gui/widgets/{arc_reactor,waveform,voice_orb}.py`, all Qt-specific files under `cipher/agents/devnex_assistant/interfaces/gui/`.
- These remain reachable via `python run_poc.py` (no `--headless`) until Sprint 6.

---

## 4. IPC protocol

### Webview ↔ Extension (postMessage, JSON-RPC-lite)
```ts
{ type: 'vscode.openFile', path: string, line?: number }
{ type: 'vscode.notify', level: 'info'|'warn'|'error', message: string }
{ type: 'host.restart' }
```

### Extension → Webview
```ts
{ type: 'host.status', state: 'starting'|'ready'|'error', detail?: string }
{ type: 'workspace.changed', workspaceFolder: string }
```

### Webview → Python (HTTP, loopback only)
- `GET  /cipher/healthz`
- `GET  /cipher/config`        — returns current DevNex config dict
- `PUT  /cipher/config`        — body: full config dict
- `POST /cipher/nodes/{node_id}/run`    — `{ runId }`
- `POST /cipher/runs/full`              — `{ runId }`
- `POST /cipher/runs/{runId}/review`    — body: `{ approved: bool }`
- `POST /cipher/workflow/reset`
- `GET  /cipher/trace?since=...`

### Python → Webview (SSE `/events/sse`)
Event envelope (mirrors the existing pyqtSignal set):
```json
{ "ts": "2026-05-18T12:00:00Z",
  "kind": "log|node.started|node.complete|review.needed|progress|status|error",
  "runId": "uuid",
  "nodeId": "S1N1",
  "payload": { ... } }
```

---

## 5. Folder layout (new `extension/`)

```
extension/
├── package.json              # name: cipher-vscode, contributes views + commands
├── tsconfig.json
├── .vscodeignore
├── README.md
├── icons/cipher-activity.svg
├── src/
│   ├── extension.ts
│   ├── cipherViewProvider.ts
│   ├── pythonHost.ts
│   ├── ipc/
│   │   ├── a2aClient.ts
│   │   ├── sseClient.ts
│   │   └── protocol.ts
│   └── util/portCheck.ts
├── webview/
│   ├── index.html
│   ├── main.ts
│   ├── styles/jarvis.css
│   └── components/
│       ├── ArcReactor.ts
│       ├── WorkflowPanel.ts
│       ├── TraceGraph.ts
│       ├── ReviewPanel.ts
│       ├── OutputLog.ts
│       └── ConfigPanel.ts
└── media/                    # built bundle output (gitignored)
```

---

## 6. Activation flow

1. User clicks CIPHER icon in Activity Bar → `cipher.mainView` resolves.
2. `CipherViewProvider.resolveWebviewView` runs `pythonHost.ensureStarted()`.
3. `pythonHost` probes 127.0.0.1:8100 `/healthz`; if missing, spawns `python run_poc.py --headless` using `cipher.pythonPath` and `cipher.repoPath` settings.
4. Webview loaded with strict CSP, opens `EventSource('http://127.0.0.1:8100/events/sse')`.
5. UI boots in Mode 0 (HUD); header button switches to Mode 1 (DevNex).

---

## 7. Risks & mitigations

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Orphaned Python process | Track PID in `globalState`; kill stale on activation; expose `cipher.restartHost` command. |
| 2 | Port conflicts | `portCheck.ts` probes; allow dynamic ports via settings; attach to healthy existing instance via `/healthz`. |
| 3 | Webview CSP | Nonce-based script tags; `connect-src` only allows `127.0.0.1:8100` and `127.0.0.1:8200`. |
| 4 | Python env discovery | `cipher.pythonPath` setting + autodetect `.venv` next to `pyproject.toml`; walkthrough shown if not found. |
| 5 | Distribution | Build with `vsce package` (unsigned) for sideload; later add Marketplace publisher + CI publish. |
