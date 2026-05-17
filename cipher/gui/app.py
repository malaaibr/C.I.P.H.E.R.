"""
C.I.P.H.E.R GUI — Application entry point.

Boot sequence:
  1. SplashScreen (animated, ~6s)
  2. CipherMainWindow (HUD mode by default, DevNex mode on nav)
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from cipher.gui.main_window import CipherMainWindow
from cipher.gui.splash import SplashScreen
from cipher.gui.theme import apply_theme


def create_app() -> QApplication:
    """Create and configure the QApplication."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("C.I.P.H.E.R")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    return app


def launch() -> int:
    """Launch the CIPHER GUI with splash → main window."""
    app = create_app()
    window = CipherMainWindow()

    def _on_splash_done() -> None:
        window.show()
        window.append_log("C.I.P.H.E.R online. All subsystems ready.", level="SUCCESS")
        app.setQuitOnLastWindowClosed(True)

    splash = SplashScreen()
    splash.finished.connect(_on_splash_done)
    splash.show()

    return app.exec()


def main() -> None:
    """CLI entry point."""
    sys.exit(launch())


if __name__ == "__main__":
    main()
