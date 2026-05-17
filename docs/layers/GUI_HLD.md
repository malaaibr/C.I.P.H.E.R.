# GUI — High-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | HLD-GUI-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Layer | GUI — Desktop User Interface |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dir | `cipher/gui/` |
| Authoritative sources | `cipher/gui/main_window.py`, `cipher/gui/app.py`, `cipher/gui/splash.py`, `docs/CIPHER_HLD.md` §11 area, `docs/CIPHER_LLD.md` §11, `docs/SESSION_HANDOFF.md` §2.1–2.6 and §4 |

---

## §1 Purpose & Scope

The GUI layer is the **top-most user-facing layer** of the 7-layer CIPHER stack.
It is a **single unified PyQt6 desktop application** that exposes two visually
distinct working modes inside one main window:

- **Mode 0 — CIPHER HUD**: A JARVIS-style 3-column dashboard (left nav list,
  center QStackedWidget of views, right system-status column) that serves as
  the landing screen and the system observation surface.
- **Mode 1 — DevNex Workspace**: A 2-column engineering workspace (220 px
  sidebar with 6 nav items + a stacked panel area + a 140 px colored log tail
  at the bottom) that drives the DevNex V-Cycle agent.

Mode switching is performed by a single `QStackedWidget` whose two children
are pre-built at window construction (`cipher/gui/main_window.py` lines
261–271). This is the unification of two previously separate applications;
see `docs/SESSION_HANDOFF.md` §2.1 and `docs/CODE_CHANGES_GUIDE.md` §1.

**In scope (this doc).**
- The unified PyQt6 desktop application under `cipher/gui/`
- The boot sequence (`run_poc.py` → splash → main window)
- The two display modes, the header bar, and the log tail
- The handoff to the DevNex agent's own GUI panels (consumed but not owned
  by this layer — they live under `cipher/agents/devnex_assistant/interfaces/gui/`)

**Out of scope.**
- DevNex panel internals (WorkflowPanel, TracePanel, ReviewPanel,
  OutputLogPanel, ConfigPanel) — they are documented under the AAL/DevNex
  layer doc
- Worker-thread business logic — workers themselves are owned by
  `devnex_assistant`; this layer only instantiates and signal-wires them
- The CIPHER backend servers (LLM Gateway :8200, A2A Server :8100) launched
  from `run_poc.py` in sibling threads

---

## §2 Position in the 7-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  GUI  (cipher/gui/)            ◄── this layer           │
│   ├─ Mode 0: CIPHER HUD dashboard                       │
│   └─ Mode 1: DevNex workspace (consumes AAL panels)     │
├─────────────────────────────────────────────────────────┤
│  AAL  (cipher/agents/)         agent implementations    │
│  ARE  (cipher/are/)            A2A server + skills      │
│  TRF  (cipher/trf/)            LLM Gateway              │
│  MKF / PKL / GCL / DRS                                  │
└─────────────────────────────────────────────────────────┘
```

GUI sits above AAL. It does not speak directly to TRF/ARE in the current
POC; instead it calls into a DevNex orchestrator instance that it lazily
constructs and that performs all backend work on its own QThread workers.

Per `CLAUDE.md` "Critical Design Decisions" #1, `main_window.py` injects
`cipher/agents/devnex_assistant/` into `sys.path` so DevNex's internal
imports (`from interfaces.gui.panels...`) resolve without rewriting the
agent's 90+ files. This is the layer's principal coupling to AAL.

---

## §3 External Interfaces

| Direction | Interface | Mechanism |
|---|---|---|
| In | Terminal launch | `python run_poc.py` (see `run_poc.py` line 41 `main()`) |
| In | Mouse / keyboard | Standard Qt event loop |
| In | File-system import | `ConfigPanel` "Import Config" file dialog (`SESSION_HANDOFF.md` §2.5) |
| Out | DevNex agent | Lazy `DevNexOrchestrator(run_context=ctx)` constructed in `_get_orchestrator()` (`main_window.py` lines 458–478) |
| Out | GCA invoker | `DevNexGCAInvoker(repo_path=...)` constructed in `_get_gca_invoker()` (lines 447–456); used to talk to a VS Code extension if present |
| Out | OS process | `subprocess.Popen(["code", "-g", target])` to open source files (`_open_in_editor`, lines 637–647) |
| Out | Backend servers | Not directly. `run_poc.py` starts LLM Gateway and A2A Server in daemon threads alongside the GUI |

The GUI never opens a socket of its own; backend access is exclusively via
in-process Python imports of the DevNex agent.

---

## §4 Internal Decomposition

```
cipher/gui/
├── app.py                       QApplication factory + launch()
├── splash.py                    Animated boot splash (SplashScreen)
├── theme.py                     JARVIS Blue HUD QSS (apply_theme)
├── main_window.py               CipherMainWindow + DevNexSidebar
├── panels/
│   ├── cipher_dashboard.py      Mode 0 — CipherDashboardPanel (3-col HUD)
│   ├── voice_panel.py           Voice interface (orb + waveform + log)
│   └── devnex/                  Local DevNex shim widgets (panel_descriptor,
│                                workflow_widget) — not the AAL panels
├── widgets/
│   ├── arc_reactor.py           ArcReactorWidget (4 states: idle / listening
│   │                             / processing / speaking)
│   ├── waveform.py              WaveformWidget (16-bar visualizer)
│   └── voice_orb.py             VoiceOrbWidget (pulsing concentric circles)
├── shell/
│   └── main_window.py           CipherShell (legacy ADR-0005 dock-based
│                                 shell; not on the current boot path)
└── client/
    ├── a2a_client.py            A2A HTTP client helper
    └── sse_client.py            Server-Sent Events client helper
