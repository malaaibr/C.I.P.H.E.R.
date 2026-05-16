"""CipherShellClient — A2A task submission from GUI (T-032, ADR-0005)."""

from __future__ import annotations

import json
from typing import AsyncGenerator
from uuid import UUID

import httpx

from cipher.core.schemas.task_contract import TaskContract, TaskResult


class CipherShellClient:
    """
    Client used by GUI panels to communicate with the A2A backend.

    Submits TaskContracts and streams SSE updates.
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base_url = base_url

    async def submit_task(self, task: TaskContract) -> UUID:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/tasks",
                content=task.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return UUID(resp.json()["task_id"])

    async def get_task_status(self, task_id: UUID) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base_url}/v1/tasks/{task_id}")
            resp.raise_for_status()
            return resp.json()

    async def stream_task(self, task_id: UUID) -> AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream(
                "GET", f"{self._base_url}/v1/tasks/{task_id}/stream"
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        yield data
                        if data.get("status") in ("COMPLETED", "FAILED"):
                            break
