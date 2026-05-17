# CIPHER GUI Integration — Code Changes Guide

**Audience**: Junior AI Engineers joining the CIPHER project
**Date**: 2026-05-17
**Scope**: All code changes made during the GUI unification sprint

---

## 1. What Was Done (High-Level)

We had **two separate GUI applications** and merged them into **one unified PyQt6 desktop app**:

| Before | After |
|--------|-------|
| **GUI 1** (CIPHER Entry): PyQt5, JARVIS blue HUD, 3-column layout | **Mode 0**: CIPHER HUD dashboard (3-column) |
| **GUI 2** (DevNex Assistant): PyQt6, 2-column sidebar layout | **Mode 1**: DevNex workspace (sidebar + panels + log) |
| Two separate executables | One app with mode switching via `QStackedWidget` |
| No shared orchestrator | `CipherOrchestrator` as parent, `DevNexOrchestrator` as child |

---

## 2. New Files Created

### 2.1 `cipher/gui/theme.py` — JARVIS Blue HUD Theme

**Why**: We needed a consistent dark-blue HUD theme across both modes. The original CIPHER Entry used PyQt5 stylesheets that wouldn't work in PyQt6.

**What it does**:
- Defines a `COLORS` dictionary with all theme tokens (background, accent, text, borders)
- Contains `JARVIS_QSS` — a complete Qt Style Sheet (QSS) string that styles every widget type
- `apply_theme(app)` function applies the stylesheet to the entire `QApplication`

**Key colors to know**:
```
Background:  #010a15  (near-black blue)
Accent:      #00c8ff  (bright cyan)
Success:     #00ff9d  (green)
Warning:     #ffb700  (amber)
Error:       #ff3a3a  (red)
Muted text:  #2d5f7a  (dim blue-grey)
```

**How it connects**: Called in `cipher/gui/app.py` → `create_app()` → `apply_theme(app)`. Every widget in the app inherits this theme.

---

### 2.2 `cipher/gui/splash.py` — Animated Boot Splash

**Why**: Visual boot sequence that shows system initialization progress while backend services start.

**What it does**:
- `SplashScreen(QWidget)` — frameless 860x560 window centered on screen
- Runs for ~6 seconds (120 ticks x 50ms per tick)
- Renders with `QPainter`: floating particles, rotating dashed rings, boot log text, progress bar
- Scrolls through 12 boot log lines (LLM Gateway, A2A Server, Redis, etc.) every 420ms
- After animation, fades out over ~750ms
- Emits `finished` signal when fade completes — this triggers the main window to show

**Key learning**: `QPainter` is Qt's low-level drawing API. Every frame, `paintEvent()` is called, and we draw everything from scratch. The `QTimer` at 50ms intervals triggers `update()` which causes a repaint.

**Signal flow**:
```
SplashScreen._fade_tick()
  → self._fade_opacity reaches 0
  → self.finished.emit()        ← This is a PyQt signal
  → self.close()
```

---

### 2.3 `cipher/gui/widgets/arc_reactor.py` — Arc Reactor Animation

**Why**: Visual indicator in the header bar showing system state (idle, listening, processing, speaking).

**What it does**:
- `ArcReactorWidget(size)` — circular animated widget
- 4 states with different color palettes: IDLE (cyan), LISTENING (teal), PROCESSING (purple), SPEAKING (green)
- Draws: outer glow, ring border, rotating tick marks, inner core orb
- Uses `sin()` for pulsing effects — the glow radius oscillates

**Key concept**: This is a custom widget that overrides `paintEvent()`. Qt calls this method whenever the widget needs redrawing. We use `QRadialGradient` for the glow effect and `QPen` for the ring.

---

### 2.4 `cipher/gui/widgets/waveform.py` — Audio Waveform Visualizer

**Why**: Visual feedback for voice activity in the Voice panel.

**What it does**:
- `WaveformWidget` — 16 vertical bars that animate when voice is active
- Each bar has a resting height; when active, bars jump to random heights every 120ms
- `set_active(True/False)` toggles animation
- `set_color(hex)` changes bar color

**Key concept**: This uses `QTimer` to periodically call `_tick()` which randomizes bar heights and calls `self.update()` to trigger a repaint.

---

### 2.5 `cipher/gui/widgets/voice_orb.py` — Voice Orb

