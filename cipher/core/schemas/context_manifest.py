"""ContextManifest — bounded evidence set provided to the LLM.

The manifest defines the closed set of artifacts the model is allowed to cite.
The CAP Validator checks citation URIs against this manifest (WF₂).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    HLD = "HLD"
    SOURCE_CODE = "SOURCE_CODE"
    HEADER = "HEADER"
    LINKER_MAP = "LINKER_MAP"
    LINKER_SCRIPT = "LINKER_SCRIPT"
    LLD_TEMPLATE = "LLD_TEMPLATE"
    SWDD_TEMPLATE = "SWDD_TEMPLATE"
    REQUIREMENT = "REQUIREMENT"
    TEST_CASE = "TEST_CASE"
    STANDARD_RULE = "STANDARD_RULE"
    DESIGN_DOCUMENT = "DESIGN_DOCUMENT"


class EvidenceItem(BaseModel):
    """One item in the evidence set provided to the LLM."""

    uri: str = Field(
        ..., description="MKF URI, e.g. mkf://Dio_HLD.md or mkf://Dio.c"
    )
    content_hash: str = Field(
        default="", description="SHA-256 hash of the content at injection time"
    )
    artifact_type: ArtifactType
    asil_level: str = Field(default="QM", description="ASIL level of this artifact")
    line_count: int = Field(default=0, ge=0)


class ContextManifest(BaseModel):
    """Closed set of evidence items provided to the model for one task."""

    task_id: str = Field(default="", description="TaskContract ID this manifest serves")
    evidence_items: list[EvidenceItem] = Field(
        default_factory=list, description="All artifacts available for citation"
    )
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_token_budget: int = Field(
        default=0, ge=0, description="Token budget allocated for context"
    )

    def uri_set(self) -> set[str]:
        """Set of all URIs in this manifest for fast lookup."""
        return {item.uri for item in self.evidence_items}

    def resolve(self, uri: str) -> EvidenceItem | None:
        """Resolve a URI to its EvidenceItem, or None if not in manifest."""
        for item in self.evidence_items:
            if item.uri == uri:
                return item
        return None
