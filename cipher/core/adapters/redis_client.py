"""Redis 7 async client for CIPHER working memory (T-005)."""

from __future__ import annotations

import os
from typing import Any

import redis.asyncio as aioredis


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class RedisClient:
    """Thin async wrapper around redis-py for working memory operations."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or get_redis_url()
        self._pool: aioredis.Redis | None = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        self._pool = aioredis.from_url(
            self._url, decode_responses=True
        )

    async def close(self) -> None:
        if self._pool:
            await self._pool.aclose()
            self._pool = None

    @property
    def pool(self) -> aioredis.Redis:  # type: ignore[type-arg]
        if self._pool is None:
            raise RuntimeError("RedisClient not connected. Call connect() first.")
        return self._pool

    async def ping(self) -> bool:
        return await self.pool.ping()  # type: ignore[return-value]

    async def get(self, key: str) -> str | None:
        return await self.pool.get(key)  # type: ignore[return-value]

    async def set(
        self, key: str, value: str, expire_s: int | None = None
    ) -> None:
        if expire_s:
            await self.pool.setex(key, expire_s, value)
        else:
            await self.pool.set(key, value)

    async def delete(self, key: str) -> None:
        await self.pool.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.pool.exists(key))

    async def expire(self, key: str, seconds: int) -> None:
        await self.pool.expire(key, seconds)

    async def keys(self, pattern: str = "*") -> list[str]:
        return await self.pool.keys(pattern)  # type: ignore[return-value]
