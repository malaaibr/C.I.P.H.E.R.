"""Config panel — QFormLayout for SWC project file inputs."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QFrame,
)
from PyQt6.QtCore import pyqtSignal

from interfaces.gui.styles import palette
from persistence.config_store import ConfigStore

_FIELDS = [
    ("SWC_name",            "SWC Name",                  "DLT"),
    ("G_SWDD_TEMP",         "Generic LLD Template",      "G_SWDD_TEMP.csv"),
    ("SWC_name_C",          "Source Code (.c)",          "DLT.c"),
    ("SWC_name_H",          "Header File (.h)",          "DLT.h"),
    ("SWC_name_TEMP_LLD",   "Component LLD Template",    "DLT_TEMP_LLD.csv"),
    ("SWC_name_FUNC_req",   "Functional Requirements",   "DLT_FUNC_req.csv"),
    ("SWC_nameInspBaseLLD", "Inspection Base LLD",       "DLTInspBaseLLD.csv"),
    ("SWC_name_HLD",        "HLD Document",              "DLT_HLD.csv"),
    ("Linker File",         "Linker Script (.lds)",      "Linkerscript"),
    ("map_file",            "Map File (.map)",           "map File"),
    ("workspace_path",      "Workspace Path",            "."),
]


class ConfigPanel(QWidget):
    """@brief SWC configuration form — mirrors the HTML prototype Config tab."""

    config_saved = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._inputs: dict[str, QLineEdit] = {}
        self._config_store = ConfigStore()
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Project Configuration")
        title.setStyleSheet(f"color: {palette.TEXT1}; font-size: 13px; font-weight: bold;")
        hl.addWidget(title)
        sub = QLabel("Saved to config.json · used by all workflow stages")
        sub.setStyleSheet(f"color: {palette.TEXT3}; font-size: 11px;")
        hl.addWidget(sub)
        hl.addStretch()
        save_btn = QPushButton("Save Config")
        save_btn.setFixedSize(110, 30)
        save_btn.setStyleSheet(
            f"background-color: {palette.ACCENT}; color: #0b0e13; "
            f"border-radius: 5px; font-weight: bold; font-size: 11px;"
        )
        save_btn.clicked.connect(self._save)
        hl.addWidget(save_btn)
        layout.addWidget(header)

        # Form grid
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        for key, label, placeholder in _FIELDS:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)

            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setStyleSheet(
                f"background-color: {palette.BG_INPUT}; color: {palette.TEXT1}; "
                f"border: 1px solid {palette.BORDER}; border-right: none; "
                f"border-radius: 5px 0 0 5px; padding: 6px 8px; "
                f"font-family: 'Cascadia Code', monospace; font-size: 10pt;"
            )
            self._inputs[key] = inp
            row_layout.addWidget(inp)

            if key not in ("SWC_name", "workspace_path"):
                browse_btn = QPushButton("…")
                browse_btn.setFixedSize(32, 32)
                browse_btn.setStyleSheet(
                    f"background-color: {palette.BG_CARD}; color: {palette.TEXT2}; "
                    f"border: 1px solid {palette.BORDER}; border-radius: 0 5px 5px 0;"
                )
                browse_btn.clicked.connect(lambda _checked, k=key: self._browse(k))
                row_layout.addWidget(browse_btn)

            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {palette.TEXT2}; font-size: 10px;")
            form.addRow(lbl, row_widget)

        layout.addWidget(form_widget)

        # JSON preview
        preview_frame = QFrame()
        preview_frame.setStyleSheet(
            f"background-color: {palette.BG_CARD}; border: 1px solid {palette.BORDER}; border-radius: 6px;"
        )
        pfl = QVBoxLayout(preview_frame)
        pfl.setContentsMargins(12, 8, 12, 8)
        preview_title = QLabel("config.json preview")
        preview_title.setStyleSheet(f"color: {palette.TEXT3}; font-size: 10px;")
        pfl.addWidget(preview_title)
        self._preview = QLabel()
        self._preview.setStyleSheet(
            f"color: {palette.ACCENT}; font-family: monospace; font-size: 10px;"
        )
        self._preview.setWordWrap(True)
        pfl.addWidget(self._preview)
        layout.addWidget(preview_frame)

    def _load(self) -> None:
        config = self._config_store.load()
        for key, inp in self._inputs.items():
            inp.setText(config.get(key, ""))

    def _save(self) -> None:
        config = {key: inp.text().strip() for key, inp in self._inputs.items()}
        self._config_store.save(config)
        import json
        self._preview.setText(json.dumps(config, indent=2))
        self.config_saved.emit(config)

    def _browse(self, key: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Select {key}")
        if path:
            self._inputs[key].setText(path)

    def get_config(self) -> dict:
        return {key: inp.text().strip() for key, inp in self._inputs.items()}
