"""MainCipher Shell — PyQt6 main window (T-030/T-031, WRAP+REFACTOR from CAR-001)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class CipherShell(QMainWindow):
    """
    CIPHER platform shell — hosts agent panels as dockable widgets.

    Replaces the monolithic MainWindow from CAR-001 with a panel-docking
    architecture per ADR-0005.
    """

    panel_mounted = pyqtSignal(str)
    panel_unmounted = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("C.I.P.H.E.R — Agentic Development Platform")
        self.setMinimumSize(1280, 800)
        self._panels: dict[str, QDockWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        header = QLabel("C.I.P.H.E.R Shell")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        self._workspace = QWidget()
        self._workspace_layout = QHBoxLayout(self._workspace)
        layout.addWidget(self._workspace)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Shell ready — no panels mounted")

    def mount_panel(self, panel_id: str, widget: QWidget, title: str) -> None:
        """Mount an agent panel as a dockable widget (ADR-0005 PanelDescriptor)."""
        if panel_id in self._panels:
            return

        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setObjectName(panel_id)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._panels[panel_id] = dock
        self.panel_mounted.emit(panel_id)
        self.statusBar().showMessage(f"Panel mounted: {title}")

    def unmount_panel(self, panel_id: str) -> None:
        """Remove a panel from the shell."""
        if panel_id not in self._panels:
            return
        dock = self._panels.pop(panel_id)
        self.removeDockWidget(dock)
        dock.deleteLater()
        self.panel_unmounted.emit(panel_id)

    def list_panels(self) -> list[str]:
        return list(self._panels.keys())
