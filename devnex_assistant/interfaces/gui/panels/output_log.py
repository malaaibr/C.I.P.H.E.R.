"""Scrollable output log panel — QPlainTextEdit with colored GCA log lines."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor

from interfaces.gui.styles import palette


class OutputLogPanel(QWidget):
    """@brief Full-tab read-only log viewer — replicates Int_Agent output_log pattern."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header_row = QWidget()
        hr = QHBoxLayout(header_row)
        hr.setContentsMargins(0, 0, 0, 0)
        hr.setSpacing(8)
        title = QLabel("GCA Output Log")
        title.setStyleSheet(f"color: {palette.TEXT2}; font-size: 11px; font-weight: bold;")
        hr.addWidget(title)
        hr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(60, 24)
        clear_btn.clicked.connect(self._clear)
        hr.addWidget(clear_btn)
        layout.addWidget(header_row)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        self._log.setStyleSheet(
            f"background-color: {palette.BG_INPUT}; color: {palette.TEXT1}; "
            f"font-family: 'Cascadia Code', 'JetBrains Mono', monospace; "
            f"font-size: 10pt; border: none;"
        )
        layout.addWidget(self._log)

    def append_line(self, message: str, level: str = "INFO") -> None:
        """@brief Insert a colored log line — uses the same color map as Int_Agent."""
        _colors = {
            "INFO":    palette.LOG_INFO,
            "ERROR":   palette.LOG_ERROR,
            "ISSUE":   palette.LOG_ISSUE,
            "WARN":    palette.LOG_ISSUE,
            "SUCCESS": palette.LOG_SUCCESS,
        }
        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(_colors.get(level.upper(), palette.LOG_INFO)))
        cursor.insertText(f"{message}\n", fmt)
        self._log.setTextCursor(cursor)
        self._log.ensureCursorVisible()

    def _clear(self) -> None:
        self._log.clear()
