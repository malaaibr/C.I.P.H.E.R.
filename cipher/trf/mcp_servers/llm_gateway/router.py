"""TaskClassRouter — maps task_class to LLM backend (T-013, ADR-0001 §4.4)."""

from __future__ import annotations

from cipher.core.schemas.task_contract import TaskClass
from cipher.trf.mcp_servers.llm_gateway.gca_http_driver import GCAHttpDriver
from cipher.trf.mcp_servers.llm_gateway.ollama_driver import OllamaDriver
from cipher.trf.mcp_servers.llm_gateway.protocol import (
    LLMBackend,
    LLMResponse,
    LLMUnavailableError,
)

_ROUTING_TABLE: dict[TaskClass, type] = {
    TaskClass.TRIAGE: OllamaDriver,
    TaskClass.PLAN: OllamaDriver,  # Gemini CLI stub — uses Ollama for POC
    TaskClass.CODE_GEN: GCAHttpDriver,
}

_router_instance: TaskClassRouter | None = None


class TaskClassRouter:
    """Routes LLM requests to the appropriate backend based on task_class."""

    def __init__(self) -> None:
        self._drivers: dict[str, LLMBackend] = {}

    def _get_driver(self, task_class: TaskClass) -> LLMBackend:
        key = task_class.value
        if key not in self._drivers:
            driver_cls = _ROUTING_TABLE[task_class]
            self._drivers[key] = driver_cls()
        return self._drivers[key]

    async def route(
        self, prompt: str, task_class: TaskClass, context: dict
    ) -> LLMResponse:
        driver = self._get_driver(task_class)
        if not await driver.is_available():
            raise LLMUnavailableError(
                driver.backend_id, f"Backend not available for {task_class}"
            )
        return await driver.complete(prompt, context)


def get_router() -> TaskClassRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = TaskClassRouter()
    return _router_instance
