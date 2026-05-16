"""Unit tests for NatsBus (T-003)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cipher.core.schemas.cloud_event import CloudEvent
from cipher.pkl.event_bus.nats_bus import NatsBus, get_nats_url


class TestGetNatsUrl:
    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NATS_URL", raising=False)
        assert get_nats_url() == "nats://localhost:4222"

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NATS_URL", "nats://custom:4222")
        assert get_nats_url() == "nats://custom:4222"


class TestNatsBus:
    def test_not_connected_raises(self) -> None:
        bus = NatsBus()
        with pytest.raises(RuntimeError, match="not connected"):
            _ = bus.js

    def test_is_connected_false_initially(self) -> None:
        bus = NatsBus()
        assert bus.is_connected is False

    @pytest.mark.asyncio
    async def test_publish(self) -> None:
        bus = NatsBus()
        mock_js = AsyncMock()
        mock_js.publish = AsyncMock()
        bus._js = mock_js
        bus._nc = MagicMock()
        bus._nc.is_connected = True

        event = CloudEvent(
            source="test.agent",
            type="cipher.task.created",
            data={"task_id": "123"},
        )
        await bus.publish("cipher.tasks.created", event)

        mock_js.publish.assert_called_once()
        call_args = mock_js.publish.call_args
        assert call_args[0][0] == "cipher.tasks.created"
        payload = json.loads(call_args[0][1].decode())
        assert payload["type"] == "cipher.task.created"
        assert payload["data"]["task_id"] == "123"

    @pytest.mark.asyncio
    async def test_subscribe_registers_callback(self) -> None:
        bus = NatsBus()
        mock_js = AsyncMock()
        mock_js.subscribe = AsyncMock()
        bus._js = mock_js

        handler = AsyncMock()
        await bus.subscribe("cipher.tasks.>", handler, durable="test-consumer")

        mock_js.subscribe.assert_called_once()
        call_kwargs = mock_js.subscribe.call_args
        assert call_kwargs[0][0] == "cipher.tasks.>"
        assert call_kwargs[1]["durable"] == "test-consumer"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        bus = NatsBus()
        mock_nc = AsyncMock()
        bus._nc = mock_nc
        bus._js = AsyncMock()

        await bus.close()
        mock_nc.close.assert_called_once()
        assert bus._nc is None
        assert bus._js is None
