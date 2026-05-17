"""Cited Reasoning Chain (CRC) — cipher.cap.crc.v1 schema.

A CRC is the typed object exchanged between the Enhanced Prompting layer
(which produces it) and the Corrective RAG / Validator layer (which checks it).
Each step carries a thought, a non-empty citation set, and a typed claim.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceType(StrEnum):
    REQUIREMENT = "REQUIREMENT"
    ARCHITECTURE = "ARCHITECTURE"
    STANDARD_RULE = "STANDARD_RULE"
    PRIOR_DESIGN = "PRIOR_DESIGN"
    TEST_VECTOR = "TEST_VECTOR"


class ClaimKind(StrEnum):
    STATE_SET = "state_set"
    TRANSITION = "transition"
    TIMING_PARAM = "timing_param"
    INTERFACE_FIELD = "interface_field"
    FUNCTION_SIGNATURE = "function_signature"
    ERROR_HANDLER = "error_handler"
    ASIL_DECLARATION = "asil_declaration"
    RESOURCE_CONSUMPTION = "resource_consumption"
    CRITICAL_SECTION = "critical_section"
    MACRO_DEFINITION = "macro_definition"
    TYPE_DEFINITION = "type_definition"
    MISRA_DEVIATION = "misra_deviation"
    REVIEW_NEEDED = "review_needed"


class Citation(BaseModel):
    """Evidence pointer — must resolve to a real artifact in the MKF."""

    artifact_uri: str = Field(
        ..., description="URI resolvable in MKF, e.g. mkf://SWc_HLD.csv#row-3"
    )
    span: str = Field(
        default="", description="Localiser within the artifact, e.g. L82-L91"
    )
    evidence_type: EvidenceType


class Claim(BaseModel):
    """Typed design content produced by a reasoning step."""

    kind: ClaimKind
    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Kind-dependent structured fields (e.g. states, value, name)",
    )


class CRCStep(BaseModel):
    """One step in the Cited Reasoning Chain: (thought, citations, claim)."""

    i: int = Field(..., ge=1, description="Step index (1-based)")
    thought: str = Field(..., min_length=1, description="Natural-language reasoning")
    citations: list[Citation] = Field(
        ..., min_length=1, description="Non-empty citation set"
    )
    claim: Claim


class CRCChain(BaseModel):
    """Complete Cited Reasoning Chain for one agent task."""

    schema_id: str = Field(default="cipher.cap.crc.v1", frozen=True)
    target_artifact: str = Field(
        ..., description="ID of the artifact being produced, e.g. LLD-Dio:v1"
    )
    target_asil: str = Field(default="QM", description="Target ASIL level")
    phase: str = Field(
        default="SWE.3", description="Current ASPICE phase, e.g. SWE.3"
    )
    generated_by: str = Field(default="", description="Agent ID that produced this CRC")
    model: str = Field(default="", description="LLM model used for generation")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int | None = Field(default=None, description="Fixed seed for reproducibility")
    steps: list[CRCStep] = Field(
        ..., min_length=1, description="Ordered sequence of reasoning steps"
    )

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def all_citations(self) -> list[Citation]:
        """Flat list of every citation across all steps."""
        return [c for step in self.steps for c in step.citations]
