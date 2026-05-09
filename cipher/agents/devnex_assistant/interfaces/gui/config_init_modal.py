"""Config Init Modal — full-screen overlay with centered SWC project config card.

Startup behaviour:
  • First run  (SWC_name blank) — no Skip button; Get Started disabled until all
    required fields are filled.
  • Returning  (SWC_name set)   — pre-fills from existing config; Skip available.
  • "Load from file…"           — lets user browse to any config.json from a
    previous run or another project.
"""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea,
    QLabel, QLineEdit, QPushButton, QFileDialog,
    QWidget, QFrame, QApplication, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics

from interfaces.gui.styles import palette
from persistence.config_store import ConfigStore


# ── Field definitions ─────────────────────────────────────────────────────────
#  (key,  display_label,  placeholder,  browse,  required)
_FIELDS = [
    ("SWC_name",            "SWC Name *",                  "DLT",                 False, True),
    ("G_SWDD_TEMP",         "Generic LLD Template *",      "G_SWDD_TEMP.csv",     True,  True),
    ("SWC_name_C",          "Source Code (.c) *",          "DLT.c",               True,  True),
    ("SWC_name_H",          "Header File (.h) *",          "DLT.h",               True,  True),
    ("SWC_name_TEMP_LLD",   "Component LLD Template *",    "DLT_TEMP_LLD.csv",    True,  True),
    ("SWC_nameInspBaseLLD", "Inspection Base LLD *",       "DLTInspBaseLLD.csv",  True,  True),
    ("SWC_name_HLD",        "HLD Document *",              "DLT_HLD.csv",         True,  True),
    ("lds_file",            "Linker File *",               "Linkerscript",        True,  True),
    ("map_file",            "Map File (.map) *",           "map File",            True,  True),
    ("SWC_name_FUNC_req",   "Functional Requirements",     "DLT_FUNC_req.csv",    True,  False),
    ("workspace_path",      "Workspace Path",              ".",                   False, False),
]

_REQUIRED = {key for key, *_, req in _FIELDS if req}


