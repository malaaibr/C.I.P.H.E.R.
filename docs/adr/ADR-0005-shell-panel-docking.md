---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# ADR-0005: Shell-Panel Docking Contract for the CIPHER Main GUI

- **Status:** Accepted
- **Deciders:** CIPHER Architecture Team
- **Date:** 2026-05-16
- **Layer:** GUI + ARE (cross-cutting: presentation and agent runtime)
- **Tags:** gui, shell, panel, docking, a2a, are, agent-registry

---

## 1. Context and Problem Statement

CIPHER's user-facing layer follows a **shell + dockable agent panels** architecture (§1.5.1). The MainCipher platform shell (CAR-001) provides a main window with a navigation sidebar and a center QStackedWidget. Each CIPHER agent gets its own panel inside the shell — the DevNex GUI (CAR-002) is the first such panel.

The existing shell has a working `inject_panel(nav_index, widget)` method (CAR-001 §2.3) that replaces views in the center stack. However, this is a static, hardcoded mechanism — panels are injected at fixed indices by the MainWindow constructor. There is no:

1. Dynamic agent discovery (panels can't register themselves at runtime)
2. Standard panel lifecycle contract (mount, unmount, error states)
3. Communication protocol between panels and the backend (currently direct Python function calls)
4. Theming discipline (panels could override shell styles)
5. Agent Registry integration (shell doesn't query ARE for available agents)

This ADR defines the canonical docking contract that formalizes how agent panels integrate with the shell.

---

## 2. Decision Drivers

- **CAR-001 (MainCipher Shell):** Existing `inject_panel()` pattern must evolve, not be replaced. The shell's 3-column HUD layout is preserved.
- **CAR-002 (DevNex Agent):** The standalone DevNex GUI (PyQt6) must dock as the first agent panel. Its `StepIndicator`, trace panels, and review dialog become panel-internal widgets.
- **§1.5.1 mandate:** No new top-level GUI. Every agent gets a panel inside the shell.
- **A2A contract:** Panels submit TaskContracts to the Orchestrator via A2A; receive updates via SSE.
- **Agent Registry (ARE):** Shell discovers available agents via `GET /v1/agents` at startup and on refresh.
- **Future agents:** The contract must support Planner, ASIL Reviewer, Compliance, Research, Garvis panels without shell code changes.

---

## 3. Considered Options

### Option A: Static Panel Registration (Current Pattern)
Keep `inject_panel(nav_index, widget)` as-is. Each new panel requires a code change in MainWindow.

**Pros:** Simple, no runtime complexity.
**Cons:** Cannot add panels without modifying shell source; no agent discovery; violates open/closed principle; blocks the "9 agents, 9 panels" future.

### Option B: Dynamic Panel Registry with Agent Card Discovery (Selected)
Panels register via a `PanelDescriptor` protocol. The shell queries the ARE Agent Registry for available agents and mounts panels dynamically.

**Pros:** Open/closed compliant; supports any number of agents; clean separation; panels are self-contained packages.
**Cons:** Slightly more complex initialization; requires A2A client in shell.

### Option C: Plugin Architecture with Dynamic Loading
Load panel code from separate packages at runtime via `importlib`.

**Pros:** Maximum decoupling.
**Cons:** Over-engineered for Local MVP; adds packaging complexity; debugging across plugin boundaries is painful.

---

## 4. Decision

**Option B: Dynamic Panel Registry with Agent Card Discovery.**

The shell at startup queries the ARE Agent Registry (`GET /v1/agents`) to discover available agents. Each agent that has a GUI panel provides a `PanelDescriptor` in its Agent Card metadata. The shell instantiates panel widgets dynamically, adds them to the navigation sidebar, and inserts them into the center QStackedWidget.

---

## 5. The Docking Contract

### 5.1 PanelDescriptor Protocol

Every agent that provides a GUI panel MUST expose a `PanelDescriptor` — a Python protocol that the shell uses to mount the panel.

```python
from typing import Protocol
from PyQt6.QtWidgets import QWidget


class PanelDescriptor(Protocol):
    """Contract between an agent panel and the CIPHER shell."""

    @property
    def agent_id(self) -> str:
        """Unique agent identifier (e.g., 'AGT-001')."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for navigation sidebar."""
        ...

    @property
    def icon_name(self) -> str:
        """Icon identifier from the CIPHER icon set."""
        ...

    @property
    def nav_order(self) -> int:
        """Position in the navigation sidebar (0 = first)."""
        ...

    def create_widget(self, client: "CipherShellClient") -> QWidget:
        """
        Instantiate the panel widget.
        The shell passes a CipherShellClient that the panel uses for
        all backend communication (A2A, SSE, MemoryAPI).
        """
        ...

    def on_mount(self) -> None:
        """Called when the panel is added to the shell."""
        ...

    def on_focus(self) -> None:
        """Called when the user navigates to this panel."""
        ...

    def on_unfocus(self) -> None:
        """Called when the user navigates away."""
        ...

    def on_unmount(self) -> None:
        """Called when the panel is removed (agent deregistered)."""
        ...
```

### 5.2 CipherShellClient (Provided by Shell to Panels)

The shell provides a `CipherShellClient` to every panel at creation time. This is the ONLY interface panels use to reach the backend.

```python
class CipherShellClient:
    """Shell-provided client for panel→backend communication."""

    async def submit_task(self, contract: TaskContract) -> str:
        """Submit a TaskContract to the Orchestrator via A2A. Returns task_id."""
        ...

    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Poll task status."""
        ...

    def subscribe_task_updates(self, task_id: str, callback: Callable[[TaskUpdate], None]) -> None:
        """Subscribe to SSE stream for real-time task progress."""
        ...

    async def query_memory(self, query: str, top_k: int = 5) -> list[MemoryResult]:
        """Query the MKF MemoryAPI."""
        ...

    def request_hitl_approval(self, gate_id: str, context: dict) -> None:
        """Surface a HITL gate in the shell's HITL pane."""
        ...

    def emit_status(self, message: str, level: str = "info") -> None:
        """Show a status message in the shell status bar."""
        ...
```

### 5.3 Agent Registry Discovery

At shell startup and on explicit refresh:

1. Shell calls `GET http://localhost:{ARE_PORT}/v1/agents`
2. ARE returns a list of Agent Cards (A2A `AgentCard` schema)
3. For each agent with `metadata.gui_panel = true`:
   - Shell imports the panel module from `gui/panels/{agent_name}/`
   - Calls `get_panel_descriptor()` module-level function
   - Mounts the panel via the descriptor contract
4. Navigation sidebar is rebuilt with discovered panels sorted by `nav_order`

### 5.4 Panel Registration (Static Fallback for POC)

For POC (before ARE is fully operational), panels are registered statically in `gui/shell/panel_registry.py`:

```python
STATIC_PANELS: list[PanelDescriptor] = [
    DevNexPanelDescriptor(),    # nav_order=0
    # Future: PlannerPanelDescriptor(), ASILPanelDescriptor(), ...
]
```

Once ARE is operational (MVP), the static registry is replaced by dynamic discovery. Both paths produce the same `list[PanelDescriptor]` — the shell doesn't know which source provided them.

### 5.5 Shell ↔ Panel Communication Rules

1. **Panels NEVER import shell internals.** Communication flows only through `CipherShellClient`.
2. **Panels NEVER import other panels.** No cross-panel imports. Shared widgets live in `gui/widgets/`.
3. **Panels NEVER call backend services directly.** All backend access goes through `CipherShellClient` methods (which internally use A2A/REST/SSE).
4. **Panels respect shell theme tokens.** Panels import `gui/shell/styles/theme_tokens.py` for colors, fonts, and spacing. Custom panel styling must use these tokens as the base.
5. **Panels are self-contained packages.** Each panel lives in `gui/panels/{agent_name}/` with its own `__init__.py` exporting `get_panel_descriptor()`.

### 5.6 HITL Gate Surfacing

When a panel's task reaches a HITL gate (LangGraph `interrupt()`):

1. Panel calls `client.request_hitl_approval(gate_id, context)`
2. Shell's HITL pane (bottom bar per §1.5.1) renders the gate with approve/reject buttons
3. User decision flows back via `CipherShellClient` → A2A → GCL HITL Gate Manager → LangGraph `resume()`
4. Panel receives the resume event via SSE subscription and updates its UI

### 5.7 Panel Lifecycle State Machine

```
REGISTERED → MOUNTING → MOUNTED → FOCUSED ↔ UNFOCUSED → UNMOUNTING → REMOVED
                                      ↓
                                   ERROR (panel crash → shell shows error card)
```

---

## 6. Rationale

This contract provides the minimum viable docking mechanism while supporting the full 9-agent panel ecosystem. The `PanelDescriptor` protocol is simple enough for POC (5 properties + 4 lifecycle methods) but extensible for MVP (add `supports_voice`, `required_permissions`, etc.). The `CipherShellClient` abstraction ensures panels are testable in isolation — inject a mock client in tests.

---

## 7. Consequences

- **Positive:** Any new agent can add a GUI panel without touching shell code. Panels are independently testable. Backend coupling is eliminated.
- **Positive:** The existing MainCipher shell layout (3-column HUD) is preserved — only the panel injection mechanism changes.
- **Negative:** POC requires implementing `CipherShellClient` even if only partially (A2A may not be ready — stub with direct calls initially).
- **Neutral:** The DevNex standalone GUI must be refactored into a `PanelDescriptor`-compliant package. This is mechanical but touches ~20 files.

---

## 8. Compliance Notes

- HITL gate surfacing in the shell satisfies ISO 26262-6 requirement for human oversight of irreversible actions.
- Panel isolation (no direct backend access) supports audit trail requirements — all panel actions route through audited `CipherShellClient` methods.

---

## 9. Affected Layers

- **GUI** — shell docking mechanism, panel registry, CipherShellClient
- **ARE** — Agent Registry `/v1/agents` endpoint must include `metadata.gui_panel` flag
- **AAL** — each agent with a panel provides a `PanelDescriptor` in its package

---

## 10. Reference Codebase Impact

- **CARs consulted:** CAR-001 (MainCipher Shell), CAR-002 (DevNex Agent)
- **Wrap/Refactor/Rewrite decisions per legacy module:**

| Legacy module | Disposition | Reasoning |
|---|---|---|
| MainCipher `CipherDashboardPanel.inject_panel()` | REFACTOR | Evolve from static index-based to dynamic `PanelDescriptor`-based registration |
| MainCipher navigation list (10 hardcoded items) | REFACTOR | Replace with dynamic list populated from Agent Registry |
| DevNex standalone `MainWindow` | REFACTOR | Decompose into `DevNexPanelDescriptor` + panel widget (remove standalone window chrome) |
| DevNex `StepIndicator` | WRAP | Moved into panel-internal layout unchanged |
| DevNex `TracePanel`, `WorkflowPanel` | WRAP | Become sub-widgets of the DevNex panel |

- **Reused assets:** All DevNex GUI widgets are preserved inside the panel package. MainCipher shell widgets (ArcReactor, HudPanel, MetricCard) remain in `gui/widgets/` for shared use.

---

## 11. Implementation Hint

The Tech Lead should plan this as three tasks: (1) implement `CipherShellClient` with A2A submission (stub SSE for POC), (2) refactor the DevNex standalone GUI into a `PanelDescriptor` package at `gui/panels/devnex/`, (3) modify the shell's `CipherDashboardPanel` to accept panels via descriptors instead of hardcoded indices. Task (2) is the largest — it requires stripping the standalone `QMainWindow` wrapper and keeping only the panel content widget.
