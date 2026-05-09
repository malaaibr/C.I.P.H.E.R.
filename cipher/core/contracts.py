"""Core contracts for the CIPHER local MVP scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Budget:
    tokens: int = 0
    seconds: int = 0


@dataclass(slots=True)
class TaskMessage:
    role: str
    parts: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class TaskEnvelope:
    task_id: str
    context_id: str
    trace_id: str
    message: TaskMessage
    metadata: dict[str, Any] = field(default_factory=dict)

