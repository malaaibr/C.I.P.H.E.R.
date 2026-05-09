"""QThread worker that runs the full V-cycle S1N1 → S9N1 sequentially."""

from __future__ import annotations

import threading

from PyQt6.QtCore import pyqtSignal

from interfaces.gui.workers.base_worker import BaseWorker
from core.errors import WorkflowAbortedError, NodeExecutionError


class FullRunWorker(BaseWorker):
    """
    @brief Runs all V-cycle nodes S1N1 → S9N1 in a single QThread.
    Human review gates use the same threading.Event pattern as NodeWorker.
    """

    log_line       = pyqtSignal(str, str)
    node_started   = pyqtSignal(str)
    node_complete  = pyqtSignal(object)
    review_needed  = pyqtSignal(str, str)
    progress       = pyqtSignal(int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, orchestrator) -> None:
        super().__init__()
        self.orchestrator     = orchestrator
        self._review_event    = threading.Event()
        self._review_approved = False

    def resume(self, approved: bool) -> None:
        """@brief Called by GUI after human review dialog resolves."""
        self._review_approved = approved
        self._review_event.set()

    def _handle_human_review(self, node_id: str, message: str) -> bool:
        self._review_event.clear()
        self.review_needed.emit(node_id, message)
        self._review_event.wait()
        return self._review_approved

    def _execute(self):
        self.orchestrator.on_log           = lambda msg, lvl: self.log_line.emit(msg, lvl)
        self.orchestrator.on_node_started  = lambda nid: self.node_started.emit(nid)
        self.orchestrator.on_node_complete = lambda res: self.node_complete.emit(res)
        self.orchestrator.on_human_review  = self._handle_human_review

        def _progress(pct: int, msg: str) -> None:
            self.progress.emit(pct, msg)
            self.safe_emit_progress(pct, msg)

        results = self.orchestrator.run_all(progress_callback=_progress)
        return results

    def run(self) -> None:
        try:
            results = self._execute()
            self.result_signal.emit(results)
        except WorkflowAbortedError as e:
            self.error_occurred.emit(f"Aborted: {e}")
        except NodeExecutionError as e:
            self.error_occurred.emit(f"Node error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {e}")
