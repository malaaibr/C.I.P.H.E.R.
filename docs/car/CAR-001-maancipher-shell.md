# CAR-001: MainCipher Shell — Platform GUI Codebase Analysis Report

- **Status:** Accepted
- **Codebase path:** reference/MainCipherdevnex-assistant/MainCipherdevnex-assistant/
- **Analysed:** 2026-05-16
- **Reference tier:** PRIMARY
- **Architectural role:** Platform shell GUI (MANDATED CIPHER main window)

---

## 0. In-Scope Subdirectories (Mandatory — Anti-Conflation Statement)

This CAR analyses ONLY the frontend GUI scaffolding of the MainCipher platform shell. It covers the main window, panel slot architecture, navigation, styling, theme, animated boot sequence, dashboard layout, and packaging.

- **In scope:**
  - `src/devnex_agent/gui/` — all GUI modules (main_window.py, app.py, panels/, widgets/, styles/, workers/)
  - `src/devnex_agent/voice/` — voice controller integration points (as GUI feature, not agent logic)
  - `assets/` — fonts, icons, images used by the shell
  - Top-level packaging: `setup.py`, `pyproject.toml`, `*.spec` (if present)

- **Out of scope (covered by CAR-002):**
  - `src/devnex_agent/bridge/` — GCA bridge (agent backend)
  - `src/devnex_agent/core/` — orchestrator, intent classifier, workflow engine, types (agent backend)
  - `src/devnex_agent/skills/` — V-cycle skills (agent backend)
  - `src/devnex_agent/persistence/` — state/config stores (agent backend)
  - `src/devnex_agent/prompt_lib/` — prompt builders (agent backend)
  - `src/devnex_agent/cli/` — CLI entry point (agent backend)

---

## 1. Module Inventory

| File / Module | Role | Lines (approx.) |
|---|---|---|
| `gui/app.py` | Application entry point: creates QApplication, applies theme, launches MainWindow | ~37 |
| `gui/main_window.py` | QMainWindow: boot→welcome→dashboard stacked layout; header bar with ArcReactor; voice state machine | ~210 |
| `gui/panels/cipher_boot_panel.py` | Animated boot splash: QPainter canvas (hex grid, rings, particles), boot log sequence, progress bar, typewriter greeting, ENTER WORKSPACE button | ~603 |
| `gui/panels/cipher_dashboard_panel.py` | Full HUD workspace: left nav (10 views), center QStackedWidget, right status column; metric cards, stage cards, HITL gate UI, compliance bars | ~632 |
| `gui/panels/workflow_panel.py` | V-cycle workflow controls: stage list, run/approve/reject buttons, wired to orchestrator | ~180 |
| `gui/panels/trace_panel.py` | Traceability viewer: HLD→LLD→Code→Test chain display | ~140 |
| `gui/panels/config_form.py` | SWC project configuration form (SWC name, file paths, model selection) | ~120 |
| `gui/panels/voice_panel.py` | Voice command panel: transcript list, state display, start/stop | ~100 |
| `gui/panels/output_log.py` | Scrollable log output panel | ~70 |
| `gui/widgets/arc_reactor.py` | Animated arc reactor indicator with IDLE/LISTENING/PROCESSING/SPEAKING states | ~90 |
| `gui/widgets/welcome_overlay.py` | Fullscreen welcome overlay with reactor animation and dismiss signal | ~60 |
| `gui/styles/hud_theme.py` | GARVIS QSS theme: complete dark-blue HUD palette, font loading, 380-line stylesheet | ~404 |
| `gui/workers/worker_thread.py` | QThread worker for async skill dispatch (bridges GUI→backend) | ~100 |
| `gui/web_server.py` | Embedded web server for GUI↔backend bridge | ~80 |
| `voice/voice_controller.py` | VoiceController: state machine, wake word, TTS/STT orchestration (GUI feature) | ~130 |
| `voice/tts.py` | Text-to-speech driver (pyttsx3) | ~80 |
| `voice/stt.py` | Speech-to-text driver (SpeechRecognition) | ~80 |

