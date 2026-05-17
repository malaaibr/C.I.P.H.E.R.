# GUI — Low-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | LLD-GUI-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.3 (Software Detailed Design) |
| Layer | GUI — Desktop User Interface |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dir | `cipher/gui/` |
| Companion HLD | `docs/layers/GUI_HLD.md` (HLD-GUI-001) |
| Authoritative sources | `cipher/gui/main_window.py`, `cipher/gui/app.py`, `cipher/gui/splash.py`, `cipher/gui/theme.py`, `run_poc.py`, `docs/SESSION_HANDOFF.md`, `docs/CODE_CHANGES_GUIDE.md` |

---

## §1 Module Inventory

Every Python file under `cipher/gui/`, with one-line purpose. Files are
listed in roughly load-order from the boot path outward.

### Boot path (always loaded)

| File | Purpose |
|---|---|
| `app.py` | QApplication factory (`create_app`) + `launch()` that wires splash → main window with the `quitOnLastWindowClosed` fix |
| `theme.py` | `apply_theme(app)` — installs the global JARVIS Blue QSS stylesheet; exports `COLORS` dict and `JARVIS_QSS` string |
| `splash.py` | `SplashScreen(QWidget)` — frameless animated boot splash (~6 s), emits `finished` signal when fade completes |
| `main_window.py` | `CipherMainWindow(QMainWindow)` + `DevNexSidebar(QFrame)` — the unified main window; **THE critical file** (704 lines) per `CLAUDE.md` Key Files table |

### Panels (Mode-specific content)

| File | Purpose |
|---|---|
| `panels/cipher_dashboard.py` | `CipherDashboardPanel` — Mode 0, 3-column HUD dashboard. Receives an `on_devnex` callback used to switch the parent `QStackedWidget` to Mode 1 |
| `panels/voice_panel.py` | `VoicePanel` — voice-mode UI: large `ArcReactorWidget` + `VoiceOrbWidget` + `WaveformWidget` + transcript `QTextEdit` |
| `panels/devnex/panel_descriptor.py` | Small local DevNex descriptor shim used by the legacy `shell/` path; not on the unified boot path |
| `panels/devnex/workflow_widget.py` | Local placeholder workflow widget for the legacy `shell/` path |

### Widgets (reusable visual primitives)

| File | Purpose |
|---|---|
| `widgets/arc_reactor.py` | `ArcReactorWidget` — animated Iron-Man-style reactor with rotating rings and pulsing glow. States: `IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING` (constants on the class) |
| `widgets/waveform.py` | `WaveformWidget` — 16-bar audio visualizer with a default rest pattern and a random-bar active mode |
| `widgets/voice_orb.py` | `VoiceOrbWidget` — concentric-circle pulse orb for voice state indication |

### Legacy / reserved

| File | Purpose |
|---|---|
| `shell/main_window.py` | `CipherShell(QMainWindow)` — older dock-based shell per ADR-0005. **Not on the current boot path**; retained for reference |
| `client/a2a_client.py` | A2A HTTP client helper. Currently unused by the boot path |
| `client/sse_client.py` | Server-Sent Events client helper. Currently unused by the boot path |
| `__init__.py` files | Package markers. Some sub-packages may be missing one per `SESSION_HANDOFF.md` §4.5 |

---

## §2 Mode-Switching Mechanism

The window has exactly one top-level `QStackedWidget` named `_mode_stack`
(`main_window.py` line 261), built once at `__init__`:

```
_mode_stack
  ├─ index 0:  CipherDashboardPanel(on_devnex=self._switch_to_devnex)
  └─ index 1:  _build_devnex_workspace()  # sidebar + devnex_stack + log_tail
```

Switching modes is a single index change plus header-state updates:

- `_switch_to_devnex()` (lines 421–426): `setCurrentIndex(1)`, sets the
  header mode label to `"DevNex"`, puts the `ArcReactorWidget` into
  `PROCESSING` state, and updates the status bar text.
