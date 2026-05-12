"""ReviewPanel — SWC Technical Review pipeline GUI.

Layout
------
ReviewPanel (QWidget)
├── _config_strip       — SWC name, reviewer, artifact path fields + RUN button
├── _node_canvas        — 9-node horizontal review pipeline visualization
├── _findings_splitter  — left: stage list | right: finding detail table
└── _status_bar         — verdict badge + progress bar + report path
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from review.review_models import (
    FindingSeverity,
    ReviewNodeStatus,
    ReviewReport,
    ReviewVerdict,
    StageResult,
)

log = logging.getLogger(__name__)

# ── Color tokens ──────────────────────────────────────────────────────────────

_BG_DEEP    = "#010a15"
_BG_CARD    = "#041624"
_BG_SIDEBAR = "#061c2e"
_BORDER     = "#1a2e40"
_TEXT1      = "#b8e8ff"
_TEXT2      = "#2d5f7a"
_ACCENT_OK  = "#00ff9d"   # passed
_ACCENT_ERR = "#ff3a8a"   # failed / critical
_ACCENT_WARN= "#ffb700"   # conditional / major
_ACCENT_INFO= "#00c8ff"   # running / info
_ACCENT_SKIP= "#4a5568"   # skipped

_SEV_COLOR = {
    FindingSeverity.CRITICAL: "#ff3a8a",
    FindingSeverity.MAJOR:    "#ffb700",
    FindingSeverity.MINOR:    "#00c8ff",
    FindingSeverity.INFO:     "#6b7280",
}

_STATUS_COLOR = {
    ReviewNodeStatus.PASSED:  _ACCENT_OK,
    ReviewNodeStatus.FAILED:  _ACCENT_ERR,
    ReviewNodeStatus.RUNNING: _ACCENT_INFO,
    ReviewNodeStatus.SKIPPED: _ACCENT_SKIP,
    ReviewNodeStatus.PENDING: _TEXT2,
}

_VERDICT_COLOR = {
    ReviewVerdict.APPROVED:    _ACCENT_OK,
    ReviewVerdict.CONDITIONAL: _ACCENT_WARN,
    ReviewVerdict.REJECTED:    _ACCENT_ERR,
    ReviewVerdict.INCOMPLETE:  _ACCENT_INFO,
}

_BTN_BASE = "border-radius: 4px; font-size: 8pt; font-family: monospace; padding: 2px 10px;"

# Review node metadata
_NODES = [
    ("R1N1", "Artifact\nCheck"),
    ("R2N1", "HLD\nReview"),
    ("R3N1", "LLD\nReview"),
    ("R4N1", "HLD→LLD\nTrace"),
    ("R5N1", "LLD→Code\nTrace"),
    ("R6N1", "KW\nGate"),
    ("R7N1", "UT Doc\nReview"),
    ("R8N1", "UT Report\nGate"),
    ("R9N1", "Verdict"),
]


# ── Node card (graphics object) ───────────────────────────────────────────────

class _ReviewNodeCard(QGraphicsObject):
    """80×70px review node card painted directly."""

    W = 90
    H = 72

    def __init__(self, node_id: str, label: str) -> None:
        super().__init__()
        self.node_id = node_id
        self._label  = label
        self._status = ReviewNodeStatus.PENDING
        self._critical = 0
        self._major    = 0
        self.setAcceptHoverEvents(True)
        self._hovered = False

    def set_status(self, status: ReviewNodeStatus, critical: int = 0, major: int = 0) -> None:
        self._status   = status
        self._critical = critical
        self._major    = major
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.W, self.H)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        accent = _STATUS_COLOR.get(self._status, _TEXT2)
        bg     = QColor(_BG_CARD)
        border = QColor(accent)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Card background
        painter.setBrush(QBrush(bg))
        pen = QPen(border, 1.5 if self._hovered else 1.0)
        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.W - 1, self.H - 1), 6, 6)

        # Node ID badge
        badge_rect = QRectF(4, 4, self.W - 8, 16)
        painter.setBrush(QBrush(QColor(accent).darker(200)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 3, 3)

        painter.setPen(QPen(QColor(accent)))
        font = QFont("monospace", 7, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self.node_id)

        # Label
        label_rect = QRectF(4, 22, self.W - 8, 28)
        painter.setPen(QPen(QColor(_TEXT1)))
        font2 = QFont("monospace", 7)
        painter.setFont(font2)
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            self._label,
        )

        # Finding pills
        pill_y = self.H - 16
        pill_x = 6
        if self._critical > 0:
            self._draw_pill(painter, pill_x, pill_y, str(self._critical), _ACCENT_ERR)
            pill_x += 28
        if self._major > 0:
            self._draw_pill(painter, pill_x, pill_y, str(self._major), _ACCENT_WARN)

    def _draw_pill(self, painter: QPainter, x: float, y: float, text: str, color: str) -> None:
        pill = QRectF(x, y, 22, 10)
        painter.setBrush(QBrush(QColor(color).darker(200)))
        painter.setPen(QPen(QColor(color), 0.8))
        painter.drawRoundedRect(pill, 4, 4)
        painter.setPen(QPen(QColor(color)))
        painter.setFont(QFont("monospace", 6, QFont.Weight.Bold))
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, text)

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def right_anchor(self) -> tuple[float, float]:
        pos = self.pos()
        return pos.x() + self.W, pos.y() + self.H / 2

    def left_anchor(self) -> tuple[float, float]:
        pos = self.pos()
        return pos.x(), pos.y() + self.H / 2


# ── Edge item ─────────────────────────────────────────────────────────────────

class _EdgeItem(QGraphicsPathItem):
    def __init__(self, x1: float, y1: float, x2: float, y2: float, color: str) -> None:
        super().__init__()
        path = QPainterPath()
        path.moveTo(x1, y1)
        cx = (x1 + x2) / 2
        path.cubicTo(cx, y1, cx, y2, x2, y2)
        self.setPath(path)
        pen = QPen(QColor(color), 1.2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setZValue(-1)


# ── Pipeline canvas ───────────────────────────────────────────────────────────

class _ReviewPipelineCanvas(QGraphicsView):
    """Horizontal 9-node pipeline visualization."""

    NODE_GAP = 110
    NODE_X0  = 16
    NODE_Y   = 20

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(_BG_DEEP)))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.setFixedHeight(_ReviewNodeCard.H + 56)

        self._cards: dict[str, _ReviewNodeCard] = {}
        self._build()

    def _build(self) -> None:
        self._scene.clear()
        self._cards.clear()

        for idx, (nid, label) in enumerate(_NODES):
            card = _ReviewNodeCard(nid, label)
            x = self.NODE_X0 + idx * self.NODE_GAP
            card.setPos(x, self.NODE_Y)
            self._scene.addItem(card)
            self._cards[nid] = card

            if idx > 0:
                prev_nid = _NODES[idx - 1][0]
                rx1, ry1 = self._cards[prev_nid].right_anchor()
                rx2, ry2 = card.left_anchor()
                edge = _EdgeItem(rx1, ry1, rx2, ry2, _TEXT2)
                self._scene.addItem(edge)

        total_w = self.NODE_X0 * 2 + len(_NODES) * self.NODE_GAP
        self._scene.setSceneRect(0, 0, total_w, _ReviewNodeCard.H + 40)

    def set_node_status(
        self,
        node_id: str,
        status:  ReviewNodeStatus,
        critical: int = 0,
        major: int = 0,
    ) -> None:
        card = self._cards.get(node_id)
        if card:
            card.set_status(status, critical, major)

    def reset_all(self) -> None:
        for card in self._cards.values():
            card.set_status(ReviewNodeStatus.PENDING)


# ── Artifact config strip ─────────────────────────────────────────────────────

class _ArtifactField(QWidget):
    """Label + QLineEdit + Browse button row for a single artifact slot."""

    def __init__(self, slot: str, label: str, parent=None) -> None:
        super().__init__(parent)
        self.slot = slot
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)

        lbl = QLabel(label)
        lbl.setFixedWidth(160)
        lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 8pt; font-family: monospace;")
        hl.addWidget(lbl)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("(optional — leave blank to auto-discover)")
        self._edit.setStyleSheet(
            f"QLineEdit {{ background: {_BG_CARD}; color: {_TEXT1}; "
            f"border: 1px solid {_BORDER}; border-radius: 3px; "
            f"padding: 2px 6px; font-size: 8pt; }}"
            f"QLineEdit:focus {{ border-color: rgba(0,200,255,0.4); }}"
        )
        hl.addWidget(self._edit, stretch=1)

        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(26)
        browse_btn.setFixedHeight(22)
        browse_btn.setStyleSheet(
            f"QPushButton {{ background: {_BG_CARD}; color: {_TEXT2}; "
            f"border: 1px solid {_BORDER}; border-radius: 3px; }}"
            f"QPushButton:hover {{ color: {_TEXT1}; border-color: {_ACCENT_INFO}; }}"
        )
        browse_btn.clicked.connect(self._browse)
        hl.addWidget(browse_btn)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Select {self.slot}", "", "All Files (*.*)")
        if path:
            self._edit.setText(path)

    def value(self) -> str:
        return self._edit.text().strip()

    def set_value(self, v: str) -> None:
        self._edit.setText(v)


# ── ReviewPanel ───────────────────────────────────────────────────────────────

class ReviewPanel(QWidget):
    """Full SWC Technical Review pipeline panel."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_worker = None
        self._report: ReviewReport | None = None
        self._current_stage: StageResult | None = None

        self._artifact_fields: dict[str, _ArtifactField] = {}
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_config_strip())
        root.addWidget(self._build_pipeline_canvas())
        root.addWidget(self._build_findings_area(), stretch=1)
        root.addWidget(self._build_status_bar())

    def _build_header(self) -> QWidget:
        strip = QWidget()
        strip.setFixedHeight(36)
        strip.setStyleSheet(
            f"background: {_BG_DEEP}; border-bottom: 1px solid {_BORDER};"
        )
        hl = QHBoxLayout(strip)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(10)

        title = QLabel("TECHNICAL REVIEW PIPELINE")
        title.setStyleSheet(
            f"color: {_TEXT2}; font-size: 8pt; font-family: monospace; letter-spacing: 3px;"
        )
        hl.addWidget(title)
        hl.addStretch()

        self._verdict_lbl = QLabel("")
        self._verdict_lbl.setStyleSheet(
            f"color: {_TEXT2}; font-size: 9pt; font-family: monospace; font-weight: bold;"
        )
        hl.addWidget(self._verdict_lbl)

        self._report_btn = QPushButton("⬇ Open Report")
        self._report_btn.setFixedHeight(24)
        self._report_btn.setVisible(False)
        self._report_btn.setStyleSheet(
            f"QPushButton {{ background: {_BG_CARD}; color: {_ACCENT_OK}; "
            f"border: 1px solid {_ACCENT_OK}; {_BTN_BASE} }}"
            f"QPushButton:hover {{ background: rgba(0,255,157,0.1); }}"
        )
        self._report_btn.clicked.connect(self._open_report)
        hl.addWidget(self._report_btn)

        return strip

    def _build_config_strip(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {_BG_SIDEBAR}; border-bottom: 1px solid {_BORDER}; }}"
        )
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(6)

        # SWC + reviewer row
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        for label_text, placeholder, attr in [
            ("SWC Name:", "e.g. Brake_Ctrl",  "_swc_edit"),
            ("Reviewer:", "Your name",         "_reviewer_edit"),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 8pt;")
            lbl.setFixedWidth(80)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedWidth(160)
            edit.setStyleSheet(
                f"QLineEdit {{ background: {_BG_CARD}; color: {_TEXT1}; "
                f"border: 1px solid {_BORDER}; border-radius: 3px; padding: 2px 6px; "
                f"font-size: 8pt; }}"
                f"QLineEdit:focus {{ border-color: rgba(0,200,255,0.4); }}"
            )
            setattr(self, attr, edit)
            top_row.addWidget(lbl)
            top_row.addWidget(edit)

        # artifacts_dir browse
        art_dir_lbl = QLabel("Artifacts Dir:")
        art_dir_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 8pt;")
        art_dir_lbl.setFixedWidth(90)
        self._artifacts_dir_edit = QLineEdit()
        self._artifacts_dir_edit.setPlaceholderText(
            "Directory with all artifacts (auto-discover)"
        )
        self._artifacts_dir_edit.setStyleSheet(
            f"QLineEdit {{ background: {_BG_CARD}; color: {_TEXT1}; "
            f"border: 1px solid {_BORDER}; border-radius: 3px; padding: 2px 6px; "
            f"font-size: 8pt; }}"
            f"QLineEdit:focus {{ border-color: rgba(0,200,255,0.4); }}"
        )
        dir_browse = QPushButton("…")
        dir_browse.setFixedSize(26, 22)
        dir_browse.setStyleSheet(
            f"QPushButton {{ background: {_BG_CARD}; color: {_TEXT2}; "
            f"border: 1px solid {_BORDER}; border-radius: 3px; }}"
            f"QPushButton:hover {{ color: {_TEXT1}; border-color: {_ACCENT_INFO}; }}"
        )
        dir_browse.clicked.connect(self._browse_artifacts_dir)
        top_row.addWidget(art_dir_lbl)
        top_row.addWidget(self._artifacts_dir_edit, stretch=1)
        top_row.addWidget(dir_browse)
        top_row.addStretch()

        self._run_btn = QPushButton("▶  Run Review")
        self._run_btn.setFixedSize(120, 26)
        self._run_btn.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT_INFO}; color: #0b0e13; "
            f"border: none; border-radius: 4px; font-size: 8pt; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #5af5ff; }}"
            f"QPushButton:disabled {{ background: {_ACCENT_SKIP}; color: {_TEXT2}; }}"
        )
        self._run_btn.clicked.connect(self._on_run_clicked)
        top_row.addWidget(self._run_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setFixedSize(80, 26)
        self._stop_btn.setVisible(False)
        self._stop_btn.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT_ERR}; color: #0b0e13; "
            f"border: none; border-radius: 4px; font-size: 8pt; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #ff6eaa; }}"
        )
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        top_row.addWidget(self._stop_btn)

        vl.addLayout(top_row)

        # Individual artifact fields (collapsible-style — shown below dir)
        fields_row = QHBoxLayout()
        fields_row.setSpacing(8)

        from review.artifact_loader import ARTIFACT_SLOTS
        col = 0
        col_widget = [QVBoxLayout(), QVBoxLayout(), QVBoxLayout()]
        for slot, label in ARTIFACT_SLOTS.items():
            field = _ArtifactField(slot, label)
            self._artifact_fields[slot] = field
            col_widget[col % 3].addWidget(field)
            col += 1

        for cw in col_widget:
            w = QWidget()
            w.setLayout(cw)
            fields_row.addWidget(w, stretch=1)
        vl.addLayout(fields_row)

        return frame

    def _build_pipeline_canvas(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet(f"background: {_BG_DEEP};")
        vl = QVBoxLayout(wrapper)
        vl.setContentsMargins(8, 8, 8, 0)
        vl.setSpacing(4)

        section_lbl = QLabel("PIPELINE NODES")
        section_lbl.setStyleSheet(
            f"color: {_TEXT2}; font-size: 7pt; font-family: monospace; letter-spacing: 2px;"
        )
        vl.addWidget(section_lbl)

        self._canvas = _ReviewPipelineCanvas()
        vl.addWidget(self._canvas)

        return wrapper

    def _build_findings_area(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter {{ background: {_BG_DEEP}; }}"
            f"QSplitter::handle {{ background: {_BORDER}; width: 1px; }}"
        )

        # Left: stage list
        self._stage_list = QListWidget()
        self._stage_list.setStyleSheet(
            f"QListWidget {{ background: {_BG_SIDEBAR}; border: none; "
            f"color: {_TEXT1}; font-family: monospace; font-size: 9pt; "
            f"border-right: 1px solid {_BORDER}; }}"
            f"QListWidget::item {{ padding: 6px 10px; }}"
            f"QListWidget::item:hover {{ background: {_BG_CARD}; }}"
            f"QListWidget::item:selected {{ background: #0d2a3d; "
            f"border-left: 2px solid {_ACCENT_INFO}; }}"
        )
        self._stage_list.setFixedWidth(220)
        self._stage_list.itemClicked.connect(self._on_stage_selected)
        splitter.addWidget(self._stage_list)

        # Right: findings table
        right = QWidget()
        right.setStyleSheet(f"background: {_BG_DEEP};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        self._stage_title_lbl = QLabel("Select a stage to view findings")
        self._stage_title_lbl.setStyleSheet(
            f"color: {_TEXT2}; font-size: 9pt; font-family: monospace; "
            f"padding: 8px 12px; border-bottom: 1px solid {_BORDER}; "
            f"background: {_BG_SIDEBAR};"
        )
        rv.addWidget(self._stage_title_lbl)

        self._findings_table = QTableWidget(0, 5)
        self._findings_table.setHorizontalHeaderLabels(
            ["Severity", "Category", "Description", "Artifact Ref", "Standard"]
        )
        self._findings_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._findings_table.horizontalHeader().setDefaultSectionSize(110)
        self._findings_table.verticalHeader().setVisible(False)
        self._findings_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._findings_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._findings_table.setStyleSheet(
            f"QTableWidget {{ background: {_BG_DEEP}; color: {_TEXT1}; "
            f"border: none; gridline-color: {_BORDER}; font-size: 8pt; }}"
            f"QTableWidget::item {{ padding: 4px 8px; }}"
            f"QTableWidget::item:selected {{ background: #0d2a3d; }}"
            f"QHeaderView::section {{ background: {_BG_SIDEBAR}; color: {_TEXT2}; "
            f"border: 1px solid {_BORDER}; padding: 4px; font-size: 8pt; }}"
        )
        rv.addWidget(self._findings_table, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        return splitter

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(32)
        bar.setStyleSheet(
            f"background: {_BG_SIDEBAR}; border-top: 1px solid {_BORDER};"
        )
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(12, 4, 12, 4)
        hl.setSpacing(12)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ background: {_BG_CARD}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {_ACCENT_INFO}; border-radius: 4px; }}"
        )
        hl.addWidget(self._progress_bar, stretch=1)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(
            f"color: {_TEXT2}; font-size: 8pt; font-family: monospace;"
        )
        hl.addWidget(self._status_lbl)

        return bar

    # ── Event handlers ────────────────────────────────────────────────────────

    def _browse_artifacts_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Artifacts Directory")
        if directory:
            self._artifacts_dir_edit.setText(directory)

    def _on_run_clicked(self) -> None:
        from review.review_orchestrator import ReviewConfig
        from interfaces.gui.workers.review_worker import ReviewWorker

        swc_name = self._swc_edit.text().strip()
        reviewer = self._reviewer_edit.text().strip()
        if not swc_name:
            self._status_lbl.setText("⚠ SWC name is required.")
            return
        if not reviewer:
            self._status_lbl.setText("⚠ Reviewer name is required.")
            return

        artifact_paths: dict[str, str] = {}
        for slot, field in self._artifact_fields.items():
            v = field.value()
            if v:
                artifact_paths[slot] = v

        config = ReviewConfig(
            swc_name        = swc_name,
            reviewer        = reviewer,
            artifact_paths  = artifact_paths,
            artifacts_dir   = self._artifacts_dir_edit.text().strip(),
        )

        # Lazy-create a GCA invoker (reuse parent window's if available)
        gca_invoker = self._get_gca_invoker()
        output_dir  = self._get_output_dir()

        self._report = None
        self._stage_list.clear()
        self._findings_table.setRowCount(0)
        self._canvas.reset_all()
        self._verdict_lbl.setText("")
        self._report_btn.setVisible(False)
        self._progress_bar.setValue(0)

        worker = ReviewWorker(config, gca_invoker, output_dir, parent=self)
        worker.log_line.connect(self._on_log)
        worker.node_started.connect(self._on_node_started)
        worker.node_complete.connect(self._on_node_complete)
        worker.progress.connect(self._on_progress)
        worker.review_finished.connect(self._on_review_finished)
        worker.error_occurred.connect(self._on_error)
        worker.finished.connect(self._on_worker_finished)

        self._active_worker = worker
        self._run_btn.setEnabled(False)
        self._stop_btn.setVisible(True)
        worker.start()

    def _on_stop_clicked(self) -> None:
        if self._active_worker and self._active_worker.isRunning():
            self._active_worker.terminate()
            self._status_lbl.setText("Review stopped by user.")
        self._run_btn.setEnabled(True)
        self._stop_btn.setVisible(False)

    def _on_log(self, message: str, level: str) -> None:
        self._status_lbl.setText(message[:120])

    def _on_node_started(self, node_id: str) -> None:
        self._canvas.set_node_status(node_id, ReviewNodeStatus.RUNNING)
        self._status_lbl.setText(f"Running {node_id}…")

    def _on_node_complete(self, result: StageResult) -> None:
        self._canvas.set_node_status(
            result.node_id,
            result.status,
            result.critical_count,
            result.major_count,
        )
        # Add to stage list
        icon_map = {
            ReviewNodeStatus.PASSED:  "✅",
            ReviewNodeStatus.FAILED:  "❌",
            ReviewNodeStatus.SKIPPED: "⏭",
            ReviewNodeStatus.RUNNING: "⏳",
            ReviewNodeStatus.PENDING: "○",
        }
        icon  = icon_map.get(result.status, "?")
        text  = f"{icon}  {result.node_id}  {result.label}"
        item  = QListWidgetItem(text)
        color = _STATUS_COLOR.get(result.status, _TEXT2)
        item.setForeground(QBrush(QColor(color)))
        item.setData(Qt.ItemDataRole.UserRole, result)
        self._stage_list.addItem(item)
        self._stage_list.scrollToBottom()

    def _on_progress(self, pct: int, node_id: str, label: str) -> None:
        self._progress_bar.setValue(pct)

    def _on_review_finished(self, report: ReviewReport) -> None:
        self._report = report
        verdict = report.verdict
        color   = _VERDICT_COLOR.get(verdict, _TEXT2)
        self._verdict_lbl.setText(f"VERDICT: {verdict.value}")
        self._verdict_lbl.setStyleSheet(
            f"color: {color}; font-size: 9pt; font-family: monospace; font-weight: bold;"
        )
        self._report_btn.setVisible(True)
        self._progress_bar.setValue(100)

    def _on_error(self, message: str) -> None:
        self._status_lbl.setText(f"ERROR: {message}")

    def _on_worker_finished(self) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setVisible(False)
        self._active_worker = None

    def _on_stage_selected(self, item: QListWidgetItem) -> None:
        result: StageResult = item.data(Qt.ItemDataRole.UserRole)
        if result is None:
            return
        self._current_stage = result
        self._stage_title_lbl.setText(
            f"{result.node_id} — {result.label}  "
            f"({len(result.findings)} finding(s))"
        )
        self._populate_findings_table(result)

    def _populate_findings_table(self, result: StageResult) -> None:
        self._findings_table.setRowCount(0)
        for f in result.findings:
            row = self._findings_table.rowCount()
            self._findings_table.insertRow(row)

            sev_item = QTableWidgetItem(f.severity.value)
            color    = _SEV_COLOR.get(f.severity, _TEXT2)
            sev_item.setForeground(QBrush(QColor(color)))
            sev_item.setFont(QFont("monospace", 8, QFont.Weight.Bold))
            self._findings_table.setItem(row, 0, sev_item)
            self._findings_table.setItem(row, 1, QTableWidgetItem(f.category))
            self._findings_table.setItem(row, 2, QTableWidgetItem(f.description))
            self._findings_table.setItem(row, 3, QTableWidgetItem(
                f.artifact_ref or f.item_ref
            ))
            self._findings_table.setItem(row, 4, QTableWidgetItem(f.standard_ref))

    # ── Report opening ────────────────────────────────────────────────────────

    def _open_report(self) -> None:
        if self._report is None:
            return
        output_dir = self._get_output_dir()
        safe_name  = self._report.swc_name.replace(" ", "_").replace("/", "_")
        md_path    = output_dir / f"{safe_name}_review_report.md"
        if md_path.exists():
            try:
                subprocess.Popen(["code", "-g", str(md_path)])
                return
            except Exception:
                pass
            try:
                if sys.platform == "win32":
                    os.startfile(str(md_path))
                else:
                    subprocess.Popen(["xdg-open", str(md_path)])
            except Exception as exc:
                log.warning("Could not open report: %s", exc)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_gca_invoker(self):
        """Walk up to MainWindow for the shared GCA invoker."""
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "_gca_invoker") and parent._gca_invoker is not None:
                return parent._gca_invoker
            if hasattr(parent, "_get_gca_invoker"):
                return parent._get_gca_invoker()
            parent = parent.parent()
        # Fallback: create a new invoker
        from gca.vscode_invoker import DevNexGCAInvoker
        return DevNexGCAInvoker(repo_path=Path("."))

    def _get_output_dir(self) -> Path:
        artifacts_dir = self._artifacts_dir_edit.text().strip()
        if artifacts_dir:
            return Path(artifacts_dir)
        return Path("generated_artifacts")