**Total GUI shell code:** ~3,116 lines across 17 modules.

---

## 2. Public API Surface (GUI Shell Contract)

### 2.1 Application Entry

```python
# gui/app.py
def create_app() -> QApplication: ...
def main() -> None: ...
```

### 2.2 MainWindow (the shell)

```python
class MainWindow(QMainWindow):
    """Boot → welcome overlay → live HUD. THE platform shell."""
    _voice_state_changed: pyqtSignal(str)
    _transcript_sig: pyqtSignal(str, str)

    def __init__(self, orchestrator: Orchestrator) -> None: ...
    # Currently takes Orchestrator directly — CIPHER must replace with A2A client
```

### 2.3 CipherDashboardPanel (the workspace)

```python
class CipherDashboardPanel(QWidget):
    """Full HUD workspace with left nav, center stack, right column."""

    def inject_panel(self, nav_index: int, widget: QWidget) -> None:
        """Replace the center-stack view at nav_index with a real widget."""
        # THIS IS THE PANEL DOCKING MECHANISM — key for ADR-0005

    def set_listening(self, listening: bool) -> None: ...
    def on_transcript(self, full_text: str, command_text: str) -> None: ...
```

### 2.4 CipherBootPanel (boot sequence)

```python
class CipherBootPanel(QWidget):
    boot_complete: pyqtSignal()  # Emitted when user clicks ENTER WORKSPACE
```

### 2.5 Theme System

```python
# gui/styles/hud_theme.py
GARVIS_COLORS: dict[str, str]  # 18 named palette entries
GARVIS_QSS: str                # Complete 380-line QSS stylesheet
def apply_theme(app: QApplication) -> None: ...
def load_fonts() -> None: ...   # Loads Orbitron, ShareTechMono from assets/fonts/
```

---

## 3. Internal Dependencies

| Dependency | Version | Used For | Notes |
|---|---|---|---|
| PyQt5 | ≥5.15 | All GUI | Note: NOT PyQt6. CIPHER may need upgrade. |
| Orbitron font | — | HUD typography | Custom font loaded from assets/fonts/ |
| Share Tech Mono font | — | Code/log typography | Custom font loaded from assets/fonts/ |
| Exo 2 font | — | Body text | Referenced in QSS but not loaded explicitly (system fallback) |

**Critical observation:** The shell uses **PyQt5**, not PyQt6. The R2.0 protocol §1.5.1 references PyQt6. This is a version migration debt item.

**Backend coupling (to be severed in CIPHER):**
- `MainWindow.__init__` receives `orchestrator: Orchestrator` directly
- `WorkflowPanel` receives `orchestrator` for direct `dispatch()` calls
- `gui/app.py` imports `_build_orchestrator` from `cli/main.py`

These direct couplings must be replaced with A2A client calls in CIPHER.

---

## 4. State & Side Effects