- `_switch_to_hud()` (lines 428–432): `setCurrentIndex(0)`, header label
  to `"HUD"`, reactor back to `IDLE`.
- `_on_devnex_nav(label)` (lines 434–443): the sidebar emits a string;
  `"__BACK__"` calls `_switch_to_hud`, everything else maps through
  `idx_map` into the inner `_devnex_stack`.

Because both modes are pre-built, switching is instantaneous and stateful
(panel contents survive a mode toggle).

### sys.path injection (the critical DevNex coupling)

`main_window.py` lines 32–35:

```python
_DEVNEX_ROOT = Path(__file__).resolve().parent.parent / "agents" / "devnex_assistant"
if str(_DEVNEX_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEVNEX_ROOT))
```

This must run **before** the `try: from interfaces.gui.panels...` import
blocks below it. Without it, DevNex panels fall back to placeholder
widgets — exactly the symptom of `SESSION_HANDOFF.md` Issue #2 before its
fix. Per `CLAUDE.md` Critical Design Decision #1, this avoids rewriting
imports in 90+ DevNex files.

Every panel import is wrapped:

```python
try:
    from interfaces.gui.panels.workflow_panel import WorkflowPanel as _WorkflowPanel, ReviewDialog as _ReviewDialog
except Exception as e:
    log.warning("Could not load WorkflowPanel: %s", e)
```

If any single panel fails, only that index of `_devnex_stack` falls back to
`_placeholder(title, desc)` (lines 404–417); the rest of the window keeps
working.

---

## §3 Splash Lifecycle (the quitOnLastWindowClosed gotcha)

This is `CLAUDE.md` Critical Design Decision #4 and `SESSION_HANDOFF.md`
Issue #1. Failing to handle it caused the app to silently exit after the
splash.

### The flow

1. `create_app()` in `app.py` calls
   `app.setQuitOnLastWindowClosed(False)` **before** showing anything.
2. `CipherMainWindow()` is constructed but **not** shown.
3. `SplashScreen()` is constructed and `splash.show()` is called. The
   splash is now the only visible top-level window.
4. The splash runs two `QTimer`s:
   - `_timer` (50 ms) advances animation ticks; at `_TOTAL_TICKS = 120`
     (~6 s) it calls `_start_fade()`.
   - `_log_timer` (420 ms) appends boot-log lines from `_BOOT_LINES`.
5. `_fade_tick()` linearly decreases `_fade_opacity` to 0 (25 steps of
   30 ms ≈ 0.75 s), then `finished.emit()` and `self.close()`.
