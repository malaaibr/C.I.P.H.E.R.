"""GCAHttpDriver — HTTP bridge to GCA for CODE_GEN tasks (T-012, ADR-0002)."""

from __future__ import annotations

import os
import time

import httpx

from cipher.core.otel import traced
from cipher.trf.mcp_servers.llm_gateway.protocol import LLMResponse, LLMUnavailableError


class GCAHttpDriver:
    """LLMBackend implementation for GCA via HTTP bridge."""

    def __init__(self) -> None:
        self._bridge_url = os.environ.get("GCA_BRIDGE_URL", "http://127.0.0.1:37778")

    @property
    def backend_id(self) -> str:
        return "gca_http"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._bridge_url}/health")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    @traced(name="gca.complete", attributes={"layer": "trf", "backend": "gca_http"})
    async def complete(self, prompt: str, context: dict) -> LLMResponse:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{self._bridge_url}/v1/generate",
                    json={
                        "prompt": prompt,
                        "workspace_hint": context.get("workspace_hint", ""),
                    },
                )
                resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise LLMUnavailableError("gca_http", str(e))

        data = resp.json()
        duration_ms = (time.perf_counter() - t0) * 1000
        return LLMResponse(
            text=data.get("text", data.get("response", "")),
            backend_id=self.backend_id,
            task_class="CODE_GEN",
            duration_ms=duration_ms,
            instance_id=data.get("instance_id"),
        )
