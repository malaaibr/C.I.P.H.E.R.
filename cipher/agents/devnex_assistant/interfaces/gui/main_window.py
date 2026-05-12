"""MainWindow — DevNex Assistant primary QMainWindow."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QPlainTextEdit, QSplitter,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor

from interfaces.gui.constants import (
    APP_NAME, APP_VERSION,
    WIN_WIDTH, WIN_HEIGHT, WIN_MIN_WIDTH, WIN_MIN_HEIGHT,
    NAV_WORKFLOW, NAV_TRACE, NAV_REVIEW, NAV_OUTPUT, NAV_CONFIG,
    ALL_NODE_IDS,
)
from interfaces.gui.styles import palette
from interfaces.gui.step_indicator import StepIndicator, StepState
from interfaces.gui.settings_manager import SettingsManager
from interfaces.gui.settings_dialog import SettingsDialog
from interfaces.gui.sidebar import Sidebar
from interfaces.gui.panels.workflow_panel import WorkflowPanel, ReviewDialog
from interfaces.gui.panels.trace_panel import TracePanel
from interfaces.gui.panels.review_panel import ReviewPanel
from interfaces.gui.panels.output_log import OutputLogPanel
from interfaces.gui.panels.config_panel import ConfigPanel

log = logging.getLogger(__name__)

_DEFAULT_ARTIFACTS_DIR = Path("generated_artifacts")

# ── Log color map — exact Int_Agent _LOG_COLORS dict ─────────────────────────
_LOG_COLORS = {
    "INFO":    palette.LOG_INFO,
    "ERROR":   palette.LOG_ERROR,
    "ISSUE":   palette.LOG_ISSUE,
    "WARN":    palette.LOG_ISSUE,
    "SUCCESS": palette.LOG_SUCCESS,
    "ts":      palette.LOG_TS,
    "step":    palette.LOG_STEP,
}

_STEP_NODE_MAP: dict[str, int] = {
    "S1": 0, "S2": 1, "S3": 2, "S4": 3, "S5": 4,
    "S6": 5, "S7": 6, "S8": 7, "S9": 8,
}


def _infer_level(msg: str) -> str:
    """Infer log level from message content — mirrors Int_Agent _infer_level()."""
    msg_upper = msg.upper()
    if any(k in msg_upper for k in ("ERROR", "FAIL", "EXCEPTION", "TRACEBACK")):
        return "ERROR"
    if any(k in msg_upper for k in ("WARN", "WARNING")):
        return "WARN"
    if any(k in msg_upper for k in ("SUCCESS", "COMPLETE", "DONE", "✓")):
        return "SUCCESS"
    if "ISSUE" in msg_upper:
        return "ISSUE"
    return "INFO"


class MainWindow(QMainWindow):
    """
    @brief Primary application window for DevNex Assistant.
    Implements the HTML prototype layout:
      Sidebar | StepIndicator | TabStack (Workflow / Trace / Output / Config) | Log Tail
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings   = SettingsManager()
        self._workers: list = []          # keep references to prevent GC
        self._active_worker = None
        self._orchestrator  = None        # created lazily when first run starts
        self._gca_invoker   = None        # shared across V-cycle and Review pipelines

        from PyQt6.QtGui import QIcon
        from interfaces.gui.icon import make_hex_pixmap
        self.setWindowIcon(QIcon(make_hex_pixmap(32)))
        self.setWindowTitle(f"{APP_NAME}  {APP_VERSION}")
        self.resize(WIN_WIDTH, WIN_HEIGHT)
        self.setMinimumSize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self.setStyleSheet(f"background-color: {palette.BG_APP}; color: {palette.TEXT1};")

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self._step_indicator = StepIndicator()   # kept for signal wiring; not displayed

        # Panel stack
        self._stack = QStackedWidget()
        self._workflow_panel = WorkflowPanel()
        self._trace_panel    = TracePanel(
            artifacts_dir=_DEFAULT_ARTIFACTS_DIR,
            on_open_source=self._open_in_external_editor,
        )
        self._review_panel   = ReviewPanel()
        self._output_panel   = OutputLogPanel()
        self._config_panel   = ConfigPanel()

        self._stack.addWidget(self._workflow_panel)   # 0 → Workflow
        self._stack.addWidget(self._trace_panel)      # 1 → Trace
        self._stack.addWidget(self._review_panel)     # 2 → Review
        self._stack.addWidget(self._output_panel)     # 3 → Output
        self._stack.addWidget(self._config_panel)     # 4 → Config

        # Sidebar + panel stack side-by-side
        self._sidebar = Sidebar(on_nav=self._on_nav)
        content = QWidget()
        cl = QHBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self._sidebar)
        cl.addWidget(self._stack, stretch=1)
        root.addWidget(content, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {palette.BORDER};")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        self._log_tail = QPlainTextEdit()
        self._log_tail.setReadOnly(True)
        self._log_tail.setMaximumBlockCount(500)
        self._log_tail.setFixedHeight(150)
        self._log_tail.setStyleSheet(
            f"background-color: {palette.BG_INPUT}; color: {palette.TEXT2}; "
            f"font-family: 'Cascadia Code', 'JetBrains Mono', monospace; "
            f"font-size: 9pt; border: none;"
        )
        root.addWidget(self._log_tail)

        # Wire signals
        self._workflow_panel.node_run_requested.connect(self._on_node_run_requested)
        self._workflow_panel.run_all_requested.connect(self._on_run_all_requested)
        self._workflow_panel.reset_requested.connect(self._on_reset_requested)
        self._config_panel.config_saved.connect(self._on_config_saved)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(
            f"background-color: {palette.BG_SIDEBAR}; "
            f"border-bottom: 1px solid {palette.BORDER};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 12, 0)
        hl.setSpacing(8)

        from PyQt6.QtGui import QIcon
        from interfaces.gui.icon import make_hex_pixmap
        icon_lbl = QLabel("⬡")
        icon_lbl.setStyleSheet(f"color: {palette.ACCENT}; font-size: 20px;")
        hl.addWidget(icon_lbl)

        title_lbl = QLabel(APP_NAME)
        title_lbl.setStyleSheet(f"color: {palette.TEXT1}; font-size: 13px; font-weight: bold;")
        hl.addWidget(title_lbl)

        ver_badge = QLabel(APP_VERSION)
        ver_badge.setStyleSheet(
            f"background-color: {palette.BG_CARD}; color: {palette.TEXT3}; "
            f"font-size: 9px; padding: 2px 6px; border-radius: 3px; "
            f"border: 1px solid {palette.BORDER};"
        )
        hl.addWidget(ver_badge)

        # Active panel breadcrumb
        self._panel_lbl = QLabel(NAV_WORKFLOW)
        self._panel_lbl.setStyleSheet(
            f"color: {palette.TEXT3}; font-size: 10px; font-family: monospace; "
            f"padding: 2px 8px;"
        )
        hl.addWidget(self._panel_lbl)

        self._status_badge = QLabel("● Idle")
        self._status_badge.setStyleSheet(
            f"background-color: rgba(60,232,200,0.08); color: {palette.ACCENT}; "
            f"font-size: 9px; padding: 2px 8px; border-radius: 3px;"
        )
        hl.addWidget(self._status_badge)
        hl.addStretch()

        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setFixedHeight(28)
        settings_btn.setStyleSheet(
            f"QPushButton {{ background-color: {palette.BG_CARD}; color: {palette.TEXT2}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 5px; "
            f"font-size: 10px; padding: 0 12px; }}"
            f"QPushButton:hover {{ color: {palette.TEXT1}; border-color: {palette.BORDER_BRIGHT}; }}"
        )
        settings_btn.clicked.connect(self._open_settings)
        hl.addWidget(settings_btn)
        return header

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_nav(self, label: str) -> None:
        idx_map = {
            NAV_WORKFLOW: 0,
            NAV_TRACE:    1,
            NAV_REVIEW:   2,
            NAV_OUTPUT:   3,
            NAV_CONFIG:   4,
        }
        self._stack.setCurrentIndex(idx_map.get(label, 0))
        self._panel_lbl.setText(f"› {label}")
        self._sidebar.set_active(label)

    # ── Worker / run logic ────────────────────────────────────────────────────

    def _get_gca_invoker(self):
        if self._gca_invoker is None:
            from gca.vscode_invoker import DevNexGCAInvoker
            config = self._config_panel.get_config()
            repo_path = Path(config.get("workspace_path", "."))
            self._gca_invoker = DevNexGCAInvoker(repo_path=repo_path)
        return self._gca_invoker

    def _get_orchestrator(self):
        if self._orchestrator is None:
            from core.run_context import DevNexRunContext
            from core.orchestrator import DevNexOrchestrator
            config = self._config_panel.get_config()
            ctx = DevNexRunContext(
                swc_name=config.get("SWC_name", "SWC"),
                workspace_path=config.get("workspace_path", "."),
            )
            self._orchestrator = DevNexOrchestrator(run_context=ctx)
            # Inject shared GCA invoker so both pipelines reuse one VS Code connection
            self._orchestrator._gca_invoker = self._get_gca_invoker()
        return self._orchestrator

    def _on_node_run_requested(self, node_id: str) -> None:
        from interfaces.gui.workers.node_worker import NodeWorker
        orchestrator = self._get_orchestrator()
        worker = NodeWorker(orchestrator, node_id)
        self._wire_worker(worker)
        self._active_worker = worker
        self._workers.append(worker)
        self._workflow_panel.set_running(True)
        self._set_status("Running", palette.WARNING)
        self.append_log(f"Starting node {node_id}…", step=node_id)
        worker.start()

    def _on_run_all_requested(self) -> None:
        from interfaces.gui.workers.full_run_worker import FullRunWorker
        orchestrator = self._get_orchestrator()
        worker = FullRunWorker(orchestrator)
        self._wire_worker(worker)
        self._active_worker = worker
        self._workers.append(worker)
        self._workflow_panel.set_running(True)
        self._set_status("Running", palette.WARNING)
        self.append_log("Starting full V-cycle run (S1N1 → S9N1)…", step="System")
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
            worker.progress.connect(lambda pct, msg: self.append_log(f"[{pct}%] {msg}", level="INFO"))

    def _on_node_started(self, node_id: str) -> None:
        self._workflow_panel.set_node_status(node_id, "running")
        stage_key = node_id[:2]
        step_idx = _STEP_NODE_MAP.get(stage_key, 0)
        self._step_indicator.update_step(step_idx, StepState.ACTIVE)
        self.append_log(f"Node {node_id} started.", step=node_id, level="INFO")

    def _on_node_complete(self, result) -> None:
        status = getattr(result, "status", "done")
        node_id = getattr(result, "node_id", "?")
        self._workflow_panel.set_node_status(node_id, status)
        artifacts = getattr(result, "artifacts", [])
        self._workflow_panel.show_node_detail(node_id, status, artifacts)

        stage_key = node_id[:2]
        step_idx = _STEP_NODE_MAP.get(stage_key, 0)
        if status in ("complete", "done"):
            self._step_indicator.update_step(step_idx, StepState.COMPLETE)
        else:
            self._step_indicator.update_step(step_idx, StepState.ERROR)

        level = "SUCCESS" if status in ("complete", "done") else "ERROR"
        self.append_log(f"Node {node_id} → {status}.", step=node_id, level=level)

        # Refresh trace graph after any stage completion
        self._trace_panel.update_from_state({"node_id": node_id, "status": status})

    def _on_review_needed(self, node_id: str, message: str) -> None:
        dlg = ReviewDialog(node_id, message, parent=self)
        approved = dlg.exec() == dlg.DialogCode.Accepted
        if self._active_worker is not None:
            self._active_worker.resume(approved)
        if not approved:
            self.append_log(f"Human review gate aborted at {node_id}.", level="WARN")

    def _on_worker_error(self, msg: str) -> None:
        self.append_log(msg, level="ERROR")
        self._workflow_panel.set_running(False)
        self._set_status("Error", palette.ERROR)
        self._active_worker = None

    def _on_run_finished(self, _result) -> None:
        self._workflow_panel.set_running(False)
        self._set_status("Idle", palette.ACCENT)
        self.append_log("Run complete.", level="SUCCESS")
        self._active_worker = None

    def _on_reset_requested(self) -> None:
        self._orchestrator = None
        self._step_indicator.reset_all()
        for nid in ALL_NODE_IDS:
            self._workflow_panel.set_node_status(nid, "idle")
        from persistence.state_store import StateStore
        StateStore().reset()
        self.append_log("Workflow state reset.", level="INFO")
        self._set_status("Idle", palette.ACCENT)

    def _on_config_saved(self, config: dict) -> None:
        self._orchestrator = None
        swc = config.get("SWC_name", "")
        self.append_log(f"Config saved. SWC = '{swc}'.", level="SUCCESS")

    # ── Log tail (exact Int_Agent append_log pattern) ─────────────────────────

    def append_log(self, msg: str, step: str = "System", level: str | None = None) -> None:
        """
        @brief Append a colored log line to the log tail.
        Mirrors Int_Agent MainWindow.append_log() exactly:
          [HH:MM:SS]  [STEP]  message
        """
        if level is None:
            level = _infer_level(msg)

        ts   = datetime.datetime.now().strftime("%H:%M:%S")
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

        # Mirror to OutputLogPanel
        self._output_panel.append_line(f"[{ts}] [{step}] {msg}", level=level)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str) -> None:
        self._status_badge.setText(f"● {text}")
        self._status_badge.setStyleSheet(
            f"background-color: rgba(60,232,200,0.08); color: {color}; "
            f"font-size: 9px; padding: 2px 8px; border-radius: 3px;"
        )

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, parent=self)
        dlg.exec()

    def _open_in_external_editor(self, path: str, line_no: int) -> None:
        """Open *path*:*line_no* in VS Code, falling back to the OS default."""
        import os
        import subprocess
        import sys
        try:
            target = f"{path}:{line_no}" if line_no else path
            subprocess.Popen(["code", "-g", target])
            return
        except Exception:
            pass
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            log.warning("Could not open %s: %s", path, exc)

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._active_worker is not None and self._active_worker.isRunning():
            self._active_worker.quit()
            self._active_worker.wait(2000)
        if self._gca_invoker is not None:
            self._gca_invoker.disconnect()
        self._settings.save()
        super().closeEvent(event)