**Why**: Pulsing visual indicator that shows whether the system is listening for voice input.

**What it does**:
- `VoiceOrbWidget` — concentric circles with a pulse ring that expands outward when listening
- `set_listening(True/False)` toggles the pulse animation

---

### 2.6 `cipher/gui/panels/cipher_dashboard.py` — CIPHER HUD Dashboard (Mode 0)

**Why**: This is the main landing screen — the 3-column CIPHER HUD that shows system status, navigation, and metrics.

**What it does**:
- `CipherDashboardPanel(on_devnex=callback)` — full 3-column layout:
  - **Left column**: Navigation list (10 views), "OPEN DevNex WORKSPACE" button, SWC context card
  - **Center column**: `QStackedWidget` with 10 views (Workflow, Trace, Components, etc.)
  - **Right column**: System Status panel (9 services with health dots), Session metrics, Quick Actions
- `on_devnex` callback: When user clicks "OPEN DevNex WORKSPACE", this fires the mode switch

**Helper classes**:
- `HudPanel(QFrame)` — bordered panel with a title header (reusable container)
- `MetricCard` — small card showing a value + label (e.g., "32 ms" / "Latency")
- `StageCard` — V-cycle stage status card with numbered badge

**Key learning**: `QStackedWidget` is like a tabbed view but without visible tabs. You switch pages by calling `setCurrentIndex(n)`. The navigation list on the left drives which page is shown.

---

### 2.7 `cipher/gui/panels/voice_panel.py` — Voice Interface Panel

**Why**: Full voice interaction UI with transcript log, command input, and visual feedback widgets.

**What it does**:
- `VoicePanel` — split layout:
  - **Left side (280px)**: ArcReactor + state label + VoiceOrb + Waveform + Start/Stop buttons
  - **Right side**: Transcript log (QTextEdit), command input (QLineEdit + Send button)
- `set_state(state)` — updates all visual elements for the given state
- `_add_entry(speaker, text)` — adds a colored line to the transcript

---

### 2.8 `cipher/gui/app.py` — Application Entry Point

**Why**: Clean separation between QApplication setup and window creation.

**What it does**:
- `create_app()` — creates `QApplication`, sets app name/version, applies theme
- `launch()` — creates splash + main window, wires splash.finished signal
- `main()` — CLI entry point

**Critical fix**: `app.setQuitOnLastWindowClosed(False)` is set during splash, then `True` after main window shows. Without this, Qt exits when the splash closes because it thinks the last window closed.

---

### 2.9 `cipher/gui/main_window.py` — Unified Main Window (THE CRITICAL FILE)

**Why**: This is the heart of the unified GUI. It ties together both modes (HUD and DevNex) and wires the DevNex orchestrator to the GUI.

**What it does**:

#### Import Strategy
```python
_DEVNEX_ROOT = Path(__file__).resolve().parent.parent / "agents" / "devnex_assistant"
sys.path.insert(0, str(_DEVNEX_ROOT))
```
We inject `devnex_assistant` onto `sys.path` so its internal imports (e.g., `from interfaces.gui.panels.workflow_panel import WorkflowPanel`) resolve correctly. All DevNex panel imports are wrapped in `try/except` with fallback to `None`.

#### DevNexSidebar
- Fixed 220px sidebar with nav buttons: Workflow, Trace, Review, Output, Config, Voice
- "CIPHER HUD" back button returns to Mode 0
- Emits `nav_clicked(str)` signal on button press

#### CipherMainWindow
- **Mode 0** (index 0): `CipherDashboardPanel` — the 3-column HUD
- **Mode 1** (index 1): DevNex workspace — sidebar + `QStackedWidget` of 6 panels + log tail
- **Header bar**: ArcReactor widget + title + mode label + status badge + voice label

#### Orchestrator Wiring (the most important part)
```
_get_orchestrator()
  → Reads config from ConfigPanel.get_config()
  → Creates DevNexRunContext(swc_name, workspace_path)
  → Creates DevNexOrchestrator(run_context=ctx)
  → Optionally attaches GCA invoker

_on_node_run_requested(node_id)
  → Calls _get_orchestrator() (lazy init)
  → Creates NodeWorker(orchestrator, node_id)
  → Calls _wire_worker(worker) to connect signals
  → worker.start() → runs in background QThread

_wire_worker(worker)
  → worker.log_line    → self.append_log()
  → worker.node_started → self._on_node_started()
  → worker.node_complete → self._on_node_complete()
  → worker.review_needed → self._on_review_needed()
  → worker.error_occurred → self._on_worker_error()
```

