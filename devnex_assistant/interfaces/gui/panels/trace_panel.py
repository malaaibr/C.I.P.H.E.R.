"""Traceability tree panel — QTreeWidget: HLD→LLD→Code→Test hierarchy."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFrame,
)
from PyQt6.QtCore import Qt

from interfaces.gui.styles import palette

_TYPE_COLORS = {
    "hld":  "#5b8fff",
    "lld":  "#3ce8c8",
    "code": "#a78bfa",
    "test": "#b0bcd8",
}
_TYPE_ICONS = {"hld": "H", "lld": "L", "code": "C", "test": "T"}


class TracePanel(QWidget):
    """@brief Interactive traceability tree view — mirrors the HTML Trace tab."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Traceability Tree")
        title.setStyleSheet(f"color: {palette.TEXT1}; font-size: 13px; font-weight: bold;")
        hl.addWidget(title)
        sub = QLabel("HLD → LLD → Code → Test Cases")
        sub.setStyleSheet(f"color: {palette.TEXT3}; font-size: 11px;")
        hl.addWidget(sub)
        hl.addStretch()

        legend_frame = QFrame()
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(10)
        for t, color in _TYPE_COLORS.items():
            lbl = QLabel(f"[{_TYPE_ICONS[t]}] {t.upper()}")
            lbl.setStyleSheet(f"color: {color}; font-size: 10px; font-family: monospace;")
            legend_layout.addWidget(lbl)
        hl.addWidget(legend_frame)
        layout.addWidget(header)

        refresh_btn = QPushButton("Refresh from Artifacts")
        refresh_btn.setFixedHeight(28)
        refresh_btn.clicked.connect(self._load_from_artifacts)
        layout.addWidget(refresh_btn)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background-color: {palette.BG_CARD}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 8px; "
            f"color: {palette.TEXT1}; font-family: monospace; font-size: 10pt; }}"
            f"QTreeWidget::item:hover {{ background-color: {palette.BG_INPUT}; }}"
            f"QTreeWidget::item:selected {{ background-color: {palette.ACCENT}; color: #0b0e13; }}"
        )
        layout.addWidget(self._tree)

        # Summary bar
        self._summary = QLabel("Coverage: — HLD · — LLD · — Code · — Tests")
        self._summary.setStyleSheet(
            f"background-color: {palette.BG_CARD}; border: 1px solid {palette.BORDER}; "
            f"border-radius: 6px; padding: 8px 12px; color: {palette.TEXT2}; font-size: 10px;"
        )
        layout.addWidget(self._summary)

    def load_tree(self, data: list) -> None:
        """@brief Populate the tree from a list of HLD nodes."""
        self._tree.clear()
        for hld_node in data:
            self._add_node(self._tree.invisibleRootItem(), hld_node, depth=0)
        self._tree.expandAll()

    def _add_node(self, parent_item, node: dict, depth: int) -> None:
        text  = f"[{_TYPE_ICONS.get(node.get('type',''), '?')}]  {node.get('label', node.get('id',''))}"
        item  = QTreeWidgetItem([text])
        color = _TYPE_COLORS.get(node.get("type", ""), palette.TEXT1)

        if node.get("status") == "pass":
            color = palette.SUCCESS
        elif node.get("status") == "fail":
            color = palette.ERROR

        from PyQt6.QtGui import QColor, QBrush
        item.setForeground(0, QBrush(QColor(color)))
        parent_item.addChild(item)

        for child in node.get("children", []):
            self._add_node(item, child, depth + 1)

    def _load_from_artifacts(self) -> None:
        """@brief Try to load trace data from generated Full_Traceability_Matrix.csv."""
        artifact_dir = Path.home() / ".devnex" / "runs"
        if not artifact_dir.exists():
            self._summary.setText("No artifact runs found. Run S9N1 first.")
            return
        runs = sorted(artifact_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for run_dir in runs:
            matrix = run_dir / "Full_Traceability_Matrix.csv"
            if matrix.exists():
                self._summary.setText(f"Loaded from: {matrix}")
                return
        self._summary.setText("Full_Traceability_Matrix.csv not found. Run the full V-cycle first.")
