"""ReviewWorker — QThread that drives the TechReviewOrchestrator.

Mirrors NodeWorker / FullRunWorker patterns exactly:
- Emits signals for log lines, node start/complete, progress, and errors
- Runs entirely in a background QThread to keep the GUI responsive
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from gca.vscode_invoker import DevNexGCAInvoker
from review.review_models import ReviewReport, StageResult
from review.review_orchestrator import ReviewConfig, TechReviewOrchestrator
from review.review_reporter import ReviewReporter


class ReviewWorker(QThread):
    """
    Background worker for the full R1N1–R9N1 review pipeline.

    Signals
    -------
    log_line(message, level)
    node_started(node_id)
    node_complete(StageResult)
    progress(pct, node_id, label)
    review_finished(ReviewReport)
    error_occurred(message)
    """

    log_line       = pyqtSignal(str, str)
    node_started   = pyqtSignal(str)
    node_complete  = pyqtSignal(object)          # StageResult
    progress       = pyqtSignal(int, str, str)   # pct, node_id, label
    review_finished= pyqtSignal(object)          # ReviewReport
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        config:       ReviewConfig,
        gca_invoker:  DevNexGCAInvoker,
        output_dir:   Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config      = config
        self._gca         = gca_invoker
        self._output_dir  = output_dir

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self) -> None:
        try:
            orchestrator = TechReviewOrchestrator(
                config            = self._config,
                gca_invoker       = self._gca,
                on_log            = self._emit_log,
                on_node_started   = self._emit_node_started,
                on_node_complete  = self._emit_node_complete,
                progress_callback = self._emit_progress,
            )
            report = orchestrator.run_all()

            # Persist reports
            reporter = ReviewReporter(self._output_dir)
            json_path, md_path = reporter.write(report)
            self._emit_log(
                f"Review reports saved: {json_path.name}, {md_path.name}", "SUCCESS"
            )
            self.review_finished.emit(report)

        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ── Signal helpers ────────────────────────────────────────────────────────

    def _emit_log(self, message: str, level: str) -> None:
        self.log_line.emit(message, level)

    def _emit_node_started(self, node_id: str) -> None:
        self.node_started.emit(node_id)

    def _emit_node_complete(self, result: StageResult) -> None:
        self.node_complete.emit(result)

    def _emit_progress(self, pct: int, node_id: str, label: str) -> None:
        self.progress.emit(pct, node_id, label)
