"""SkillLoader — resolves skill_id to executable Skill instances (T-022)."""

from __future__ import annotations

from typing import Protocol

from cipher.core.schemas.task_contract import TaskContract, TaskResult


class Skill(Protocol):
    """Protocol for all CIPHER skills."""

    @property
    def skill_id(self) -> str: ...

    async def execute(self, task: TaskContract) -> TaskResult: ...


class SkillLoader:
    """Registry-based skill resolution (Stages 1+2 from DevNex)."""

    def __init__(self) -> None:
        self._registry: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._registry[skill.skill_id] = skill

    def resolve(self, skill_id: str) -> Skill | None:
        return self._registry.get(skill_id)

    def list_skills(self) -> list[str]:
        return list(self._registry.keys())


_loader_instance: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SkillLoader()
    return _loader_instance
