"""OPA Client — policy evaluation against OPA sidecar (T-027)."""

from __future__ import annotations

import os

import httpx


class OpaClient:
    """Evaluates authorization policies against the OPA REST API."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.environ.get("OPA_URL", "http://localhost:8181")

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._url}/health")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def evaluate(
        self, policy_path: str = "cipher/authz", input_data: dict | None = None
    ) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{self._url}/v1/data/{policy_path}",
                json={"input": input_data or {}},
            )
            if resp.status_code != 200:
                return False
            result = resp.json()
            return result.get("result", {}).get("allow", False)
