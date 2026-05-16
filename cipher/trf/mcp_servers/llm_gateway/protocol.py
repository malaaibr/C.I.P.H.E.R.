"""LLMBackend Protocol and response model (T-010, ADR-0001 §4.1)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Unified response from any LLM backend."""

    text: str
    backend_id: str
    task_class: str
    duration_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    instance_id: str | None = None


class LLMUnavailableError(Exception):
    """Raised when a backend cannot fulfill a request."""

    def __init__(self, backend: str, reason: str) -> None:
        self.backend = backend
        self.reason = reason
        super().__init__(f"Backend '{backend}' unavailable: {reason}")


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol that all LLM backend drivers must satisfy."""

    async def complete(self, prompt: str, context: dict) -> LLMResponse: ...

    async def is_available(self) -> bool: ...

    @property
    def backend_id(self) -> str: ...
