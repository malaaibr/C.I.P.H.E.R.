"""NATS JetStream event bus wrapper (T-003)."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Coroutine

import nats
from nats.aio.client import Client as NatsClient
from nats.js import JetStreamContext

from cipher.core.schemas.cloud_event import CloudEvent

MessageHandler = Callable[[CloudEvent], Coroutine[Any, Any, None]]


def get_nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


class NatsBus:
    """
    Async NATS JetStream wrapper for CIPHER event routing.

    Provides publish/subscribe on CloudEvent-typed messages with
    JetStream durable consumers for reliable delivery.
    """

    STREAM_NAME = "CIPHER"
    SUBJECTS = "cipher.>"

    def __init__(self, url: str | None = None) -> None:
        self._url = url or get_nats_url()
        self._nc: NatsClient | None = None
        self._js: JetStreamContext | None = None

    @property
    def is_connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    async def connect(self) -> None:
        self._nc = await nats.connect(self._url)
        self._js = self._nc.jetstream()
        await self._ensure_stream()

    async def close(self) -> None:
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def _ensure_stream(self) -> None:
        assert self._js is not None
        try:
            await self._js.find_stream_info_by_subject(self.SUBJECTS)
        except Exception:
            await self._js.add_stream(
                name=self.STREAM_NAME, subjects=[self.SUBJECTS]
            )

    @property
    def js(self) -> JetStreamContext:
        if self._js is None:
            raise RuntimeError("NatsBus not connected. Call connect() first.")
        return self._js

    async def publish(self, subject: str, event: CloudEvent) -> None:
        payload = event.model_dump_json().encode()
        await self.js.publish(subject, payload)

    async def subscribe(
        self,
        subject: str,
        handler: MessageHandler,
        durable: str | None = None,
    ) -> None:
        async def _cb(msg: Any) -> None:
            data = json.loads(msg.data.decode())
            event = CloudEvent.model_validate(data)
            await handler(event)
            await msg.ack()

        sub = await self.js.subscribe(subject, durable=durable, cb=_cb)
