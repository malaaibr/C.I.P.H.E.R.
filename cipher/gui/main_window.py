"""
CipherMainWindow — Unified GUI integrating CIPHER HUD + DevNex Workspace.

Layout modes:
  Mode 0 (CIPHER HUD): 3-column dashboard — nav + center views + right status
  Mode 1 (DevNex):      2-column workspace — sidebar + panel stack + log tail

DevNex orchestrator is wired as child of CIPHER orchestrator.
Worker threads (NodeWorker, FullRunWorker) execute V-cycle nodes in background.
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from cipher.gui.panels.cipher_dashboard import CipherDashboardPanel
from cipher.gui.panels.voice_panel import VoicePanel
from cipher.gui.widgets.arc_reactor import ArcReactorWidget

log = logging.getLogger(__name__)

# ── Inject devnex_assistant onto sys.path so its internal imports resolve ─────
_DEVNEX_ROOT = Path(__file__).resolve().parent.parent / "agents" / "devnex_assistant"
if str(_DEVNEX_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEVNEX_ROOT))

# ── Import real DevNex panels ─────────────────────────────────────────────────
_WorkflowPanel = None
_ReviewDialog = None
_TracePanel = None
_ReviewPanel = None
_OutputLogPanel = None
_ConfigPanel = None
_StepIndicator = None
_StepState = None
_NodeWorker = None
_FullRunWorker = None
_ALL_NODE_IDS = None

try:
    from interfaces.gui.panels.workflow_panel import WorkflowPanel as _WorkflowPanel, ReviewDialog as _ReviewDialog
except Exception as e:
    log.warning("Could not load WorkflowPanel: %s", e)

try:
    from interfaces.gui.panels.trace_panel import TracePanel as _TracePanel
except Exception as e:
    log.warning("Could not load TracePanel: %s", e)

try:
    from interfaces.gui.panels.review_panel import ReviewPanel as _ReviewPanel
except Exception as e:
    log.warning("Could not load ReviewPanel: %s", e)

try:
    from interfaces.gui.panels.output_log import OutputLogPanel as _OutputLogPanel
except Exception as e:
    log.warning("Could not load OutputLogPanel: %s", e)

try:
    from interfaces.gui.panels.config_panel import ConfigPanel as _ConfigPanel
except Exception as e:
    log.warning("Could not load ConfigPanel: %s", e)

try:
    from interfaces.gui.step_indicator import StepIndicator as _StepIndicator, StepState as _StepState
except Exception as e:
    log.warning("Could not load StepIndicator: %s", e)

try:
    from interfaces.gui.workers.node_worker import NodeWorker as _NodeWorker
except Exception as e:
    log.warning("Could not load NodeWorker: %s", e)

try:
    from interfaces.gui.workers.full_run_worker import FullRunWorker as _FullRunWorker
except Exception as e:
    log.warning("Could not load FullRunWorker: %s", e)

try:
    from interfaces.gui.constants import ALL_NODE_IDS as _ALL_NODE_IDS
except Exception as e:
    log.warning("Could not load ALL_NODE_IDS: %s", e)

try:
    from interfaces.gui.styles import palette as _palette
except Exception:
    _palette = None


# ── Navigation labels ─────────────────────────────────────────────────────────
_DEVNEX_NAV_WORKFLOW = "Workflow"
_DEVNEX_NAV_TRACE = "Trace"
_DEVNEX_NAV_REVIEW = "Review"
_DEVNEX_NAV_OUTPUT = "Output"
_DEVNEX_NAV_CONFIG = "Config"
_DEVNEX_NAV_VOICE = "Voice"
_DEVNEX_NAV_ITEMS = [
    _DEVNEX_NAV_WORKFLOW, _DEVNEX_NAV_TRACE, _DEVNEX_NAV_REVIEW,
    _DEVNEX_NAV_OUTPUT, _DEVNEX_NAV_CONFIG, _DEVNEX_NAV_VOICE,
]

# Colors
_LOG_COLORS = {
    "INFO": "#4fc3f7", "ERROR": "#ff7b72", "WARN": "#e3b341",
    "SUCCESS": "#3fb950", "ts": "#8b949e", "step": "#79c0ff",
}

_ACCENT = "#00c8ff"
_GREEN = "#00ff9d"
_WARN = "#ffb700"
_MUTED = "#2d5f7a"
_BG = "#010a15"
_PANEL = "#041624"

_DEFAULT_ARTIFACTS_DIR = Path("generated_artifacts")

_STEP_NODE_MAP: dict[str, int] = {
    "S1": 0, "S2": 1, "S3": 2, "S4": 3, "S5": 4,
    "S6": 5, "S7": 6, "S8": 7, "S9": 8,
}


def _infer_level(msg: str) -> str:
    upper = msg.upper()
    if any(k in upper for k in ("ERROR", "FAIL", "EXCEPTION")):
        return "ERROR"
    if any(k in upper for k in ("WARN", "WARNING")):
        return "WARN"
    if any(k in upper for k in ("SUCCESS", "COMPLETE", "DONE")):
        return "SUCCESS"
    return "INFO"


class DevNexSidebar(QFrame):
    """Sidebar for DevNex 2-column mode."""

    nav_clicked = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color:{_PANEL};border-right:1px solid rgba(0,200,255,0.18);")
        self._buttons: dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 8)
        root.setSpacing(4)

        back_btn = QPushButton("← CIPHER HUD")
        back_btn.setFixedHeight(34)
        back_btn.setStyleSheet(
            f"QPushButton{{background:rgba(0,200,255,0.08);border:1px solid rgba(0,200,255,0.3);"
            f"color:{_ACCENT};border-radius:4px;font-size:9pt;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:rgba(0,200,255,0.15);}}"
        )
        back_btn.clicked.connect(lambda: self.nav_clicked.emit("__BACK__"))
        root.addWidget(back_btn)
        root.addSpacing(12)

        title = QLabel("DevNex")
        title.setStyleSheet(f"color:{_ACCENT};font-size:14pt;font-weight:bold;letter-spacing:3px;")
        root.addWidget(title)
        sub = QLabel("V-Cycle Engine")
        sub.setStyleSheet(f"color:{_MUTED};font-size:9pt;")
        root.addWidget(sub)
        root.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:rgba(0,200,255,0.18);")
        sep.setFixedHeight(1)
        root.addWidget(sep)
        root.addSpacing(8)

        for label in _DEVNEX_NAV_ITEMS:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._btn_style(False))
            btn.clicked.connect(lambda _, lbl=label: self._on_click(lbl))
            self._buttons[label] = btn
            root.addWidget(btn)
            root.addSpacing(2)

        root.addStretch()

        footer = QLabel("v1.0.0-MVP")
        footer.setStyleSheet(f"color:{_MUTED};font-size:8pt;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

    def _on_click(self, label: str) -> None:
        self.set_active(label)
        self.nav_clicked.emit(label)

    def set_active(self, label: str) -> None:
        for lbl, btn in self._buttons.items():
            btn.setStyleSheet(self._btn_style(lbl == label))

    @staticmethod
    def _btn_style(active: bool) -> str:
        if active:
            return (
                f"QPushButton{{background:{_ACCENT};color:#010a15;"
                f"border-radius:5px;text-align:left;padding:6px 10px;font-size:10pt;font-weight:bold;}}"
            )
        return (
            f"QPushButton{{background:transparent;color:#b8e8ff;"
            f"border-radius:5px;text-align:left;padding:6px 10px;font-size:10pt;}}"
            f"QPushButton:hover{{background:rgba(0,200,255,0.08);color:{_ACCENT};}}"
        )


class CipherMainWindow(QMainWindow):
    """
    Unified CIPHER + DevNex main window.

    Mode 0: CipherDashboardPanel (3-column HUD)
    Mode 1: DevNex workspace (sidebar + panel stack + log tail)

    DevNex orchestrator is lazily created on first node run and wired
    to workers that execute V-cycle nodes in background QThreads.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("C.I.P.H.E.R — V-Cycle Intelligence Platform")
        self.resize(1360, 880)
        self.setMinimumSize(1100, 700)

        self._workers: list = []
        self._active_worker = None
        self._orchestrator = None
        self._gca_invoker = None

        self._build_ui()
        self.statusBar().showMessage("C.I.P.H.E.R  |  ONLINE  |  A2A :8100  |  LLM :8200")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self._mode_stack = QStackedWidget()

        # Mode 0: CIPHER Dashboard
        self._dashboard = CipherDashboardPanel(on_devnex=self._switch_to_devnex)
        self._mode_stack.addWidget(self._dashboard)

        # Mode 1: DevNex Workspace
        self._devnex_widget = self._build_devnex_workspace()
        self._mode_stack.addWidget(self._devnex_widget)

        root.addWidget(self._mode_stack, stretch=1)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(
            "QWidget{background:rgba(1,8,22,0.97);"
            "border-bottom:1px solid rgba(0,200,255,0.18);}"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 4, 12, 4)
        hl.setSpacing(10)

        self._arc_reactor = ArcReactorWidget(size=40)
        self._arc_reactor.set_state(ArcReactorWidget.IDLE)
        hl.addWidget(self._arc_reactor)

        title = QLabel("C.I.P.H.E.R")
        title.setStyleSheet(f"color:{_ACCENT};font-size:14pt;font-weight:bold;letter-spacing:4px;")
        hl.addWidget(title)

        self._mode_label = QLabel("HUD")
        self._mode_label.setStyleSheet(
            f"color:{_MUTED};font-size:9pt;letter-spacing:2px;padding:2px 8px;"
            f"border:1px solid rgba(0,200,255,0.2);border-radius:3px;"
        )
        hl.addWidget(self._mode_label)

        self._status_badge = QLabel("● Idle")
        self._status_badge.setStyleSheet(
            f"background-color:rgba(0,200,255,0.08);color:{_ACCENT};"
            f"font-size:9pt;padding:2px 8px;border-radius:3px;"
        )
        hl.addWidget(self._status_badge)

        self._voice_label = QLabel("VOICE: IDLE")
        self._voice_label.setStyleSheet(f"color:{_MUTED};font-size:9pt;")
        hl.addStretch()
        hl.addWidget(self._voice_label)
        return header

    # ── DevNex Workspace (Mode 1) ─────────────────────────────────────────────

    def _build_devnex_workspace(self) -> QWidget:
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QWidget()
        cl = QHBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._devnex_sidebar = DevNexSidebar()
        self._devnex_sidebar.nav_clicked.connect(self._on_devnex_nav)
        cl.addWidget(self._devnex_sidebar)

        self._devnex_stack = QStackedWidget()

        # Step indicator (hidden but used for signal wiring)
        if _StepIndicator is not None:
            self._step_indicator = _StepIndicator()
        else:
            self._step_indicator = None

        # 0: Workflow
        if _WorkflowPanel is not None:
            self._workflow_panel = _WorkflowPanel()
            self._workflow_panel.node_run_requested.connect(self._on_node_run_requested)
            self._workflow_panel.run_all_requested.connect(self._on_run_all_requested)
            self._workflow_panel.reset_requested.connect(self._on_reset_requested)
        else:
            self._workflow_panel = self._placeholder("Workflow Panel", "WorkflowPanel failed to load.")
        self._devnex_stack.addWidget(self._workflow_panel)

        # 1: Trace
        if _TracePanel is not None:
            self._trace_panel = _TracePanel(
                artifacts_dir=_DEFAULT_ARTIFACTS_DIR,
                on_open_source=self._open_in_editor,
            )
        else:
            self._trace_panel = self._placeholder("Trace Panel", "TracePanel failed to load.")
        self._devnex_stack.addWidget(self._trace_panel)

        # 2: Review
        if _ReviewPanel is not None:
            self._review_panel = _ReviewPanel()
        else:
            self._review_panel = self._placeholder("Review Panel", "ReviewPanel failed to load.")
        self._devnex_stack.addWidget(self._review_panel)

        # 3: Output Log
        if _OutputLogPanel is not None:
            self._output_panel = _OutputLogPanel()
        else:
            self._output_panel = self._placeholder("Output Log", "OutputLogPanel failed to load.")
        self._devnex_stack.addWidget(self._output_panel)

        # 4: Config
        if _ConfigPanel is not None:
            self._config_panel = _ConfigPanel()
            if hasattr(self._config_panel, "config_saved"):
                self._config_panel.config_saved.connect(self._on_config_saved)
        else:
            self._config_panel = self._placeholder("Config Panel", "ConfigPanel failed to load.")
        self._devnex_stack.addWidget(self._config_panel)

        # 5: Voice
        self._devnex_voice = VoicePanel()
        self._devnex_stack.addWidget(self._devnex_voice)

        cl.addWidget(self._devnex_stack, stretch=1)
        root.addWidget(content, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:rgba(0,200,255,0.18);")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        self._log_tail = QPlainTextEdit()
        self._log_tail.setReadOnly(True)
        self._log_tail.setMaximumBlockCount(500)
        self._log_tail.setFixedHeight(140)
        self._log_tail.setStyleSheet(
            f"background-color:#020d1a;color:{_MUTED};"
            f"font-family:'Cascadia Code','Consolas',monospace;font-size:9pt;border:none;"
        )
        root.addWidget(self._log_tail)
        return container

    @staticmethod
    def _placeholder(title: str, desc: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet(f"color:{_ACCENT};font-size:16pt;font-weight:bold;")
        d = QLabel(desc)
        d.setStyleSheet(f"color:{_MUTED};font-size:10pt;")
        d.setWordWrap(True)
        layout.addWidget(t)
        layout.addSpacing(8)
        layout.addWidget(d)
        return w

    # ── Mode switching ─────────────────────────────────────────

    def _switch_to_devnex(self) -> None:
        self._mode_stack.setCurrentIndex(1)
        self._mode_label.setText("DevNex")
        self._arc_reactor.set_state(ArcReactorWidget.PROCESSING)
        self._devnex_sidebar.set_active(_DEVNEX_NAV_WORKFLOW)
        self.statusBar().showMessage("C.I.P.H.E.R  |  DevNex WORKSPACE  |  V-Cycle Engine")

    def _switch_to_hud(self) -> None:
        self._mode_stack.setCurrentIndex(0)
        self._mode_label.setText("HUD")
        self._arc_reactor.set_state(ArcReactorWidget.IDLE)
        self.statusBar().showMessage("C.I.P.H.E.R  |  ONLINE  |  A2A :8100  |  LLM :8200")

    def _on_devnex_nav(self, label: str) -> None:
        if label == "__BACK__":
            self._switch_to_hud()
            return
        idx_map = {
            _DEVNEX_NAV_WORKFLOW: 0, _DEVNEX_NAV_TRACE: 1,
            _DEVNEX_NAV_REVIEW: 2, _DEVNEX_NAV_OUTPUT: 3,
            _DEVNEX_NAV_CONFIG: 4, _DEVNEX_NAV_VOICE: 5,
        }
        self._devnex_stack.setCurrentIndex(idx_map.get(label, 0))

    # ── DevNex Orchestrator (lazy init — child of CipherOrchestrator) ─────────

    def _get_gca_invoker(self):
        if self._gca_invoker is None:
            try:
                from gca.vscode_invoker import DevNexGCAInvoker
                config = self._get_config()
                repo_path = Path(config.get("workspace_path", "."))
                self._gca_invoker = DevNexGCAInvoker(repo_path=repo_path)
            except Exception as e:
                self.append_log(f"GCA Invoker init failed: {e}", level="WARN")
        return self._gca_invoker

    def _get_orchestrator(self):
        if self._orchestrator is None:
            try:
                from core.run_context import DevNexRunContext
                from core.orchestrator import DevNexOrchestrator

                config = self._get_config()
                ctx = DevNexRunContext(
                    swc_name=config.get("SWC_name", "SWC"),
                    workspace_path=config.get("workspace_path", "."),
                )
                self._orchestrator = DevNexOrchestrator(run_context=ctx)

                gca = self._get_gca_invoker()
                if gca is not None:
                    self._orchestrator._gca_invoker = gca

                self.append_log("DevNex orchestrator initialized.", level="SUCCESS")
            except Exception as e:
                self.append_log(f"Orchestrator init failed: {e}", level="ERROR")
        return self._orchestrator

    def _get_config(self) -> dict:
        if _ConfigPanel is not None and hasattr(self._config_panel, "get_config"):
            return self._config_panel.get_config()
        return {}

    # ── Worker / run logic (mirrors devnex_assistant MainWindow) ──────────────

    def _on_node_run_requested(self, node_id: str) -> None:
        if _NodeWorker is None:
            self.append_log("NodeWorker not available.", step=node_id, level="ERROR")
            return

        orchestrator = self._get_orchestrator()
        if orchestrator is None:
            self.append_log("Orchestrator not available.", step=node_id, level="ERROR")
            return

        worker = _NodeWorker(orchestrator, node_id)
        self._wire_worker(worker)
        self._active_worker = worker
        self._workers.append(worker)

        if _WorkflowPanel is not None:
            self._workflow_panel.set_running(True)
        self._set_status("Running", _WARN)
        self.append_log(f"Starting node {node_id}...", step=node_id)
        worker.start()

    def _on_run_all_requested(self) -> None:
        if _FullRunWorker is None:
            self.append_log("FullRunWorker not available.", level="ERROR")
            return

        orchestrator = self._get_orchestrator()
        if orchestrator is None:
            self.append_log("Orchestrator not available.", level="ERROR")
            return

        worker = _FullRunWorker(orchestrator)
        self._wire_worker(worker)
        self._active_worker = worker
        self._workers.append(worker)

        if _WorkflowPanel is not None:
            self._workflow_panel.set_running(True)
        self._set_status("Running", _WARN)
        self.append_log("Starting full V-cycle run (S1N1 → S9N1)...", step="System")
        worker.start()

    def _wire_worker(self, worker) -> None:
        worker.log_line.connect(lambda msg, lvl: self.append_log(msg, level=lvl))
        worker.node_started.connect(self._on_node_started)
        worker.node_complete.connect(self._on_node_complete)
        worker.review_needed.connect(self._on_review_needed)
        worker.error_occurred.connect(self._on_worker_error)
        if hasattr(worker, "result_signal"):
            worker.result_signal.connect(self._on_run_finished)
        if hasattr(worker, "progress"):
            worker.progress.connect(
                lambda pct, msg: self.append_log(f"[{pct}%] {msg}", level="INFO")
            )

    def _on_node_started(self, node_id: str) -> None:
        if _WorkflowPanel is not None and hasattr(self._workflow_panel, "set_node_status"):
            self._workflow_panel.set_node_status(node_id, "running")
        if self._step_indicator is not None and _StepState is not None:
            stage_key = node_id[:2]
            step_idx = _STEP_NODE_MAP.get(stage_key, 0)
            self._step_indicator.update_step(step_idx, _StepState.ACTIVE)
        self.append_log(f"Node {node_id} started.", step=node_id, level="INFO")

    def _on_node_complete(self, result) -> None:
        status = getattr(result, "status", "done")
        node_id = getattr(result, "node_id", "?")

        if _WorkflowPanel is not None and hasattr(self._workflow_panel, "set_node_status"):
            self._workflow_panel.set_node_status(node_id, status)
        if _WorkflowPanel is not None and hasattr(self._workflow_panel, "show_node_detail"):
            artifacts = getattr(result, "artifacts", [])
            self._workflow_panel.show_node_detail(node_id, status, artifacts)

        if self._step_indicator is not None and _StepState is not None:
            stage_key = node_id[:2]
            step_idx = _STEP_NODE_MAP.get(stage_key, 0)
            if status in ("complete", "done"):
                self._step_indicator.update_step(step_idx, _StepState.COMPLETE)
            else:
                self._step_indicator.update_step(step_idx, _StepState.ERROR)

        level = "SUCCESS" if status in ("complete", "done") else "ERROR"
        self.append_log(f"Node {node_id} → {status}.", step=node_id, level=level)

        # Refresh trace graph
        if _TracePanel is not None and hasattr(self._trace_panel, "update_from_state"):
            self._trace_panel.update_from_state({"node_id": node_id, "status": status})

    def _on_review_needed(self, node_id: str, message: str) -> None:
        if _ReviewDialog is not None:
            dlg = _ReviewDialog(node_id, message, parent=self)
            approved = dlg.exec() == dlg.DialogCode.Accepted
        else:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, f"Review Gate — {node_id}",
                f"{message}\n\nApprove and continue?",
            )
            approved = reply == QMessageBox.StandardButton.Yes

        if self._active_worker is not None:
            self._active_worker.resume(approved)
        if not approved:
            self.append_log(f"Human review gate aborted at {node_id}.", level="WARN")

    def _on_worker_error(self, msg: str) -> None:
        self.append_log(msg, level="ERROR")
        if _WorkflowPanel is not None and hasattr(self._workflow_panel, "set_running"):
            self._workflow_panel.set_running(False)
        self._set_status("Error", "#ff3a3a")
        self._active_worker = None

    def _on_run_finished(self, _result) -> None:
        if _WorkflowPanel is not None and hasattr(self._workflow_panel, "set_running"):
            self._workflow_panel.set_running(False)
        self._set_status("Idle", _ACCENT)
        self.append_log("Run complete.", level="SUCCESS")
        self._active_worker = None

    def _on_reset_requested(self) -> None:
        self._orchestrator = None
        if self._step_indicator is not None:
            self._step_indicator.reset_all()
        if _ALL_NODE_IDS is not None and _WorkflowPanel is not None:
            for nid in _ALL_NODE_IDS:
                if hasattr(self._workflow_panel, "set_node_status"):
                    self._workflow_panel.set_node_status(nid, "idle")
        try:
            from persistence.state_store import StateStore
            StateStore().reset()
        except Exception:
            pass
        self.append_log("Workflow state reset.", level="INFO")
        self._set_status("Idle", _ACCENT)

    def _on_config_saved(self, config: dict) -> None:
        self._orchestrator = None
        swc = config.get("SWC_name", "")
        self.append_log(f"Config saved. SWC = '{swc}'.", level="SUCCESS")

    # ── Helpers ────────────────────────────────────────────────

    def _set_status(self, text: str, color: str) -> None:
        self._status_badge.setText(f"● {text}")
        self._status_badge.setStyleSheet(
            f"background-color:rgba(0,200,255,0.08);color:{color};"
            f"font-size:9pt;padding:2px 8px;border-radius:3px;"
        )

    def _open_in_editor(self, path: str, line_no: int) -> None:
        import os
        import subprocess
        try:
            target = f"{path}:{line_no}" if line_no else path
            subprocess.Popen(["code", "-g", target])
        except Exception:
            try:
                os.startfile(path)
            except Exception as exc:
                log.warning("Could not open %s: %s", path, exc)

    # ── Log tail ───────────────────────────────────────────────

    def append_log(self, msg: str, step: str = "System", level: str | None = None) -> None:
        if level is None:
            level = _infer_level(msg)

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        cursor = self._log_tail.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        def _insert(text: str, color_hex: str) -> None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))
            cursor.insertText(text, fmt)

        _insert(f"[{ts}] ", _LOG_COLORS["ts"])
        _insert(f"[{step}] ", _LOG_COLORS["step"])
        _insert(f"{msg}\n", _LOG_COLORS.get(level.upper(), _LOG_COLORS["INFO"]))

        self._log_tail.setTextCursor(cursor)
        self._log_tail.ensureCursorVisible()

        # Mirror to output panel
        if _OutputLogPanel is not None and hasattr(self, "_output_panel"):
            try:
                self._output_panel.append_line(f"[{ts}] [{step}] {msg}", level=level)
            except Exception:
                pass

    # ── Public API ─────────────────────────────────────────────

    def set_voice_state(self, state: str) -> None:
        labels = {"idle": "VOICE: IDLE", "listening": "VOICE: LISTENING",
                  "processing": "VOICE: THINKING", "speaking": "VOICE: SPEAKING"}
        self._voice_label.setText(labels.get(state, "VOICE: IDLE"))
        reactor_map = {"idle": ArcReactorWidget.IDLE, "listening": ArcReactorWidget.LISTENING,
                       "processing": ArcReactorWidget.PROCESSING, "speaking": ArcReactorWidget.SPEAKING}
        self._arc_reactor.set_state(reactor_map.get(state, ArcReactorWidget.IDLE))
        self._devnex_voice.set_state(state)

    def closeEvent(self, event) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            self._active_worker.quit()
            self._active_worker.wait(2000)
        if self._gca_invoker is not None:
            try:
                self._gca_invoker.disconnect()
            except Exception:
                pass
        try:
            from core.file_logger import close_file_logging
            close_file_logging()
        except Exception:
            pass
        super().closeEvent(event)
