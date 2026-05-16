"""Qdrant client wrapper (T-007)."""

from __future__ import annotations

import os

import httpx


def get_qdrant_url() -> str:
    return os.environ.get("QDRANT_URL", "http://localhost:6333")


class QdrantHealthClient:
    """Lightweight health-check client for Qdrant."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or get_qdrant_url()

    async def health_check(self) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._url}/healthz")
            return resp.status_code == 200