#### Human Review Gate
When a V-cycle node requires human approval:
1. Worker emits `review_needed(node_id, message)` signal
2. Main window shows `ReviewDialog` (or `QMessageBox` fallback)
3. User approves or rejects
4. Main window calls `worker.resume(approved)`
5. Worker's `threading.Event` unblocks and continues

**Key concept**: The worker runs in a `QThread` (background thread). It blocks on a `threading.Event` while waiting for human review. The GUI thread stays responsive. When the user clicks Approve/Reject, the GUI thread calls `worker.resume()` which sets the event and unblocks the worker thread.

---

### 2.10 `cipher/core/orchestrator.py` — CIPHER Mother Orchestrator

**Why**: Top-level orchestrator that owns child orchestrators (DevNex, future agents).

**What it does**:
- `CipherOrchestrator` — parent node in the orchestration tree
- `register_child(name, orchestrator)` — registers a child (e.g., "devnex")
- `get_child(name)` / `devnex` property — retrieves children
- `start()` / `stop()` — lifecycle management
- Holds URLs for LLM Gateway (`:8200`) and A2A Server (`:8100`)

**Design pattern**: This follows the **Composite pattern** — the mother orchestrator delegates to child orchestrators, each managing their own domain.

---

### 2.11 `run_poc.py` — POC Entry Point (Modified)

**Changes made**:
1. Now imports `create_app` from `cipher.gui.app` instead of creating QApplication directly
2. Creates `CipherOrchestrator` as the mother node
3. Starts LLM Gateway and A2A Server in daemon threads with error handling
4. Uses splash → main window transition with `quitOnLastWindowClosed` fix
5. Added `window.raise_()` and `window.activateWindow()` to ensure window appears on top after splash

---

### 2.12 Config Panel Update — `devnex_assistant/.../config_panel.py`

**Change**: Added "Import Config" button next to "Save Config".

**What it does**:
- Opens a `QFileDialog` filtered to `*.json`
- Reads the selected JSON file
- Populates all matching fields in the config form
- Updates the JSON preview

**Why**: Users need to load config from previous project setups without manually typing all 11 fields.

---

## 3. Key Bugs Fixed

### Bug 1: Window Disappears After Splash

**Symptom**: Splash screen plays, then nothing — app exits silently.

**Root cause**: Qt's default `quitOnLastWindowClosed` is `True`. When splash closes (it's the only visible window), Qt thinks the app should exit and kills the event loop.

**Fix**:
```python
# In create_app():
app.setQuitOnLastWindowClosed(False)   # Don't exit when splash closes

# In _on_splash_done():
window.show()
app.setQuitOnLastWindowClosed(True)    # Now it's safe — main window is visible
```

**Lesson**: Always check Qt's window lifecycle behavior when using splash screens.

### Bug 2: DevNex Panels Show Placeholder Text

**Symptom**: Switching to DevNex mode shows "Workflow Panel" text instead of the real panel.

**Root cause**: DevNex panels use internal imports like `from interfaces.gui.styles import palette`. These only resolve if `devnex_assistant/` is on `sys.path`.

**Fix**:
```python
_DEVNEX_ROOT = Path(__file__).resolve().parent.parent / "agents" / "devnex_assistant"
sys.path.insert(0, str(_DEVNEX_ROOT))
```

**Lesson**: When integrating a standalone app as a sub-module, you may need to manipulate `sys.path` to preserve its internal import structure.

### Bug 3: DevNex Backend Not Executing

**Symptom**: Clicking "Run" on nodes only logged "Node run requested: S1N1" but nothing happened.

**Root cause**: The initial `_on_node_run()` method just called `self.append_log()` — it didn't create workers or wire the orchestrator.

**Fix**: Full rewrite of `main_window.py` to add:
- Lazy `_get_orchestrator()` that creates `DevNexOrchestrator` with config from ConfigPanel
- `NodeWorker` / `FullRunWorker` thread creation
- Complete signal wiring via `_wire_worker()`
- All signal handlers: `_on_node_started`, `_on_node_complete`, `_on_review_needed`, etc.

