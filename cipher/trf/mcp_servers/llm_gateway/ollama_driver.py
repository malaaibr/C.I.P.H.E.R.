"""OllamaDriver — wraps Ollama HTTP API for TRIAGE tasks (T-011, ADR-0001 §4.2)."""

from __future__ import annotations

import os
import time

import httpx

from cipher.core.otel import traced
from cipher.trf.mcp_servers.llm_gateway.protocol import LLMResponse, LLMUnavailableError


class OllamaDriver:
    """LLMBackend implementation for local Ollama server."""

    def __init__(self) -> None:
        self._base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b")

    @property
    def backend_id(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    @traced(name="ollama.complete", attributes={"layer": "trf", "backend": "ollama"})
    async def complete(self, prompt: str, context: dict) -> LLMResponse:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": context.get("model", self._model),
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise LLMUnavailableError("ollama", str(e))

        data = resp.json()
        duration_ms = (time.perf_counter() - t0) * 1000
        return LLMResponse(
            text=data.get("response", ""),
            backend_id=self.backend_id,
            task_class="TRIAGE",
            duration_ms=duration_ms,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )
