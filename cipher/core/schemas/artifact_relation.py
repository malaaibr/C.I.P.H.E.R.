"""ArtifactRelation — links between versioned artifacts in the knowledge graph."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RelationType(StrEnum):
    DERIVES_FROM = "DERIVES_FROM"
    REFINES = "REFINES"
    IMPLEMENTS = "IMPLEMENTS"
    TESTS = "TESTS"
    SUPERSEDES = "SUPERSEDES"
    REFERENCES = "REFERENCES"
    GENERATED_BY = "GENERATED_BY"
    APPROVED_BY = "APPROVED_BY"
    VIOLATES = "VIOLATES"
    CONFORMS_TO = "CONFORMS_TO"


class ArtifactRelation(BaseModel):
    """Directed edge between two artifacts (source → target)."""

    relation_id: UUID = Field(default_factory=uuid4)
    source_artifact_id: str
    target_artifact_id: str
    relation_type: RelationType
    v_cycle_stage: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by_agent: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    valid_from: datetime | None = Field(
        default=None, description="Temporal edge start (None = since creation)"
    )
    valid_to: datetime | None = Field(
        default=None, description="Temporal edge end (None = still valid)"
    )
    metadata: dict[str, str] = Field(default_factory=dict)
