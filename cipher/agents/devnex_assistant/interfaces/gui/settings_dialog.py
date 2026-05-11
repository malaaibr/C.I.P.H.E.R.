"""Settings dialog for DevNex GUI — Appearance and Paths only."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLineEdit, QCheckBox, QPushButton, QFormLayout, QLabel,
)
from PyQt6.QtCore import Qt

from interfaces.gui.settings_manager import SettingsManager
from interfaces.gui.styles import palette


class SettingsDialog(QDialog):
    """Tabbed settings dialog — Appearance / Paths."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("DevNex — Settings")
        self.resize(560, 340)
        self.setModal(True)
        self.setStyleSheet(
            f"QDialog {{ background: {palette.BG_APP}; color: {palette.TEXT1}; }}"
            f"QTabWidget::pane {{ border: 1px solid {palette.BORDER}; "
            f"background: {palette.BG_SIDEBAR}; border-radius: 0 0 6px 6px; }}"
            f"QTabBar::tab {{ background: {palette.BG_SIDEBAR}; color: {palette.TEXT2}; "
            f"padding: 7px 20px; font-size: 11px; border: 1px solid {palette.BORDER}; "
            f"border-bottom: none; margin-right: 2px; border-radius: 5px 5px 0 0; }}"
            f"QTabBar::tab:selected {{ background: {palette.ACCENT}; color: #0b0e13; "
            f"font-weight: bold; }}"
            f"QTabBar::tab:hover:!selected {{ background: {palette.BG_CARD}; color: {palette.TEXT1}; }}"
        )
        self.settings_manager = settings_manager
        self._build_ui()
        self._load_values()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(8)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_appearance_tab(), "Appearance")
        self._tabs.addTab(self._build_paths_tab(),      "Paths")
        root.addWidget(self._tabs, stretch=1)

        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        bl.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background: {palette.BG_CARD}; color: {palette.TEXT2}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 4px; padding: 5px 8px; }}"
            f"QPushButton:hover {{ color: {palette.TEXT1}; border-color: {palette.BORDER_BRIGHT}; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        bl.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet(
            f"QPushButton {{ background: {palette.ACCENT}; color: #0b0e13; "
            f"border: none; border-radius: 4px; padding: 5px 8px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #5af5d8; }}"
        )
        save_btn.clicked.connect(self._save)
        bl.addWidget(save_btn)

        root.addWidget(btn_row)

    # ── Appearance tab ────────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {palette.BG_SIDEBAR};")
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.font_size_input = QLineEdit()
        self.font_size_input.setPlaceholderText("Medium")
        self.font_size_input.setStyleSheet(self._input_style())

        self.sidebar_collapsed_cb = QCheckBox("Sidebar collapsed by default")
        self.sidebar_collapsed_cb.setStyleSheet(f"color: {palette.TEXT1};")
        self.debug_logging_cb = QCheckBox("Enable debug logging")
        self.debug_logging_cb.setStyleSheet(f"color: {palette.TEXT1};")

        form.addRow(self._form_lbl("Font Size:"),  self.font_size_input)
        form.addRow("", self.sidebar_collapsed_cb)
        form.addRow("", self.debug_logging_cb)
        return w

    # ── Paths tab ─────────────────────────────────────────────────────────────

    def _build_paths_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {palette.BG_SIDEBAR};")
        form = QFormLayout(w)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.run_storage_input = QLineEdit()
        self.run_storage_input.setStyleSheet(self._input_style())
        self.log_dir_input = QLineEdit()
        self.log_dir_input.setStyleSheet(self._input_style())

        form.addRow(self._form_lbl("Run Storage Dir:"), self.run_storage_input)
        form.addRow(self._form_lbl("Log Directory:"),   self.log_dir_input)
        return w

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _form_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {palette.TEXT2}; font-size: 11px;")
        return lbl

    @staticmethod
    def _input_style() -> str:
        return (
            f"QLineEdit {{ background: {palette.BG_INPUT}; color: {palette.TEXT1}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 4px; "
            f"padding: 5px 8px; font-size: 11px; }}"
            f"QLineEdit:focus {{ border-color: rgba(60,232,200,0.5); }}"
        )

    def _load_values(self) -> None:
        sm = self.settings_manager
        self.font_size_input.setText(str(sm.get(SettingsManager.KEY_FONT_SIZE, "Medium")))
        self.sidebar_collapsed_cb.setChecked(bool(sm.get(SettingsManager.KEY_SIDEBAR_COLLAPSED, False)))
        self.debug_logging_cb.setChecked(bool(sm.get(SettingsManager.KEY_DEBUG_LOGGING, False)))
        self.run_storage_input.setText(str(sm.get(SettingsManager.KEY_RUN_STORAGE_DIR, "")))
        self.log_dir_input.setText(str(sm.get(SettingsManager.KEY_LOG_DIR, "")))

    def _save(self) -> None:
        sm = self.settings_manager
        sm.set(SettingsManager.KEY_FONT_SIZE,         self.font_size_input.text().strip())
        sm.set(SettingsManager.KEY_SIDEBAR_COLLAPSED, self.sidebar_collapsed_cb.isChecked())
        sm.set(SettingsManager.KEY_DEBUG_LOGGING,     self.debug_logging_cb.isChecked())
        sm.set(SettingsManager.KEY_RUN_STORAGE_DIR,   self.run_storage_input.text().strip())
        sm.set(SettingsManager.KEY_LOG_DIR,           self.log_dir_input.text().strip())
        sm.save()
        self.accept()
