"""Base QThread worker for non-blocking PyQt6 GUI operations."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """
    Abstract QThread worker.

    Subclasses implement _execute() which runs in the worker thread.
    Results and errors are dispatched back to the Qt main thread via signals.

    Usage::

        worker = SomeWorker(...)
        worker.progress_signal.connect(self._on_progress)
        worker.result_signal.connect(self._on_complete)
        worker.error_signal.connect(self._on_error)
        worker.start()
        # later:
        worker.cancel()
    """

    progress_signal: pyqtSignal = pyqtSignal(int, str)
    result_signal:   pyqtSignal = pyqtSignal(object)
    error_signal:    pyqtSignal = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False

    def cancel(self) -> None:
        """Signal the worker to stop at the next checkpoint."""
        self._cancelled = True

    def run(self) -> None:
        """Called by QThread.start(); delegates to _execute()."""
        try:
            result = self._execute()
            if not self._cancelled:
                self.result_signal.emit(result)
        except Exception as exc:
            self.error_signal.emit(str(exc))

    def _execute(self) -> Any:
        """Subclasses must override this to perform the actual work."""
        raise NotImplementedError("BaseWorker subclasses must implement _execute().")

    def safe_emit_progress(self, percent: int, message: str) -> None:
        """Emit a bounded progress update."""
        if not self._cancelled:
            self.progress_signal.emit(max(0, min(100, percent)), message)
