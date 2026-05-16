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


class ArtifactRelation(BaseModel):
    """Directed edge between two artifacts (source → target)."""

    relation_id: UUID = Field(default_factory=uuid4)
    source_artifact_id: str
    target_artifact_id: str
    relation_type: RelationType
    v_cycle_stage: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by_agent: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
