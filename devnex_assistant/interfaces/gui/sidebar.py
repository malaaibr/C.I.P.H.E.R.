"""Left navigation sidebar for DevNex GUI — adapted from Int_Agent Sidebar."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget,
)
from PyQt6.QtCore import Qt

from interfaces.gui.constants import APP_NAME, APP_SUBTITLE, APP_VERSION, NAV_ITEMS, SIDEBAR_W
from interfaces.gui.styles import palette


class Sidebar(QFrame):
    """240 px wide dark sidebar with V-cycle nav buttons and run status card."""

    def __init__(self, parent=None, on_nav: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_W)
        self.setStyleSheet(f"background-color: {palette.BG_SIDEBAR}; border: none;")
        self._on_nav = on_nav
        self._nav_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self.set_active(NAV_ITEMS[0])

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 8)
        root.setSpacing(0)

        # ── Logo + title ──────────────────────────────────────────────
        top = QWidget()
        tl  = QHBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(8)

        # Hexagon icon (text stand-in)
        icon_lbl = QLabel("⬡")
        icon_lbl.setStyleSheet(f"color: {palette.ACCENT}; font-size: 22px;")
        tl.addWidget(icon_lbl)

        title_col = QWidget()
        tvl = QVBoxLayout(title_col)
        tvl.setContentsMargins(0, 0, 0, 0)
        tvl.setSpacing(1)
        app_name_lbl = QLabel(APP_NAME)
        app_name_lbl.setStyleSheet(f"color: {palette.TEXT1}; font-size: 13px; font-weight: bold;")
        subtitle_lbl = QLabel(APP_SUBTITLE)
        subtitle_lbl.setStyleSheet(f"color: {palette.TEXT3}; font-size: 10px;")
        tvl.addWidget(app_name_lbl)
        tvl.addWidget(subtitle_lbl)
        tl.addWidget(title_col)
        tl.addStretch()
        root.addWidget(top)
        root.addSpacing(8)

        root.addWidget(self._divider())
        root.addSpacing(8)

        # ── Nav buttons ───────────────────────────────────────────────
        for label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setFixedHeight(36)
            btn.setStyleSheet(self._btn_style(active=False))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked, lbl=label: self._nav_clicked(lbl))
            self._nav_buttons[label] = btn
            root.addWidget(btn)
            root.addSpacing(2)

        root.addStretch()
        root.addWidget(self._divider())
        root.addSpacing(8)

        # ── SWC name + version footer ──────────────────────────────────
        self._swc_lbl = QLabel("SWC: —")
        self._swc_lbl.setStyleSheet(f"color: {palette.TEXT3}; font-size: 10px;")
        self._swc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._swc_lbl)
        root.addSpacing(4)

        footer = QLabel(f"{APP_VERSION}")
        footer.setStyleSheet(f"color: {palette.TEXT3}; font-size: 10px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

    def set_active(self, panel_name: str) -> None:
        for label, btn in self._nav_buttons.items():
            active = label.lower() == panel_name.lower() or panel_name.lower() in label.lower()
            btn.setStyleSheet(self._btn_style(active))

    def set_swc_name(self, swc: str) -> None:
        self._swc_lbl.setText(f"SWC: {swc or '—'}")

    def _nav_clicked(self, label: str) -> None:
        self.set_active(label)
        if self._on_nav is not None:
            self._on_nav(label)

    @staticmethod
    def _btn_style(active: bool) -> str:
        bg = palette.ACCENT if active else "transparent"
        fg = "#0b0e13" if active else palette.TEXT2
        return (
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border-radius: 6px; text-align: left; padding: 6px 10px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {palette.BG_CARD}; color: {palette.TEXT1}; }}"
        )

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {palette.BORDER};")
        line.setFixedHeight(1)
        return line
