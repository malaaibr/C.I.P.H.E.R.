"""DevNex Assistant — PyQt6 GUI entry point."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main() -> None:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("[ERROR] PyQt6 not installed. Run: pip install PyQt6>=6.6.0")
        sys.exit(1)

    # Start file logging before anything else so every print() is captured
    from core.file_logger import setup_file_logging, close_file_logging
    log_path = setup_file_logging()
    print(f"[DevNex] Session log: {log_path}")

    from interfaces.gui.app import launch_app

    app = QApplication(sys.argv)
    app.setApplicationName("DevNex Assistant")
    app.setOrganizationName("DevNex")

    from PyQt6.QtGui import QIcon
    from interfaces.gui.icon import make_hex_pixmap
    app.setWindowIcon(QIcon(make_hex_pixmap(256)))

    exit_code = launch_app(app)
    close_file_logging()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
