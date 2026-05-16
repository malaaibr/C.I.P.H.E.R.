"""DevNex Pydantic schema migration (T-029) — CAR-002 dataclasses → Pydantic v2."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VCycleStage(StrEnum):
    """V-Cycle stages (13 canonical per CIPHER spec)."""

    S1N1 = "S1N1"  # HLD → LLD
    S2N1 = "S2N1"  # LLD → Unit Design
    S3N1 = "S3N1"  # Unit Design → Implementation
    S4N1 = "S4N1"  # Implementation → Unit Test
    S5N1 = "S5N1"  # Unit Test → Integration Test
    S6N1 = "S6N1"  # Integration Test → System Test
    S7N1 = "S7N1"  # System Test → Acceptance Test
    S8N1 = "S8N1"  # Requirement Tracing
    S9N1 = "S9N1"  # Safety Analysis


class NodeStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NodeResult(BaseModel):
    """Result from a single workflow node execution."""

    node_id: str
    stage: VCycleStage
    status: NodeStatus
    output: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)
    duration_ms: float | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillManifest(BaseModel):
    """SKILL.md parsed representation (Stage 1 descriptor)."""

    skill_id: str
    name: str
    description: str
    version: str = "0.1.0"
    v_cycle_stages: list[VCycleStage] = Field(default_factory=list)
    required_backends: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """Workflow definition replacing AF.json format."""

    workflow_id: str
    name: str
    description: str
    nodes: list[str] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)
    entry_point: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeRequest(BaseModel):
    """Request to the GCA HTTP bridge (from CAR-002 DevNex)."""

    prompt: str
    workspace_hint: str = ""
    timeout_s: float = 300.0
    request_id: UUID = Field(default_factory=uuid4)


class BridgeResponse(BaseModel):
    """Response from the GCA HTTP bridge."""

    text: str
    instance_id: str | None = None
    duration_ms: float
    request_id: UUID
