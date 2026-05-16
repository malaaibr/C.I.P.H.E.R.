"""TaskContract — A2A task submission and result schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskClass(StrEnum):
    TRIAGE = "TRIAGE"
    PLAN = "PLAN"
    CODE_GEN = "CODE_GEN"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskContract(BaseModel):
    """Immutable contract submitted to an agent via A2A."""

    task_id: UUID = Field(default_factory=uuid4)
    task_class: TaskClass
    skill_id: str
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    requester_agent_id: str
    target_agent_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_s: float = 300.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result envelope returned by an agent upon task completion."""

    task_id: UUID
    status: TaskStatus
    output: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)
    error_message: str | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float | None = None
