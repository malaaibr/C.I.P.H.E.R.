"""QThread worker for single V-cycle node execution."""

from __future__ import annotations

import threading

from PyQt6.QtCore import pyqtSignal

from interfaces.gui.workers.base_worker import BaseWorker
from core.errors import WorkflowAbortedError, NodeExecutionError


class NodeWorker(BaseWorker):
    """
    @brief Runs one V-cycle node in a QThread background thread.
    Mirrors Int_Agent InvokeWorker pattern.

    Human review gates use threading.Event:
    - Worker emits review_needed signal → GUI shows dialog → GUI calls worker.resume(approved)
    - Worker blocks on threading.Event until resume() is called
    """

    log_line       = pyqtSignal(str, str)    # (message, level)
    node_started   = pyqtSignal(str)         # node_id
    node_complete  = pyqtSignal(object)      # NodeResult
    review_needed  = pyqtSignal(str, str)    # (node_id, message)
    error_occurred = pyqtSignal(str)         # error message

    def __init__(self, orchestrator, node_id: str) -> None:
        super().__init__()
        self.orchestrator     = orchestrator
        self.node_id          = node_id
        self._review_event    = threading.Event()
        self._review_approved = False

    def resume(self, approved: bool) -> None:
        """@brief Called by GUI after human review dialog resolves."""
        self._review_approved = approved
        self._review_event.set()

    def _handle_human_review(self, node_id: str, message: str) -> bool:
        """@brief Block QThread until GUI responds to review dialog."""
        self._review_event.clear()
        self.review_needed.emit(node_id, message)
        self._review_event.wait()   # blocks this thread only — GUI stays responsive
        return self._review_approved

    def _execute(self):
        self.orchestrator.on_log           = lambda msg, lvl: self.log_line.emit(msg, lvl)
        self.orchestrator.on_node_started  = lambda nid: self.node_started.emit(nid)
        self.orchestrator.on_node_complete = lambda res: self.node_complete.emit(res)
        self.orchestrator.on_human_review  = self._handle_human_review

        result = self.orchestrator.run_node(self.node_id)
        return result

    def run(self) -> None:
        try:
            result = self._execute()
            self.node_complete.emit(result)
        except WorkflowAbortedError as e:
            self.error_occurred.emit(f"Aborted: {e}")
        except NodeExecutionError as e:
            self.error_occurred.emit(f"Node error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error in {self.node_id}: {e}")
