"""DevNex Orchestrator A2A Adapter (T-023)."""

from __future__ import annotations

from cipher.core.otel import traced
from cipher.core.schemas.task_contract import TaskContract, TaskResult, TaskStatus


class DevNexAdapter:
    """
    Adapts A2A TaskContract into a LangGraph workflow execution.

    Maps skill_id to workflow node sequence and returns TaskResult.
    """

    def __init__(self) -> None:
        self._engine = None

    @property
    def skill_id(self) -> str:
        return "devnex_orchestrator"

    @traced(name="devnex.execute", attributes={"layer": "aal"})
    async def execute(self, task: TaskContract) -> TaskResult:
        from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill

        skill = S1N1Skill()
        return await skill.execute(task)
