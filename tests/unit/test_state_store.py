"""Unit tests for StateStore (T-014)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cipher.core.adapters.state_store import StateStore


@pytest.fixture
def mock_redis() -> AsyncMock:
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.delete = AsyncMock()
    client.exists = AsyncMock(return_value=False)
    return client


class TestStateStore:
    @pytest.mark.asyncio
    async def test_save_and_load(self, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(return_value='{"step": 3}')
        store = StateStore(mock_redis, namespace="test")

        await store.save("workflow-1", {"step": 3})
        mock_redis.set.assert_called_once_with("test:workflow-1", '{"step": 3}')

        data = await store.load("workflow-1")
        assert data == {"step": 3}

    @pytest.mark.asyncio
    async def test_load_missing_key(self, mock_redis: AsyncMock) -> None:
        store = StateStore(mock_redis)
        result = await store.load("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, mock_redis: AsyncMock) -> None:
        store = StateStore(mock_redis)
        await store.delete("key")
        mock_redis.delete.assert_called_once_with("cipher:state:key")

    @pytest.mark.asyncio
    async def test_exists(self, mock_redis: AsyncMock) -> None:
        mock_redis.exists = AsyncMock(return_value=True)
        store = StateStore(mock_redis)
        assert await store.exists("key") is True