**Lesson**: GUI buttons need to do more than log — they need to spawn background workers that actually execute the business logic.

### Bug 4: Window Not Visible After Splash (Windows)

**Symptom**: Window was created and `show()` was called, but it appeared behind other windows.

**Fix**: Added `window.raise_()` and `window.activateWindow()` after `window.show()` in `_on_splash_done()`.

**Lesson**: On Windows, `show()` alone doesn't guarantee focus. Use `raise_()` + `activateWindow()` to bring the window to front.

---

## 4. Architecture Decisions

### Why `QStackedWidget` for Mode Switching?

Instead of creating/destroying widgets when switching modes, we pre-build both the HUD and DevNex workspace and stack them. `QStackedWidget` only renders the visible page, so there's no performance overhead. Switching modes is instant — just `setCurrentIndex(0)` or `setCurrentIndex(1)`.

### Why Lazy Orchestrator Init?

The `DevNexOrchestrator` is only created when the user first clicks "Run" on a node. This avoids startup delays and ensures the ConfigPanel has been filled in before the orchestrator reads its config.

### Why `sys.path` Injection?

The DevNex Assistant was a standalone app with its own import structure (`from interfaces.gui.panels... import ...`). Converting all imports to absolute would require changing 90+ files. Instead, we inject its root directory onto `sys.path` so its relative imports work unchanged.

### Why QThread + threading.Event for Human Review?

V-cycle nodes sometimes need human approval (review gates). The worker runs in a `QThread` (keeps GUI responsive). When review is needed:
1. Worker emits a signal (crosses thread boundary safely via Qt's signal-slot mechanism)
2. Worker blocks on `threading.Event.wait()` (only blocks the worker thread)
3. GUI shows dialog, user decides
4. GUI calls `worker.resume(approved)` which sets the event
5. Worker thread unblocks and continues

This pattern keeps the GUI responsive while the worker waits for human input.

---

## 5. File Dependency Map

```
run_poc.py
  ├── cipher.gui.app.create_app()
  │     └── cipher.gui.theme.apply_theme()
  ├── cipher.gui.main_window.CipherMainWindow
  │     ├── cipher.gui.panels.cipher_dashboard.CipherDashboardPanel
  │     ├── cipher.gui.panels.voice_panel.VoicePanel
  │     ├── cipher.gui.widgets.arc_reactor.ArcReactorWidget
  │     ├── [sys.path inject] devnex_assistant/
  │     │     ├── interfaces.gui.panels.workflow_panel.WorkflowPanel
  │     │     ├── interfaces.gui.panels.trace_panel.TracePanel
  │     │     ├── interfaces.gui.panels.review_panel.ReviewPanel
  │     │     ├── interfaces.gui.panels.output_log.OutputLogPanel
  │     │     ├── interfaces.gui.panels.config_panel.ConfigPanel
  │     │     ├── interfaces.gui.workers.node_worker.NodeWorker
  │     │     ├── interfaces.gui.workers.full_run_worker.FullRunWorker
  │     │     ├── interfaces.gui.step_indicator.StepIndicator
  │     │     └── core.orchestrator.DevNexOrchestrator
  │     │           ├── core.run_context.DevNexRunContext
  │     │           ├── persistence.state_store.StateStore
  │     │           ├── persistence.config_store.ConfigStore
  │     │           └── gca.vscode_invoker.DevNexGCAInvoker
  │     └── cipher.gui.splash.SplashScreen
  ├── cipher.core.orchestrator.CipherOrchestrator
  ├── cipher.trf.mcp_servers.llm_gateway.server (LLM Gateway :8200)
  └── cipher.are.a2a_server.server (A2A Server :8100)
```

---

## 6. How to Run

```bash
# 1. Start infrastructure (Docker required)
cd deploy/local
docker compose up -d

# 2. Ensure Ollama is running with a model
ollama pull qwen2.5-coder:1.5b

# 3. Launch the app
python run_poc.py
```

The splash screen plays for ~7 seconds, then the CIPHER HUD appears. Click "OPEN DevNex WORKSPACE" to switch to the DevNex panels. Configure your SWC project in the Config panel, then click nodes in the Workflow panel to execute them.
