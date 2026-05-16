"""CloudEvent — NATS event envelope following CloudEvents spec v1.0."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CloudEvent(BaseModel):
    """
    CloudEvents v1.0 envelope for NATS JetStream messages.

    Spec: https://cloudevents.io/
    """

    id: UUID = Field(default_factory=uuid4)
    source: str
    type: str
    specversion: str = "1.0"
    time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    subject: str | None = None
    datacontenttype: str = "application/json"
    data: dict[str, Any] = Field(default_factory=dict)
