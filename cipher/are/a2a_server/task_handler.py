"""Task handler — dispatches tasks to registered skills (T-021)."""

from __future__ import annotations

from cipher.core.otel import traced
from cipher.core.schemas.task_contract import TaskContract, TaskResult, TaskStatus


@traced(name="a2a.handle_task", attributes={"layer": "are"})
async def handle_task(task: TaskContract) -> TaskResult:
    from cipher.are.skill_loader.loader import get_skill_loader

    loader = get_skill_loader()
    skill = loader.resolve(task.skill_id)
    if skill is None:
        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            error_message=f"Skill not found: {task.skill_id}",
        )
    return await skill.execute(task)
