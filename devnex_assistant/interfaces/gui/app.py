"""QApplication bootstrap — SplashScreen → ConfigInitModal → MainWindow."""

from __future__ import annotations


def launch_app(app) -> int:
    """
    @brief Startup sequence:
      1. SplashScreen (~9 s animated, then fades out).
      2. ConfigInitModal:
           • First run  — modal loops until all required fields are filled
             (Escape blocked, no Skip button).
           • Returning  — pre-filled from existing config; Skip available.
      3. MainWindow is shown after the modal is accepted or skipped.
    """
    from interfaces.gui.splash import SplashScreen
    from interfaces.gui.main_window import MainWindow
    from interfaces.gui.config_init_modal import ConfigInitModal
    from persistence.config_store import ConfigStore

    window = MainWindow()

    def _show_config_modal() -> None:
        """Loop modal until accepted (first run) or show once (returning user)."""
        while True:
            config = ConfigStore().load()
            swc = config.get("SWC_name", "").strip()

            if swc:
                # Returning user — show modal once, allow Skip
                modal = ConfigInitModal()
                modal.exec()   # Accept or Skip both proceed to main window
                break
            else:
                # First run — loop until the user fills all required fields
                modal = ConfigInitModal()
                result = modal.exec()
                if result == ConfigInitModal.DialogCode.Accepted:
                    break
                # result == Rejected means Skip was somehow hit or window closed —
                # on a true first run the Skip button is hidden and Escape is
                # blocked, so this branch should never be reached.  Guard anyway.
                if not config.get("SWC_name", "").strip():
                    continue   # re-show
                break

        # Sync config panel with whatever is now saved
        window._config_panel._load()

    def _on_splash_done() -> None:
        _show_config_modal()
        window.show()

    splash = SplashScreen()
    splash.finished.connect(_on_splash_done)
    splash.show()

    return app.exec()