The GUI shell itself persists NO state. All persistence flows through:
- `WorkflowPanel` → `orchestrator.dispatch()` → backend StateStore (not shell's concern)
- `VoiceController` → `orchestrator.dispatch()` → same path

The shell is purely a presentation layer. This is architecturally clean for CIPHER — the shell can be rewired to call A2A endpoints without internal state migration.

---

## 5. Mapping to CIPHER Layers

| Legacy Module | CIPHER Layer | CIPHER Target Path | Disposition | Reasoning |
|---|---|---|---|---|
| `gui/app.py` | GUI / shell | `gui/shell/app.py` | REFACTOR | Replace `_build_orchestrator()` with A2A client factory; upgrade PyQt5→PyQt6 |
| `gui/main_window.py` | GUI / shell | `gui/shell/main_window.py` | REFACTOR | Replace `Orchestrator` param with `CipherA2AClient`; add agent panel registry hook |
| `gui/panels/cipher_boot_panel.py` | GUI / shell | `gui/shell/boot_panel.py` | WRAP | Preserved as-is (pure animation, no backend coupling) |
| `gui/panels/cipher_dashboard_panel.py` | GUI / shell | `gui/shell/dashboard.py` | REFACTOR | `inject_panel()` becomes the formal docking API (ADR-0005); add dynamic agent discovery via ARE `GET /v1/agents` |
| `gui/panels/workflow_panel.py` | GUI / panels / devnex | `gui/panels/devnex/workflow_panel.py` | REFACTOR | Replace `orchestrator.dispatch()` with A2A TaskContract submission |
| `gui/panels/trace_panel.py` | GUI / panels / devnex | `gui/panels/devnex/trace_panel.py` | WRAP | Presentation-only; wire to MemoryAPI query for trace data |
| `gui/panels/config_form.py` | GUI / shell | `gui/shell/config_form.py` | WRAP | Project config is shell-level, not agent-specific |
| `gui/panels/voice_panel.py` | GUI / shell | `gui/shell/voice_panel.py` | WRAP | Voice is a shell feature (all agents can be commanded by voice) |
| `gui/panels/output_log.py` | GUI / shell | `gui/shell/output_log.py` | WRAP | Generic log viewer |
| `gui/widgets/arc_reactor.py` | GUI / widgets | `gui/widgets/arc_reactor.py` | WRAP | Pure visual — no changes needed |
| `gui/widgets/welcome_overlay.py` | GUI / widgets | `gui/widgets/welcome_overlay.py` | WRAP | Pure visual |
| `gui/styles/hud_theme.py` | GUI / shell | `gui/shell/styles/hud_theme.py` | REFACTOR | Upgrade PyQt5→PyQt6 QSS syntax; expose GARVIS_COLORS as theme tokens for panels |
| `gui/workers/worker_thread.py` | GUI / shell | `gui/shell/workers/async_worker.py` | REFACTOR | Replace direct orchestrator calls with async A2A/SSE client |
| `voice/` (all) | GUI / shell | `gui/shell/voice/` | WRAP | Voice is shell-level; TTS/STT hardware integration preserved |

---

## 6. Reusable Assets

### GUI Components (direct reuse in `cipher/gui/`)
- **CipherBootPanel** — full animated boot splash, production-quality. WRAP.
- **CipherDashboardPanel** — the 3-column HUD layout with `inject_panel()` docking. REFACTOR for dynamic agents.
- **ArcReactorWidget** — 4-state animated indicator. WRAP.
- **GarvisWelcomeOverlay** — dismissible overlay. WRAP.
- **HudPanel** — reusable card container widget. WRAP.
- **MetricCard** — numeric metric display widget. WRAP.
- **StageCard** — V-cycle stage status card. WRAP.
- **VoiceOrbWidget** — pulsing voice indicator. WRAP.
- **WaveformWidget** — audio waveform visualizer. WRAP.

### Theme System (direct reuse)
- **GARVIS_COLORS** palette (18 named colors) — becomes CIPHER shell theme token set.
- **GARVIS_QSS** (380 lines) — complete dark HUD stylesheet. Serves as the CIPHER platform theme.
- **Font stack:** Orbitron (headings), Share Tech Mono (code), Exo 2 (body).

### Navigation Architecture
- 10-item left nav list controlling a QStackedWidget center view.
- Nav items: Workflow, Traceability, Components, Artifacts, Voice, Config, Output, Compliance, Code Diff, Activity.
- This becomes the **agent panel registry** — each nav item maps to a registered agent panel.

---

## 7. Architectural Debt

### DEBT-001: PyQt5 Instead of PyQt6
- **Location:** All GUI modules — `from PyQt5.QtCore import ...`
- **Description:** Shell uses PyQt5. CIPHER §1.4 environment implies PyQt6 compatibility (the devnex_assistant reference uses PyQt6).
- **Impact:** API differences between PyQt5 and PyQt6 (exec_ → exec, setAttribute changes, enum namespacing).
- **Resolution:** Upgrade imports during REFACTOR. Most changes are mechanical. Target: T-GUI-001.

### DEBT-002: Direct Orchestrator Coupling
- **Location:** `gui/main_window.py:57`, `gui/app.py:25`, `gui/panels/workflow_panel.py`
- **Description:** MainWindow constructor takes `Orchestrator` instance directly. WorkflowPanel calls `orchestrator.dispatch()` synchronously.
- **Impact:** Cannot use shell without a local Orchestrator instance. Blocks A2A-based architecture.
- **Resolution:** Replace with `CipherA2AClient` interface. Shell submits TaskContracts via A2A; receives results via SSE. Target: ADR-0005, T-GUI-002.

### DEBT-003: Static Navigation (No Dynamic Agent Discovery)
- **Location:** `gui/panels/cipher_dashboard_panel.py:269-280`
- **Description:** Navigation items are hardcoded as a fixed list of 10 strings. No mechanism to add/remove agent panels at runtime.
- **Impact:** Cannot dynamically register new agent panels from the ARE Agent Registry.
- **Resolution:** Replace static list with dynamic agent discovery via `GET /v1/agents` from ARE. Each registered agent contributes a nav entry + panel widget. Target: ADR-0005, T-GUI-003.

### DEBT-004: No A2A Client Layer
- **Location:** N/A (does not exist)
- **Description:** No A2A client exists in the shell. All backend interaction is via direct Python function calls.
- **Impact:** Shell cannot communicate with the CIPHER backend via network protocols.
- **Resolution:** Implement `gui/client/a2a_client.py` (async httpx-based A2A JSON-RPC client) and `gui/client/sse_client.py` (SSE stream for task progress). Target: T-GUI-004.

---

## 8. Open Questions for Other Roles

- **For [LEAD]:** What is the effort to upgrade PyQt5→PyQt6? Is it a blocking prerequisite or can it be deferred to MVP?
- **For [DEV]:** The `inject_panel(nav_index, widget)` pattern is the seed of the docking contract — how should it evolve to support hot-registration of agent panels?
- **For [QA-TEST]:** Can the boot animation and dashboard be tested headlessly (QTest framework)?
- **For [QA-PROC]:** Does the boot sequence need compliance evidence (startup audit log)?

---

## 9. CIPHER Contracts Affected (Forward Brief)

| ADR / Task | Trigger from this CAR |
|---|---|
| **ADR-0005** (Shell-Panel Docking Contract) | `inject_panel()` pattern is the existing docking mechanism; must be formalized with agent discovery, lifecycle, and theming rules |
| **T-GUI-001** (PyQt5→PyQt6 Migration) | DEBT-001; mechanical upgrade of all imports and enum references |
| **T-GUI-002** (A2A Client Integration) | DEBT-002; replace direct orchestrator coupling with network client |
| **T-GUI-003** (Dynamic Agent Navigation) | DEBT-003; agent panel registry populated from ARE |
| **T-GUI-004** (A2A + SSE Client Module) | DEBT-004; implement `gui/client/` package |
| **T-GUI-005** (Shell Copy to cipher/gui/shell/) | Physical copy of shell modules to authoritative CIPHER path |

---

## 10. Summary Assessment

**Fitness for CIPHER integration: HIGH**

The MainCipher shell is a production-quality, visually polished platform GUI that already implements the shell + dockable-panel pattern CIPHER requires. The `CipherDashboardPanel.inject_panel()` method is a working prototype of the ADR-0005 docking contract. The boot sequence, theme system, and widget library are directly reusable.

The primary integration costs are: (a) upgrading PyQt5→PyQt6 (mechanical, ~2 days), (b) severing direct Orchestrator coupling and replacing with A2A client (~3 days), and (c) adding dynamic agent discovery to the navigation (~1 day). None of these are architectural blockers.

The shell is purely a presentation layer with zero internal state — this makes the A2A rewiring safe and testable in isolation.

**Recommended action:** REFACTOR the shell to accept an A2A client instead of a direct Orchestrator; WRAP all visual widgets and the boot panel unchanged; add the A2A/SSE client package as NEW code.
