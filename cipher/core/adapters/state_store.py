"""StateStore — Redis-backed state persistence (T-014, replaces JSON StateStore)."""

from __future__ import annotations

import json
from typing import Any

from cipher.core.adapters.redis_client import RedisClient


class StateStore:
    """
    Key-value state store backed by Redis.

    Preserves the load()/save() API from DevNex's JSON-based StateStore
    but uses Redis as the backend per ADR-0003 §1.3.
    """

    def __init__(self, client: RedisClient, namespace: str = "cipher:state") -> None:
        self._client = client
        self._ns = namespace

    def _key(self, key: str) -> str:
        return f"{self._ns}:{key}"

    async def save(self, key: str, data: dict[str, Any]) -> None:
        await self._client.set(self._key(key), json.dumps(data))

    async def load(self, key: str) -> dict[str, Any] | None:
        raw = await self._client.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def delete(self, key: str) -> None:
        await self._client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return await self._client.exists(self._key(key))
