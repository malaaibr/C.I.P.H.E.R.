"""Full Traceability skill — S9N1."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import List

from core.console_logging import format_console_log, utc_timestamp
from skills.base_skill import ISkill

MODULE_NAME = "FullTraceSkill"


@dataclass
class TaskResult:
    task_id:   str
    status:    str
    output:    str
    summary:   str
    artifacts: List[str] = field(default_factory=list)
    errors:    List[str] = field(default_factory=list)


class FullTraceSkill(ISkill):
    """
    @brief Handles Stage 9: full HLD→LLD→Code→Test→UTD traceability matrix.
    Node: S9N1.
    """

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def execute(self, intent, context) -> TaskResult:
        self._trace("Executing FullTraceSkill for S9N1.")
        result = self.orchestrator.run_node("S9N1")

        return TaskResult(
            task_id="S9N1",
            status=result.status,
            output=result.output,
            summary=f"Full traceability matrix generated. Status: '{result.status}'.",
            artifacts=result.artifacts,
            errors=result.errors,
        )