```

The boot path uses `app.py → splash.py → main_window.py` only. `shell/` is
the older dock-based experiment retained for reference. `client/` contains
helpers reserved for future use; nothing on the current boot path imports
them.

---

## §5 Dependencies

**Hard dependencies (runtime imports):**
- `PyQt6` — `QtWidgets`, `QtCore`, `QtGui` (window, signals, painter)
- `cipher.gui.theme.apply_theme` — applied once in `create_app()`
- `cipher.agents.devnex_assistant.*` — injected via `sys.path`, imported
  lazily inside `main_window.py` (`WorkflowPanel`, `TracePanel`,
  `ReviewPanel`, `OutputLogPanel`, `ConfigPanel`, `StepIndicator`,
  `NodeWorker`, `FullRunWorker`, `ALL_NODE_IDS`)
- `cipher.core.orchestrator.CipherOrchestrator` — constructed in `run_poc.py`
  as the intended mother node (see §7 for the current wiring gap)

**Soft / try-except dependencies (graceful degradation):**
Every DevNex panel import is wrapped in `try: ... except Exception`. If a
panel fails to load (e.g., missing `interfaces.gui.styles.palette`), the
window falls back to `_placeholder(title, desc)` so the rest of the GUI
keeps working — see `main_window.py` lines 50–98 and `_placeholder()` at
404–417.

**Asset dependencies:**
- Fonts assumed installed on the host: `Segoe UI`, `Cascadia Code`, `Consolas`
  (declared in `cipher/gui/theme.py`)

---

## §6 Quality Attributes

| Attribute | Target | Mechanism |
|---|---|---|
| Splash timing | ~6 s total (120 ticks × 50 ms) + ~0.75 s fade | `splash.py` `_TOTAL_TICKS = 120`, `_TICK_MS = 50`, `_FADE_MS = 700` |
| Mode-switch latency | Instantaneous (single `setCurrentIndex` on a pre-built `QStackedWidget`) | `_switch_to_devnex` / `_switch_to_hud` in `main_window.py` lines 421–432 |
| Log-tail throughput | Bounded; ring buffer of 500 blocks | `QPlainTextEdit.setMaximumBlockCount(500)` at `main_window.py` line 395 |
| GUI responsiveness during runs | Main thread never blocks on agent work | All node execution runs in `QThread` workers (`NodeWorker`, `FullRunWorker`); review gates use `threading.Event.wait()` on the worker thread, not the GUI thread |
| Window-z order on Windows | Window must come to front after splash | `window.raise_()` + `window.activateWindow()` after `show()` in `run_poc.py` lines 76–78 |
| Theming | Single global QSS applied once | `apply_theme(app)` in `create_app()` |

---

## §7 Open Questions / Known Gaps

These are tracked verbatim against `docs/SESSION_HANDOFF.md` §4 — nothing
below is invented.

1. **Voice pipeline is not wired (§4.2).** `VoicePanel`, `ArcReactorWidget`,
   `WaveformWidget`, and `VoiceOrbWidget` render and animate, but there is
   no TTS/STT backend behind them. The voice UI is a visual-only
   placeholder in the MVP.

2. **CipherOrchestrator parent-child wiring is incomplete (§4.3).**
   `CipherOrchestrator` is constructed in `run_poc.py` (line 48) but is
   **not** passed into `CipherMainWindow`. The DevNex orchestrator built
   inside `_get_orchestrator()` is therefore not registered as a child of
   the CIPHER mother orchestrator. The intended fix is to pass
   `CipherOrchestrator` to the window and call
   `orchestrator.register_child("devnex", devnex_orch)`.

3. **End-to-end node execution unverified (§4.1).** The smoke test in
   §2.4 confirms construction and wiring, but a real `Run S1N1` against a
   workspace with SWC files has not been exercised end-to-end.

4. **`cipher/agents/devnex/` adapter status (§4.4).** `run_poc.py` still
   imports `S1N1Skill` from `cipher.agents.devnex.skills.vcycle_s1n1.skill`.
   The user has asked whether the `cipher/agents/devnex/` folder should be
   removed; that decision is pending and affects GUI imports only
   indirectly.

5. **Sub-package `__init__.py` completeness (§4.5).** Because
   `main_window.py` uses `sys.path` injection, some sub-packages under
   `cipher/gui/` may be missing `__init__.py` without breaking the current
   run. If/when import paths are normalised, those files must be added.

6. **HUD center views are largely placeholders.** Per
   `SESSION_HANDOFF.md` §8 step 4, "10 views in center QStackedWidget,
   most are placeholder." Filling these in is a follow-up.

7. **System status column is static.** Per `SESSION_HANDOFF.md` §8 step 5,
   service status pills are not yet driven by health-check polling.
