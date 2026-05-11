"""Test Generation skill — S6N1, S7N1, S8N1."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import List

from core.console_logging import format_console_log, utc_timestamp
from skills.base_skill import ISkill

MODULE_NAME = "TestGenSkill"


@dataclass
class TaskResult:
    task_id:   str
    status:    str
    output:    str
    summary:   str
    artifacts: List[str] = field(default_factory=list)
    errors:    List[str] = field(default_factory=list)


class TestGenSkill(ISkill):
    """
    @brief Handles Stages 6-8: test generation and UTD documentation.
    Nodes: S6N1, S7N1, S8N1.
    """

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def execute(self, intent, context) -> TaskResult:
        self._trace(f"Executing TestGenSkill for stage='{intent.vcycle_stage}'.")
        stage = intent.vcycle_stage or "S6N1"
        node_id = stage if stage in ("S6N1", "S7N1", "S8N1") else "S6N1"
        result = self.orchestrator.run_node(node_id)

        return TaskResult(
            task_id=node_id,
            status=result.status,
            output=result.output,
            summary=f"Test generation node {node_id} completed with status '{result.status}'.",
            artifacts=result.artifacts,
            errors=result.errors,
        )
