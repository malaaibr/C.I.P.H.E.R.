"""IssueReport — typed validator feedback for the Draft-Verify-Finalize loop.

When the CAP Validator detects a well-formedness violation, it returns a
structured IssueReport naming the exact step and the exact condition that
failed, so the model receives a precise diagnostic rather than a vague retry.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ViolationType(StrEnum):
    UNCITED = "WF1_UNCITED"
    UNRESOLVED = "WF2_UNRESOLVED"
    TYPE_MISMATCH = "WF3_TYPE_MISMATCH"
    ASIL_DOWNCAST = "WF4_ASIL_DOWNCAST"
    PHASE_VIOLATION = "WF5_PHASE_VIOLATION"
    FIELD_MISMATCH = "WF6_FIELD_MISMATCH"


class WellFormednessViolation(BaseModel):
    """A single well-formedness check failure on one CRC step."""

    step_index: int = Field(..., ge=1, description="Index of the failing CRC step")
    violation_type: ViolationType
    message: str = Field(
        ..., description="Human-readable explanation of the violation"
    )
    expected: str = Field(default="", description="What was expected")
    actual: str = Field(default="", description="What was found")
    citation_uri: str | None = Field(
        default=None, description="URI of the offending citation, if applicable"
    )


class ValidationVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class IssueReport(BaseModel):
    """Aggregated validation result for a complete CRC chain."""

    report_id: UUID = Field(default_factory=uuid4)
    crc_target_artifact: str = Field(
        ..., description="Target artifact from the CRC being validated"
    )
    verdict: ValidationVerdict
    violations: list[WellFormednessViolation] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    validator_version: str = Field(default="1.0.0")
    revision_number: int = Field(
        default=0, ge=0, description="Which revision attempt this report is for"
    )

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def is_pass(self) -> bool:
        return self.verdict == ValidationVerdict.PASS
