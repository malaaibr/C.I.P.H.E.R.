"""TraceFilterBar — horizontal chip row that filters the trace graph by NodeKind."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from core.trace_model import NodeKind

# Per-kind accent colors (mirrors TRACE_COLORS token table)
_KIND_ACCENT: dict[Optional[NodeKind], str] = {
    None:          "#3ce8c8",
    NodeKind.HLD:  "#00c8ff",
    NodeKind.LLD:  "#00ff9d",
    NodeKind.CODE: "#ffb700",
    NodeKind.TEST: "#8b5cf6",
    NodeKind.UTD:  "#ff3a8a",
}

_CHIP_DEFS: list[tuple[Optional[NodeKind], str]] = [
    (None,          "ALL"),
    (NodeKind.HLD,  "HLD"),
    (NodeKind.LLD,  "LLD"),
    (NodeKind.CODE, "CODE"),
    (NodeKind.TEST, "TEST"),
    (NodeKind.UTD,  "UTD"),
]


def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r}, {g}, {b}"


def _chip_style(kind: Optional[NodeKind], selected: bool) -> str:
    color = _KIND_ACCENT[kind]
    base = (
        "border-radius: 5px; font-size: 9pt; font-family: monospace; "
        "padding: 2px 12px; min-width: 52px; min-height: 24px;"
    )
    if selected:
        return (
            f"QPushButton {{ background-color: rgba({_rgb(color)}, 0.18); "
            f"color: {color}; border: 1px solid {color}; {base} }}"
        )
    return (
        f"QPushButton {{ background-color: transparent; "
        f"color: #2d5f7a; border: 1px solid #2d5f7a; {base} }}"
        f"QPushButton:hover {{ color: {color}; border-color: {color}; }}"
    )


class TraceFilterBar(QWidget):
    """
    Horizontal chip bar for column-level filtering.

    Emits ``filter_changed(Optional[NodeKind])``; ``None`` means "show all".
    """

    filter_changed = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current: Optional[NodeKind] = None
        self._buttons: dict[Optional[NodeKind], QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedHeight(44)
        self.setStyleSheet("background-color: #010a15;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        for kind, label in _CHIP_DEFS:
            btn = QPushButton(label)
            btn.setStyleSheet(_chip_style(kind, kind == self._current))
            btn.clicked.connect(lambda _, k=kind: self._select(k))
            self._buttons[kind] = btn
            layout.addWidget(btn)

        layout.addStretch()

    def _select(self, kind: Optional[NodeKind]) -> None:
        self._current = kind
        for k, btn in self._buttons.items():
            btn.setStyleSheet(_chip_style(k, k == self._current))
        self.filter_changed.emit(kind)

    def current_filter(self) -> Optional[NodeKind]:
        """Return the currently active filter kind (``None`` = ALL)."""
        return self._current
