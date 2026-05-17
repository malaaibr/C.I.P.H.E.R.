"""CipherDashboardPanel — 3-column CIPHER HUD (PyQt6 port of reference)."""

from __future__ import annotations

import random
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QProgressBar, QPushButton,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

_BG = "#010a15"
_PANEL = "#041624"
_ACCENT = "#00c8ff"
_CYAN = "#00ffe5"
_GREEN = "#00ff9d"
_WARN = "#ffb700"
_BAD = "#ff3a3a"
_MUTED = "#2d5f7a"
_TEXT = "#b8e8ff"
_TEAL = "#7fd3ff"


def _pill(text: str, color: str, border: str) -> QLabel:
    pill = QLabel(text)
    pill.setStyleSheet(
        f"color:{color};border:1px solid {border};padding:3px 8px;border-radius:2px;"
        "letter-spacing:1px;font-size:8pt;"
    )
    return pill


class HudPanel(QFrame):
    """Bordered panel with a title header."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"HudPanel{{background:{_PANEL};border:1px solid rgba(0,200,255,0.18);border-radius:4px;}}"
        )
        self.setObjectName("HudPanel")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        label = QLabel(title.upper())
        label.setStyleSheet(f"color:{_MUTED};letter-spacing:2px;font-size:8pt;")
        layout.addWidget(label)
        self._body = QVBoxLayout()
        self._body.setSpacing(4)
        layout.addLayout(self._body)
        self.setLayout(layout)

    def body(self) -> QVBoxLayout:
        return self._body


class MetricCard(QFrame):
    """Small card with a large value and label."""

    def __init__(self, label: str, value: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:rgba(15,0,25,0.8);border:1px solid rgba(0,200,255,0.14);border-radius:3px;}"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        self._val = QLabel(value)
        self._val.setStyleSheet(f"color:{color};font-size:14pt;font-weight:bold;")
        self._val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{_MUTED};font-size:8pt;letter-spacing:1px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._val)
        layout.addWidget(lbl)
        self.setLayout(layout)

    def set_value(self, text: str) -> None:
        self._val.setText(text)


class StageCard(QFrame):
    """V-Cycle stage card with status badge."""

    def __init__(self, num: str, title: str, desc: str, status: str, parent=None) -> None:
        super().__init__(parent)
        color, bg, badge = self._style_for(status)
        self.setStyleSheet(
            f"QFrame{{border:1px solid {color};border-radius:4px;background:{bg};}}"
        )
        row = QHBoxLayout()
        row.setContentsMargins(6, 4, 6, 4)
        num_lbl = QLabel(num)
        num_lbl.setStyleSheet(f"color:{color};font-weight:bold;font-size:10pt;")
        body = QVBoxLayout()
        head = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{color};font-size:9pt;")
        badge_lbl = QLabel(badge)
        badge_lbl.setStyleSheet(f"color:{color};border:1px solid {color};padding:2px 6px;font-size:7pt;")
        head.addWidget(title_lbl)
        head.addStretch(1)
        head.addWidget(badge_lbl)
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color:{_MUTED};font-size:8pt;")
        body.addLayout(head)
        body.addWidget(desc_lbl)
        row.addWidget(num_lbl)
        row.addLayout(body, stretch=1)
        self.setLayout(row)

    @staticmethod
    def _style_for(status: str) -> tuple[str, str, str]:
        if status == "done":
            return _GREEN, "rgba(0,255,157,0.05)", "DONE"
        if status == "active":
            return _ACCENT, "rgba(0,200,255,0.08)", "ACTIVE"
        if status == "hitl":
            return _WARN, "rgba(255,183,0,0.08)", "HITL"
        return _MUTED, "rgba(20,0,30,0.4)", "PEND"


class CipherDashboardPanel(QWidget):
    """3-column CIPHER HUD — the main landing view."""

    devnex_requested = None  # signal set by main_window

    def __init__(self, on_devnex=None, parent=None) -> None:
        super().__init__(parent)
        self._on_devnex = on_devnex
        self.setStyleSheet(f"QWidget{{background:{_BG};color:{_TEXT};}}")

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        main = QHBoxLayout()
        main.setSpacing(8)
        main.setContentsMargins(8, 8, 8, 8)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self._build_workflow_view())
        self._center_stack.addWidget(self._build_trace_view())
        self._center_stack.addWidget(self._build_components_view())
        self._center_stack.addWidget(self._build_artifacts_view())
        self._center_stack.addWidget(self._build_voice_view())
        self._center_stack.addWidget(self._build_config_view())
        self._center_stack.addWidget(self._build_output_view())
        self._center_stack.addWidget(self._build_compliance_view())
        self._center_stack.addWidget(self._build_code_view())
        self._center_stack.addWidget(self._build_activity_view())

        main.addLayout(self._build_left_col(), 1)
        main.addWidget(self._center_stack, 3)
        main.addLayout(self._build_right_col(), 1)
        root.addLayout(main, stretch=1)
        self.setLayout(root)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        self._latency_timer = QTimer(self)
        self._latency_timer.timeout.connect(self._update_latency)
        self._latency_timer.start(2500)

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet(
            "QFrame{background:rgba(1,8,22,0.95);border-bottom:1px solid rgba(0,200,255,0.2);}"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 6, 12, 6)
        title = QLabel("C.I.P.H.E.R")
        title.setStyleSheet(f"color:{_ACCENT};font-size:16pt;font-weight:bold;letter-spacing:5px;")
        sub = QLabel("V-CYCLE INTELLIGENCE PLATFORM  ·  MVP 1.0  ·  LLM GATEWAY")
        sub.setStyleSheet(f"color:{_MUTED};font-size:8pt;")
        left = QVBoxLayout()
        left.setSpacing(1)
        left.addWidget(title)
        left.addWidget(sub)
        left_box = QWidget()
        left_box.setLayout(left)
        row.addWidget(left_box)
        row.addStretch(1)
        row.addWidget(_pill("LLM ONLINE", _GREEN, _GREEN))
        row.addWidget(_pill("VOICE READY", _CYAN, _CYAN))
        row.addWidget(_pill("A2A :8100", _MUTED, "rgba(0,200,255,0.2)"))
        self._clock = QLabel("00:00:00")
        self._clock.setStyleSheet(f"color:{_MUTED};font-size:11pt;")
        row.addWidget(self._clock)
        return bar

    def _build_left_col(self) -> QVBoxLayout:
        nav = QVBoxLayout()
        nav.setSpacing(8)
        panel = HudPanel("Navigation")
        self._nav_list = QListWidget()
        for item in [
            "V-Cycle Workflow",
            "Traceability Matrix",
            "Component Store",
            "Artifacts",
            "Voice Interface",
            "Config / SWC",
            "Output Log",
            "Compliance",
            "Code Diff",
            "Activity",
        ]:
            self._nav_list.addItem(QListWidgetItem(item))
        self._nav_list.setCurrentRow(0)
        self._nav_list.currentRowChanged.connect(self._center_stack.setCurrentIndex)
        panel.body().addWidget(self._nav_list)
        nav.addWidget(panel)

        # DevNex button
        devnex_btn = QPushButton("OPEN  DevNex  WORKSPACE  >>")
        devnex_btn.setFixedHeight(38)
        devnex_btn.setStyleSheet(
            f"QPushButton{{background:{_ACCENT};color:#010a15;border:none;border-radius:3px;"
            f"font-weight:bold;letter-spacing:2px;font-size:9pt;}}"
            f"QPushButton:hover{{background:{_GREEN};}}"
        )
        devnex_btn.clicked.connect(self._open_devnex)
        nav.addWidget(devnex_btn)

        swc_panel = HudPanel("SWC Context")
        for label, value, color in [
            ("SWC Name", "—", _ACCENT),
            ("Workflow State", "IDLE", _MUTED),
            ("LLM Backend", "Ollama", _GREEN),
            ("A2A Server", ":8100", _CYAN),
            ("Gateway", ":8200", _CYAN),
        ]:
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(label))
            val = QLabel(value)
            val.setStyleSheet(f"color:{color};")
            rl.addStretch(1)
            rl.addWidget(val)
            swc_panel.body().addWidget(row_w)
        nav.addWidget(swc_panel)
        return nav

    def _open_devnex(self) -> None:
        if self._on_devnex:
            self._on_devnex()

    def _build_workflow_view(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setSpacing(8)

        metrics = QGridLayout()
        self._metric_latency = MetricCard("latency", "— ms", _GREEN)
        metrics.addWidget(MetricCard("stages done", "0/9", _GREEN), 0, 0)
        metrics.addWidget(MetricCard("LLD reqs", "0", _CYAN), 0, 1)
        metrics.addWidget(MetricCard("funcs linked", "0", _GREEN), 0, 2)
        metrics.addWidget(MetricCard("HITL gates", "0", _WARN), 1, 0)
        metrics.addWidget(MetricCard("HLD→LLD trace", "—", _GREEN), 1, 1)
        metrics.addWidget(self._metric_latency, 1, 2)
        layout.addLayout(metrics)

        stages = HudPanel("V-Cycle Pipeline")
        for num, title, desc, status in [
            ("1", "S1N1 LLD Gen", "Generate TEMP LLD", "pending"),
            ("2", "S1N23 Categorize", "Categorize LLD", "pending"),
            ("3", "S1N4 Unique IDs", "Assign IDs", "pending"),
            ("4", "S2 Code Link", "Embed IDs into code", "pending"),
            ("5", "S3-S5 Trace", "Generate trace reports", "pending"),
            ("6", "S6 Test Gen", "Generate .tst", "pending"),
            ("7", "S7 UTD", "Parse VectorCAST", "pending"),
            ("8", "S8 UTD Link", "Link to LLD", "pending"),
            ("9", "S9 Full Trace", "Audit-ready matrix", "pending"),
        ]:
            stages.body().addWidget(StageCard(num, title, desc, status))
        layout.addWidget(stages)
        return wrap

    def _build_trace_view(self) -> QWidget:
        panel = HudPanel("Traceability Matrix")
        chain = QLabel("HLD → LLD → Code → TST → UTD → Full Trace")
        chain.setStyleSheet(f"color:{_TEAL};")
        panel.body().addWidget(chain)
        panel.body().addWidget(QLabel("No trace data loaded. Run V-Cycle to populate."))
        return panel

    def _build_components_view(self) -> QWidget:
        panel = HudPanel("Component Store")
        search = QLineEdit()
        search.setPlaceholderText("Search components...")
        panel.body().addWidget(search)
        panel.body().addWidget(QLabel("Component index will appear after first run."))
        return panel

    def _build_artifacts_view(self) -> QWidget:
        panel = HudPanel("Artifacts (MinIO)")
        panel.body().addWidget(QLabel("Artifacts stored in MinIO buckets:"))
        panel.body().addWidget(QLabel("  cipher-artifacts/"))
        panel.body().addWidget(QLabel("  cipher-checkpoints/"))
        return panel

    def _build_voice_view(self) -> QWidget:
        panel = HudPanel("Voice Interface")
        panel.body().addWidget(QLabel("Voice control ready."))
        panel.body().addWidget(QLabel('Say "Hey C.I.P.H.E.R" to activate.'))
        return panel

    def _build_config_view(self) -> QWidget:
        panel = HudPanel("Config / SWC")
        for label in ["SWC_NAME", "SWC_C", "SWC_H", "HLD", "TEMP_LLD", "FUNC_REQ"]:
            panel.body().addWidget(QLabel(f"  {label}: —"))
        return panel

    def _build_output_view(self) -> QWidget:
        panel = HudPanel("Output Log")
        self._output_log = QTextEdit()
        self._output_log.setReadOnly(True)
        self._output_log.setStyleSheet("background:#020d1a;border:none;color:#b8e8ff;font-size:9pt;")
        self._output_log.append("C.I.P.H.E.R ready. Awaiting commands...")
        panel.body().addWidget(self._output_log)
        return panel

    def _build_compliance_view(self) -> QWidget:
        panel = HudPanel("Compliance Dashboard")
        for label, value, color in [
            ("HLD→LLD", 0, _MUTED),
            ("LLD→Code", 0, _MUTED),
            ("Code→Test", 0, _MUTED),
            ("UTD", 0, _MUTED),
        ]:
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(label))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(value)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            rl.addWidget(bar, stretch=1)
            panel.body().addWidget(row_w)
        return panel

    def _build_code_view(self) -> QWidget:
        panel = HudPanel("Code Diff")
        diff = QTextEdit()
        diff.setReadOnly(True)
        diff.setStyleSheet("background:#020d1a;border:none;font-size:9pt;")
        diff.setHtml("<span style='color:#2d5f7a'>No diff available yet.</span>")
        panel.body().addWidget(diff)
        return panel

    def _build_activity_view(self) -> QWidget:
        panel = HudPanel("Activity Timeline")
        log = QTextEdit()
        log.setReadOnly(True)
        log.setStyleSheet("background:#020d1a;border:none;font-size:9pt;")
        log.append("Session started.")
        panel.body().addWidget(log)
        return panel

    def _build_right_col(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)

        status = HudPanel("System Status")
        for name, value, color in [
            ("LLM Gateway", ":8200", _GREEN),
            ("A2A Server", ":8100", _GREEN),
            ("Ollama", "qwen2.5-coder:1.5b", _GREEN),
            ("Redis", ":6379", _GREEN),
            ("Memgraph", ":7687", _GREEN),
            ("Qdrant", ":6333", _GREEN),
            ("MinIO", ":9000", _GREEN),
            ("NATS", ":4222", _GREEN),
            ("OPA", ":8181", _GREEN),
            ("Voice", "READY", _CYAN),
        ]:
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(name))
            val = QLabel(value)
            val.setStyleSheet(f"color:{color};")
            rl.addStretch(1)
            rl.addWidget(val)
            status.body().addWidget(row_w)
        col.addWidget(status)

        session = HudPanel("Session")
        for name, value, color in [
            ("LLM Calls", "0", _ACCENT),
            ("Avg Latency", "—", _GREEN),
            ("Artifacts", "0", _GREEN),
            ("HITL Gates", "0", _WARN),
        ]:
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(name))
            val = QLabel(value)
            val.setStyleSheet(f"color:{color};")
            rl.addStretch(1)
            rl.addWidget(val)
            session.body().addWidget(row_w)
        col.addWidget(session)

        actions = HudPanel("Quick Actions")
        for text in [
            "Run S1N1 — LLD Gen",
            "Run Full V-Cycle",
            "Open DevNex Workspace",
            "Check Infrastructure",
        ]:
            btn = QPushButton(text)
            actions.body().addWidget(btn)
        col.addWidget(actions)
        col.addStretch()
        return col

    def _update_clock(self) -> None:
        self._clock.setText(datetime.now().strftime("%H:%M:%S"))

    def _update_latency(self) -> None:
        value = random.randint(28, 46)
        self._metric_latency.set_value(f"{value} ms")

    def set_listening(self, listening: bool) -> None:
        pass

    def append_output(self, text: str) -> None:
        if hasattr(self, "_output_log"):
            self._output_log.append(text)
