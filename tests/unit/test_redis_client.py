"""Unit tests for RedisClient (T-005)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cipher.core.adapters.redis_client import RedisClient, get_redis_url


class TestGetRedisUrl:
    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert get_redis_url() == "redis://localhost:6379/0"

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_URL", "redis://custom:6380/2")
        assert get_redis_url() == "redis://custom:6380/2"


class TestRedisClient:
    @pytest.fixture
    def client(self) -> RedisClient:
        return RedisClient("redis://localhost:6379/0")

    def test_not_connected_raises(self, client: RedisClient) -> None:
        with pytest.raises(RuntimeError, match="not connected"):
            _ = client.pool

    @pytest.mark.asyncio
    async def test_ping(self, client: RedisClient) -> None:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        client._pool = mock_redis
        assert await client.ping() is True

    @pytest.mark.asyncio
    async def test_get_set(self, client: RedisClient) -> None:
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value="bar")
        client._pool = mock_redis

        await client.set("foo", "bar")
        mock_redis.set.assert_called_once_with("foo", "bar")

        result = await client.get("foo")
        assert result == "bar"

    @pytest.mark.asyncio
    async def test_set_with_expire(self, client: RedisClient) -> None:
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        client._pool = mock_redis

        await client.set("key", "val", expire_s=60)
        mock_redis.setex.assert_called_once_with("key", 60, "val")

    @pytest.mark.asyncio
    async def test_delete(self, client: RedisClient) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()
        client._pool = mock_redis

        await client.delete("key")
        mock_redis.delete.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_exists(self, client: RedisClient) -> None:
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        client._pool = mock_redis

        assert await client.exists("key") is True
