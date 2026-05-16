"""DevNex Workflow Widget — panel content for V-cycle submission (T-033)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DevNexWorkflowWidget(QWidget):
    """UI for submitting HLD prompts and viewing LLD generation progress."""

    task_submitted = pyqtSignal(str)  # emits prompt text

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("DevNex V-Cycle — S1N1 LLD Generation"))

        layout.addWidget(QLabel("HLD Prompt:"))
        self._prompt_input = QPlainTextEdit()
        self._prompt_input.setPlaceholderText(
            "Enter High-Level Design requirements here..."
        )
        layout.addWidget(self._prompt_input)

        self._submit_btn = QPushButton("Generate LLD")
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

        self._status_label = QLabel("Status: Idle")
        layout.addWidget(self._status_label)

        layout.addWidget(QLabel("Output:"))
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        layout.addWidget(self._output)

    def _on_submit(self) -> None:
        prompt = self._prompt_input.toPlainText().strip()
        if prompt:
            self._status_label.setText("Status: Submitting...")
            self._submit_btn.setEnabled(False)
            self.task_submitted.emit(prompt)

    def set_status(self, status: str) -> None:
        self._status_label.setText(f"Status: {status}")

    def set_output(self, text: str) -> None:
        self._output.setPlainText(text)
        self._submit_btn.setEnabled(True)

    def append_output(self, text: str) -> None:
        self._output.appendPlainText(text)
