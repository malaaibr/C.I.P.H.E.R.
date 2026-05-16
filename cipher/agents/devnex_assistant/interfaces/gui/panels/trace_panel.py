"""TracePanel — full-featured V-cycle trace graph panel.

Hierarchy
---------
TracePanel (QWidget)
├── _header_strip        QWidget  — title + stats + FIT / RELOAD buttons
├── _filter_bar          TraceFilterBar  — [ ALL ] [ HLD ] [ LLD ] [ CODE ] [ TEST ] [ UTD ]
├── body
│   ├── _canvas          TraceGraphCanvas  — bezier diagram surface
│   └── _detail_drawer   QFrame  — slides in on node selection (320 px)
└── QFileSystemWatcher   — auto-reload when trace_graph.json changes
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QFileSystemWatcher
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.trace_loader import load_trace_graph
from core.trace_model import NodeKind, TraceGraph
from interfaces.gui.panels.trace_filter_bar import TraceFilterBar
from interfaces.gui.panels.trace_graph_canvas import TraceGraphCanvas

log = logging.getLogger(__name__)

_DEFAULT_ARTIFACTS = Path("generated_artifacts")

_KIND_ACCENT: dict[NodeKind, str] = {
    NodeKind.HLD:  "#00c8ff",
    NodeKind.LLD:  "#00ff9d",
    NodeKind.CODE: "#ffb700",
    NodeKind.TEST: "#8b5cf6",
    NodeKind.UTD:  "#ff3a8a",
}

_BTN_BASE = (
    "border-radius: 4px; font-size: 8pt; font-family: monospace; padding: 0 8px;"
)


class TracePanel(QWidget):
    """V-cycle traceability graph — HLD → LLD → CODE → TEST → UTD."""

    def __init__(
        self,
        artifacts_dir: Path = _DEFAULT_ARTIFACTS,
        on_open_source: Optional[Callable[[str, int], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._artifacts_dir  = Path(artifacts_dir)
        self._on_open_source = on_open_source or _default_open_source
        self._graph: TraceGraph = TraceGraph()
        self._selected_node_id: Optional[str] = None

        self._build_ui()
        self._setup_watcher()
        self.reload()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header_strip())

        self._filter_bar = TraceFilterBar()
        root.addWidget(self._filter_bar)

        # Body: canvas (flex) + detail drawer (fixed 320 px)
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._canvas = TraceGraphCanvas()
        body_layout.addWidget(self._canvas, stretch=1)

        self._detail_drawer = self._build_detail_drawer()
        self._detail_drawer.setVisible(False)
        body_layout.addWidget(self._detail_drawer)

        root.addWidget(body, stretch=1)

        # Wire signals
        self._filter_bar.filter_changed.connect(self._canvas.set_filter)
        self._canvas.node_selected.connect(self._show_detail)
        self._canvas.node_activated.connect(self._on_activate_node)

    def _build_header_strip(self) -> QWidget:
        strip = QWidget()
        strip.setFixedHeight(36)
        strip.setStyleSheet(
            "background-color: #010a15; border-bottom: 1px solid #1a2e40;"
        )
        hl = QHBoxLayout(strip)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(8)

        title = QLabel("TRACE GRAPH")
        title.setStyleSheet(
            "color: #2d5f7a; font-size: 8pt; font-family: monospace; letter-spacing: 3px;"
        )
        hl.addWidget(title)
        hl.addStretch()

        self._stats_lbl = QLabel("0 nodes · 0 links")
        self._stats_lbl.setStyleSheet(
            "color: #2d5f7a; font-size: 9pt; font-family: monospace;"
        )
        hl.addWidget(self._stats_lbl)

        fit_btn = QPushButton("⊞ FIT")
        fit_btn.setFixedHeight(24)
        fit_btn.setStyleSheet(
            f"QPushButton {{ background-color: #041624; color: #2d5f7a; "
            f"border: 1px solid #2d5f7a; {_BTN_BASE} }}"
            f"QPushButton:hover {{ color: #00c8ff; border-color: #00c8ff; }}"
        )
        fit_btn.clicked.connect(lambda: self._canvas.fit_view())
        hl.addWidget(fit_btn)

        reload_btn = QPushButton("↻ RELOAD")
        reload_btn.setFixedHeight(24)
        reload_btn.setStyleSheet(
            f"QPushButton {{ background-color: #041624; color: #2d5f7a; "
            f"border: 1px solid #2d5f7a; {_BTN_BASE} }}"
            f"QPushButton:hover {{ color: #00ff9d; border-color: #00ff9d; }}"
        )
        reload_btn.clicked.connect(self.reload)
        hl.addWidget(reload_btn)

        return strip

    def _build_detail_drawer(self) -> QFrame:
        drawer = QFrame()
        drawer.setFixedWidth(320)
        drawer.setStyleSheet(
            "QFrame { background-color: #041624; border-left: 1px solid #1a2e40; }"
        )

        layout = QVBoxLayout(drawer)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # ID + kind badge row
        id_row = QHBoxLayout()
        self._d_id = QLabel("")
        self._d_id.setStyleSheet(
            "color: #b8e8ff; font-size: 10pt; font-family: monospace; font-weight: bold;"
        )
        id_row.addWidget(self._d_id)
        id_row.addStretch()
        self._d_kind = QLabel("")
        self._d_kind.setStyleSheet(
            "color: #010a15; font-size: 8pt; font-family: monospace; "
            "padding: 2px 6px; border-radius: 3px;"
        )
        id_row.addWidget(self._d_kind)
        layout.addLayout(id_row)

        self._d_sublabel = QLabel("")
        self._d_sublabel.setStyleSheet(
            "color: #2d5f7a; font-size: 8pt; font-family: monospace;"
        )
        layout.addWidget(self._d_sublabel)

        self._d_title = QLabel("")
        self._d_title.setWordWrap(True)
        self._d_title.setStyleSheet(
            "color: #b8e8ff; font-size: 9pt; font-family: monospace;"
        )
        layout.addWidget(self._d_title)

        self._d_asil = QLabel("")
        self._d_asil.setStyleSheet(
            "background-color: #f5a623; color: #010a15; font-size: 8pt; "
            "font-family: monospace; padding: 2px 8px; border-radius: 3px;"
        )
        self._d_asil.setVisible(False)
        layout.addWidget(self._d_asil)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a2e40;")
        layout.addWidget(sep)

        nbr_lbl = QLabel("LINKED NODES")
        nbr_lbl.setStyleSheet(
            "color: #2d5f7a; font-size: 7pt; font-family: monospace; letter-spacing: 2px;"
        )
        layout.addWidget(nbr_lbl)

        self._d_neighbors = QListWidget()
        self._d_neighbors.setStyleSheet(
            "QListWidget { background-color: #010a15; border: 1px solid #1a2e40; "
            "color: #b8e8ff; font-family: monospace; font-size: 9pt; }"
            "QListWidget::item:hover { background-color: #0d1f35; }"
            "QListWidget::item:selected { background-color: #1a2e40; }"
        )
        self._d_neighbors.setMaximumHeight(160)
        self._d_neighbors.itemClicked.connect(self._on_neighbor_clicked)
        layout.addWidget(self._d_neighbors)

        layout.addStretch()

        self._open_btn = QPushButton("Open in Editor")
        self._open_btn.setFixedHeight(30)
        self._open_btn.setStyleSheet(
            "QPushButton { background-color: #041624; color: #00c8ff; "
            "border: 1px solid #00c8ff; border-radius: 4px; font-size: 9pt; }"
            "QPushButton:hover { background-color: #0d2a3d; }"
        )
        self._open_btn.setVisible(False)
        self._open_btn.clicked.connect(self._on_open_btn)
        layout.addWidget(self._open_btn)

        close_btn = QPushButton("✕  Close")
        close_btn.setFixedHeight(28)
        close_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #2d5f7a; "
            "border: 1px solid #2d5f7a; border-radius: 4px; font-size: 8pt; }"
            "QPushButton:hover { color: #ff3a8a; border-color: #ff3a8a; }"
        )
        close_btn.clicked.connect(self._hide_detail)
        layout.addWidget(close_btn)

        return drawer

    def _setup_watcher(self) -> None:
        watch_path = str(self._artifacts_dir / "trace_graph.json")
        self._watcher = QFileSystemWatcher([watch_path])
        self._watcher.fileChanged.connect(self._on_file_changed)

    def _on_file_changed(self, path: str) -> None:
        # Qt removes the path from the watcher on some platforms after a change
        self._watcher.addPath(path)
        log.debug("trace_graph.json changed — auto-reloading")
        self.reload()

    # ── Public API ────────────────────────────────────────────────────────────

    def reload(self) -> None:
        """Reload the TraceGraph from *artifacts_dir* and refresh the canvas."""
        self._graph = load_trace_graph(self._artifacts_dir)
        self._canvas.set_graph(self._graph)
        n = len(self._graph.nodes)
        e = len(self._graph.edges)
        self._stats_lbl.setText(f"{n} nodes  ·  {e} links")
        self._hide_detail()

    def update_from_state(self, state: dict) -> None:
        """Called by WorkflowPanel / MainWindow after each stage completes."""
        self.reload()

    # ── Detail drawer helpers ─────────────────────────────────────────────────

    def _show_detail(self, node_id: str) -> None:
        node = next((n for n in self._graph.nodes if n.id == node_id), None)
        if node is None:
            return
        self._selected_node_id = node_id
        accent = _KIND_ACCENT.get(node.kind, "#b8e8ff")

        self._d_id.setText(node.id)
        self._d_kind.setText(node.kind.value)
        self._d_kind.setStyleSheet(
            f"background-color: {accent}; color: #010a15; font-size: 8pt; "
            f"font-family: monospace; padding: 2px 6px; border-radius: 3px;"
        )
        self._d_sublabel.setText(node.sublabel)
        self._d_title.setText(node.title or node.label)

        if node.asil:
            self._d_asil.setText(f"ASIL {node.asil}")
            self._d_asil.setVisible(True)
        else:
            self._d_asil.setVisible(False)

        self._d_neighbors.clear()
        for nid in self._graph.neighbors(node_id):
            neighbor = next((n for n in self._graph.nodes if n.id == nid), None)
            if neighbor is None:
                continue
            item = QListWidgetItem(f"[{neighbor.kind.value}] {nid}")
            item.setForeground(QBrush(QColor(_KIND_ACCENT.get(neighbor.kind, "#b8e8ff"))))
            item.setData(Qt.ItemDataRole.UserRole, nid)
            self._d_neighbors.addItem(item)

        self._open_btn.setVisible(bool(node.source_file))
        self._detail_drawer.setVisible(True)

    def _hide_detail(self) -> None:
        self._selected_node_id = None
        self._detail_drawer.setVisible(False)

    def _on_neighbor_clicked(self, item: QListWidgetItem) -> None:
        nid = item.data(Qt.ItemDataRole.UserRole)
        if nid:
            self._canvas.focus_node(nid)

    def _on_open_btn(self) -> None:
        if self._selected_node_id:
            self._on_activate_node(self._selected_node_id)

    def _on_activate_node(self, node_id: str) -> None:
        node = next((n for n in self._graph.nodes if n.id == node_id), None)
        if node and node.source_file:
            self._on_open_source(node.source_file, node.line_no)


# ── Default source-file opener ────────────────────────────────────────────────

def _default_open_source(path: str, line_no: int) -> None:
    """Open *path*:*line_no* in VS Code, falling back to the OS default."""
    try:
        target = f"{path}:{line_no}" if line_no else path
        subprocess.Popen(["code", "-g", target])
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not open %s: %s", path, exc)
