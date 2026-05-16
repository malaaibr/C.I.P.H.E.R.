"""SSE Client — Server-Sent Events consumer for real-time updates (T-032)."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx


class SSEClient:
    """Generic SSE client for consuming event streams."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def subscribe(self, path: str) -> AsyncGenerator[dict[str, Any], None]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", f"{self._base_url}{path}") as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