class ConfigInitModal(QDialog):
    """
    @brief Full-screen overlay modal — must be dismissed before the main window
    appears.  On first launch it enforces that all required fields are filled.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        # Cover the full primary screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self._inputs: dict[str, QLineEdit] = {}
        self._go_btn:    QPushButton | None = None
        self._skip_btn:  QPushButton | None = None
        self._status_lbl: QLabel | None     = None
        self._loaded_lbl: QLabel | None     = None
        self._config_store = ConfigStore()
        self._is_first_run = True

        self._build_ui()
        self._preload()
        self._validate()

    # ── Semi-transparent overlay ───────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 195))

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Outer layout — vertically + horizontally centers the card
        outer_v = QVBoxLayout(self)
        outer_v.setContentsMargins(0, 0, 0, 0)
        outer_v.setSpacing(0)
        outer_v.addStretch(1)

        outer_h = QHBoxLayout()
        outer_h.setContentsMargins(0, 0, 0, 0)
        outer_h.setSpacing(0)
        outer_h.addStretch(1)

        card = self._build_card()
        outer_h.addWidget(card)

        outer_h.addStretch(1)
        outer_v.addLayout(outer_h)
        outer_v.addStretch(1)

    def _build_card(self) -> QFrame:
        screen = QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 900

        card = QFrame()
        card.setObjectName("ConfigCard")
        card.setFixedWidth(780)
        card.setMaximumHeight(int(avail_h * 0.92))
        card.setStyleSheet(
            "QFrame#ConfigCard {"
            f"  background-color: {palette.BG_APP};"
            f"  border: 1px solid {palette.BORDER_BRIGHT};"
            "  border-radius: 14px;"
            "}"
        )

        cl = QVBoxLayout(card)
        cl.setContentsMargins(44, 32, 44, 28)
        cl.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────────
        icon = QLabel("⬡")
        icon.setStyleSheet(f"color: {palette.ACCENT}; font-size: 28px; border: none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(icon)
        cl.addSpacing(6)

        title = QLabel("Initialize Project Config")
        title.setStyleSheet(
            f"color: {palette.TEXT1}; font-size: 17px; font-weight: bold; border: none;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(title)
        cl.addSpacing(4)

        sub = QLabel("Configure your SWC project files before launching DevNex Assistant")
        sub.setStyleSheet(f"color: {palette.TEXT3}; font-size: 11px; border: none;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(sub)
        cl.addSpacing(12)

        # ── Loaded-from-previous indicator ─────────────────────────────────────
        self._loaded_lbl = QLabel("")
        self._loaded_lbl.setStyleSheet(
            f"background-color: rgba(74,222,128,0.08); color: {palette.SUCCESS}; "
            f"font-size: 10px; padding: 5px 10px; border-radius: 5px; border: none;"
        )
        self._loaded_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loaded_lbl.setWordWrap(True)
        self._loaded_lbl.hide()
        cl.addWidget(self._loaded_lbl)
        cl.addSpacing(8)

        # ── Load-from-file row ─────────────────────────────────────────────────
        lf_row = QWidget()
        lf_row.setStyleSheet("background: transparent; border: none;")
        lfl = QHBoxLayout(lf_row)
        lfl.setContentsMargins(0, 0, 0, 0)
        lfl.addStretch()
        load_btn = QPushButton("↺  Load from file…")
        load_btn.setFixedHeight(28)
        load_btn.setStyleSheet(
            f"background: transparent; color: {palette.ACCENT}; "
            f"border: 1px solid {palette.ACCENT}; border-radius: 5px; "
            f"font-size: 10px; padding: 0 12px;"
        )
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._load_from_file)
        lfl.addWidget(load_btn)
        cl.addWidget(lf_row)
        cl.addSpacing(8)

        # ── Separator ──────────────────────────────────────────────────────────
        cl.addWidget(self._hr())
        cl.addSpacing(10)

        # ── Form in scroll area ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            f"QScrollBar::handle:vertical {{ background: {palette.BORDER_BRIGHT}; border-radius: 3px; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        max_form_h = max(200, int(avail_h * 0.92) - 310)
        scroll.setMaximumHeight(max_form_h)

        form_container = QWidget()
        form_container.setStyleSheet("background: transparent;")
        form = QFormLayout(form_container)
        form.setSpacing(9)
        form.setContentsMargins(0, 0, 4, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        for key, label, placeholder, has_browse, required in _FIELDS:
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(0)

            right_radius = "0 5px 5px 0" if has_browse else "5px"
            left_radius  = "5px 0 0 5px" if has_browse else "5px"
            border_right = "border-right: none;" if has_browse else ""

            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setStyleSheet(
                f"background-color: {palette.BG_INPUT}; color: {palette.TEXT1}; "
                f"border: 1px solid {palette.BORDER}; {border_right} "
                f"border-radius: {left_radius}; "
                f"padding: 5px 8px; font-family: 'Cascadia Code', monospace; font-size: 10pt;"
            )
            if required:
                inp.textChanged.connect(self._validate)
            self._inputs[key] = inp
            row_l.addWidget(inp)

            if has_browse:
                btn = QPushButton("…")
                btn.setFixedSize(30, 30)
                btn.setStyleSheet(
                    f"background-color: {palette.BG_CARD}; color: {palette.TEXT2}; "
                    f"border: 1px solid {palette.BORDER}; border-radius: 0 5px 5px 0;"
                )
                btn.clicked.connect(lambda _c, k=key: self._browse(k))
                row_l.addWidget(btn)

            lbl_text = label
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(
                f"color: {palette.TEXT2 if required else palette.TEXT3}; "
                f"font-size: 10px; background: transparent;"
            )
            form.addRow(lbl, row_w)

        scroll.setWidget(form_container)
        cl.addWidget(scroll, stretch=1)
        cl.addSpacing(12)

        # ── Validation status ──────────────────────────────────────────────────
        cl.addWidget(self._hr())
        cl.addSpacing(8)

        self._status_lbl = QLabel("Fill in all required fields (*) to continue.")
        self._status_lbl.setStyleSheet(
            f"color: {palette.TEXT3}; font-size: 10px; border: none;"
        )
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self._status_lbl)
        cl.addSpacing(10)

        # ── Buttons ────────────────────────────────────────────────────────────
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent; border: none;")
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)
        bl.addStretch()

        self._skip_btn = QPushButton("Skip — use existing")
        self._skip_btn.setFixedSize(160, 36)
        self._skip_btn.setStyleSheet(
            f"background: transparent; color: {palette.TEXT3}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 6px; font-size: 11px;"
        )
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self.reject)
        self._skip_btn.hide()   # shown only for returning users

        self._go_btn = QPushButton("⬡  Get Started")
        self._go_btn.setFixedSize(160, 36)
        self._go_btn.setEnabled(False)
        self._go_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._go_btn.setStyleSheet(self._go_btn_style(enabled=False))
        self._go_btn.clicked.connect(self._save_and_accept)

        bl.addWidget(self._skip_btn)
        bl.addWidget(self._go_btn)
        cl.addWidget(btn_row)

        return card

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _preload(self) -> None:
        config = self._config_store.load()
        swc    = config.get("SWC_name", "").strip()

        if swc:
            self._is_first_run = False
            for key, inp in self._inputs.items():
                inp.setText(config.get(key, ""))
            self._loaded_lbl.setText(
                f"↺  Loaded previous config — SWC: {swc}"
            )
            self._loaded_lbl.show()
            self._skip_btn.show()
        else:
            self._is_first_run = True
            self._loaded_lbl.hide()
            self._skip_btn.hide()

    def _validate(self) -> None:
        missing = [k for k in _REQUIRED if not self._inputs[k].text().strip()]
        n       = len(missing)
        ok      = n == 0

        self._go_btn.setEnabled(ok)
        self._go_btn.setStyleSheet(self._go_btn_style(enabled=ok))

        if ok:
            self._status_lbl.setText("✓  All required fields filled — ready to launch")
            self._status_lbl.setStyleSheet(
                f"color: {palette.SUCCESS}; font-size: 10px; "
                f"font-weight: bold; border: none;"
            )
        else:
            noun = "field" if n == 1 else "fields"
            self._status_lbl.setText(f"⚠  {n} required {noun} still missing")
            self._status_lbl.setStyleSheet(
                f"color: {palette.WARNING}; font-size: 10px; border: none;"
            )

    def _load_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Config File", "", "JSON config (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for key, inp in self._inputs.items():
                inp.setText(str(data.get(key, "")))
            swc = data.get("SWC_name", "")
            self._loaded_lbl.setText(
                f"↺  Loaded from file — SWC: {swc or '(unnamed)'}"
            )
            self._loaded_lbl.show()
            if not self._is_first_run:
                self._skip_btn.show()
            self._validate()
        except Exception as exc:
            self._loaded_lbl.setText(f"⚠  Could not load config: {exc}")
            self._loaded_lbl.setStyleSheet(
                f"background-color: rgba(240,80,96,0.08); color: {palette.ERROR}; "
                f"font-size: 10px; padding: 5px 10px; border-radius: 5px; border: none;"
            )
            self._loaded_lbl.show()

    def _browse(self, key: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Select {key}")
        if path:
            self._inputs[key].setText(path)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """Block Escape on first run so the user cannot bypass required fields."""
        if event.key() == Qt.Key.Key_Escape and self._is_first_run:
            return
        super().keyPressEvent(event)

    def _save_and_accept(self) -> None:
        config = {key: inp.text().strip() for key, inp in self._inputs.items()}
        if not config.get("workspace_path"):
            config["workspace_path"] = "."
        self._config_store.save(config)
        self.accept()

    def get_config(self) -> dict:
        return {key: inp.text().strip() for key, inp in self._inputs.items()}

    # ── Style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _go_btn_style(enabled: bool) -> str:
        if enabled:
            return (
                f"background-color: {palette.ACCENT}; color: #0b0e13; "
                f"border-radius: 6px; font-weight: bold; font-size: 12px; border: none;"
            )
        return (
            f"background-color: {palette.BG_CARD}; color: {palette.TEXT3}; "
            f"border-radius: 6px; font-size: 12px; border: none;"
        )

    @staticmethod
    def _hr() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {palette.BORDER}; border: none;")
        line.setFixedHeight(1)
        return line