6. `_on_splash_done` (in `app.py` / `run_poc.py`) is connected to
   `splash.finished`. It:
   - calls `window.show()`,
   - on Windows additionally calls `window.raise_()` and
     `window.activateWindow()` (per `SESSION_HANDOFF.md` Issue #4 fix),
   - logs three SUCCESS lines into the window's log tail, and
   - **only now** flips `app.setQuitOnLastWindowClosed(True)`.

Had we left `quitOnLastWindowClosed` at its default `True` value, the
moment the splash closed (step 5), Qt would observe "last visible window
has just closed" and tear down the event loop before step 6's
`window.show()` could register a new top-level window.

### The `_on_splash_done` reference implementations

- `cipher/gui/app.py` `launch()` lines 31–45 — the in-package launcher.
- `run_poc.py` `main()` lines 74–88 — the production launcher that also
  starts backend server threads. This is the form used by `python run_poc.py`.

Both forms are equivalent on the splash-handling axis; `run_poc.py`
additionally writes three `append_log(... level=...)` lines after
`window.show()` to seed the log tail.

---

## §4 Worker Threads

Worker threads belong to the DevNex agent (`cipher/agents/devnex_assistant/
interfaces/gui/workers/`), but the GUI layer is what instantiates them and
brokers their signals. Documented here because the wiring lives in
`main_window.py`.

### Pattern

For each user-initiated run:

1. `_on_node_run_requested(node_id)` (lines 487–506) or
   `_on_run_all_requested()` (lines 508–527) is called from a panel signal.
2. The GUI calls `_get_orchestrator()` — lazy-init that returns an existing
   `DevNexOrchestrator` or constructs one from the current `ConfigPanel`
   contents.
3. `worker = _NodeWorker(orchestrator, node_id)` (or `_FullRunWorker`) is
   created. `_NodeWorker` and `_FullRunWorker` are `QThread` subclasses
   provided by DevNex.
4. `_wire_worker(worker)` (lines 529–540) connects:
   - `worker.log_line` → `append_log`
   - `worker.node_started` → `_on_node_started`
   - `worker.node_complete` → `_on_node_complete`
   - `worker.review_needed` → `_on_review_needed`
   - `worker.error_occurred` → `_on_worker_error`
   - optional `worker.result_signal` → `_on_run_finished`
   - optional `worker.progress` → log line
5. The worker is appended to `self._workers` and stored as `_active_worker`
   so it isn't garbage-collected and can be `quit()` / `wait()` on close.
6. `worker.start()` launches the QThread.

### Review-gate pattern (`threading.Event`)

When a V-cycle node needs human approval, the worker emits
`review_needed(node_id, message)` and then **blocks** its own thread on a
`threading.Event.wait()` — this is `CLAUDE.md` Critical Design Decision
#3.

The GUI handler `_on_review_needed` (lines 576–591):

1. Shows DevNex's `ReviewDialog` if importable, else falls back to
   `QMessageBox.question`.
2. Reads the user decision into `approved: bool`.
3. Calls `self._active_worker.resume(approved)`, which sets the event and
   unblocks the worker thread.

The GUI thread is never blocked — `.wait()` runs on the worker QThread.

### Cleanup on close

`closeEvent` (lines 689–703) calls `quit()` + `wait(2000)` on
`_active_worker`, disconnects the GCA invoker if present, and closes file
logging via DevNex's `core.file_logger.close_file_logging()`.

---

## §5 Configuration

The GUI itself has very little user-facing configuration. The user-facing
configuration belongs to the DevNex `ConfigPanel` (SWC name, workspace
path, etc.) and is read by the window via `_get_config()` (lines 480–483)
each time the orchestrator is lazily constructed.

### Theme tokens (`cipher/gui/theme.py`)

Single source of truth for colors:

| Token | Value | Used for |
|---|---|---|
| `bg_primary` | `#010a15` | Window/canvas background |
| `bg_panel` | `#041624` | Panel surface |
| `accent_blue` | `#00c8ff` | Primary accent (titles, active nav, reactor IDLE) |
| `accent_cyan` | `#00ffe5` | Secondary accent (reactor LISTENING) |
| `success` | `#00ff9d` | SUCCESS log lines, reactor SPEAKING |
| `warning` | `#ffb700` | WARN log lines |
| `danger` | `#ff3a3a` | ERROR badge |
| `text_primary` | `#b8e8ff` | Body text |
| `text_muted` | `#2d5f7a` | Muted captions, inactive labels |
| `border` | `rgba(0,200,255,0.18)` | Default panel border |

The `JARVIS_QSS` string then styles `QMainWindow`, `QPushButton`,
`QLineEdit`, `QTextEdit`, `QPlainTextEdit`, `QListWidget`, `QProgressBar`,
`QTabWidget`, `QFrame`, and `QStatusBar`.

Several modules (`main_window.py`, `cipher_dashboard.py`, `splash.py`,
`voice_panel.py`) re-declare local color constants (`_ACCENT`, `_GREEN`,
`_WARN`, `_MUTED`, `_BG`, `_PANEL`) for inline `setStyleSheet` calls.
These mirror the `theme.COLORS` values; they are not a separate theme.

### Fonts

Declared in QSS only — no font files are bundled. The host OS is expected
to provide:
- `Segoe UI` — primary UI text (Windows default; commonly absent on Linux)
- `Cascadia Code` / `Consolas` — monospace (boot log, log tail)

There is no `cipher/gui/assets/` font directory in the current tree.

---

## §6 Test Coverage

The only documented automated check for the GUI layer is the smoke test
recorded in `docs/SESSION_HANDOFF.md` §2.4:

```
CipherMainWindow constructed OK
  _workflow_panel type: WorkflowPanel  (real, not placeholder)
  _step_indicator available: True
  Orchestrator: DevNexOrchestrator
  Config keys: ['SWC_name', 'G_SWDD_TEMP', 'SWC_name_C', ...]
  NodeWorker created and wired successfully
```

It verifies:
- The window constructs without raising.
- `sys.path` injection succeeded (the real `WorkflowPanel` loaded, not the
  placeholder).
- `StepIndicator` imported.
- Lazy `DevNexOrchestrator` construction succeeds with a default config.
- A `NodeWorker` can be created and wired.

What is **not** covered (and is flagged in `SESSION_HANDOFF.md` §4.1):
- End-to-end execution of a node (`Run S1N1`) with a real SWC workspace.
- Mode switching under user input (manual only today).
- Voice state changes (no backend wired — see §7).
- Splash → main-window transition timing on non-Windows hosts.

There is no `tests/gui/` directory in the current tree.

---

## §7 TODOs / Known Issues

Carried forward verbatim from `docs/SESSION_HANDOFF.md` §4. Nothing below
is invented.

| # | Status | Item |
|---|---|---|
| 4.1 | Not yet tested | Actual node execution through GCA (smoke test passes; real `Run S1N1` against workspace files not exercised end-to-end) |
| 4.2 | Not yet wired | Voice system — `VoicePanel`, `ArcReactorWidget`, `WaveformWidget`, `VoiceOrbWidget` render, but no TTS/STT backend is connected |
| 4.3 | Not yet wired | `CipherOrchestrator` is constructed in `run_poc.py` but never passed to `CipherMainWindow`; DevNex orchestrator is therefore not registered as `orchestrator.register_child("devnex", devnex_orch)` |
| 4.4 | Decision pending | `cipher/agents/devnex/` (the A2A adapter folder) — keep as the CIPHER-layer bridge, or move `S1N1Skill` into `devnex_assistant`? Affects `run_poc.py` line 19 import |
| 4.5 | Cleanup | Some `cipher/gui/` sub-packages may be missing `__init__.py`. Currently masked by `sys.path` injection; must be added if import paths are normalised |
| 8.4 | Follow-up | HUD center `QStackedWidget` has 10 views — most are placeholders (see `SESSION_HANDOFF.md` §8 step 4) |
| 8.5 | Follow-up | Dashboard right-column service-status pills are static; need health-check polling (`SESSION_HANDOFF.md` §8 step 5) |

### Architectural notes for the next change

- When wiring `CipherOrchestrator` as parent (4.3), prefer passing it into
  `CipherMainWindow.__init__` and storing it on `self._cipher_orchestrator`,
  then having `_get_orchestrator()` call
  `self._cipher_orchestrator.register_child("devnex", self._orchestrator)`
  after construction. Do not move orchestrator construction back into
  `run_poc.py` — the lazy-from-config pattern is required because the user
  may edit the SWC config in `ConfigPanel` before the first run.
- When connecting voice (4.2), the public surface is already in place:
  `CipherMainWindow.set_voice_state(state)` (lines 680–687) maps a
  `str` state into both the header `ArcReactor`, the header voice label,
  and the `VoicePanel`. A voice backend only needs to call this method.
- When normalising imports (4.5), removing the `sys.path` insertion will
  require renaming `from interfaces.gui...` imports to
  `from cipher.agents.devnex_assistant.interfaces.gui...` across the
  DevNex package. This is the explicit reason the injection exists today.
