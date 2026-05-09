"""Minimal lifecycle primitives for the local MVP scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cipher.core.contracts import Budget


class AgentState(str, Enum):
    SPAWNED = "spawned"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass(slots=True)
class AgentDescriptor:
    agent_id: str
    agent_name: str
    trust_tier: str
    budget: Budget
    scopes: list[str]
    state: AgentState = AgentState.SPAWNED
    checkpoint_uri: str | None = None

