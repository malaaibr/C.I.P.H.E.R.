"""Data models for the DevNex Technical Review pipeline.

Hierarchy
---------
FindingSeverity   — CRITICAL / MAJOR / MINOR / INFO
ReviewVerdict     — APPROVED / CONDITIONAL / REJECTED / INCOMPLETE
ReviewFinding     — one structured reviewer comment with location reference
StageResult       — outcome of a single review node (R1N1 … R9N1)
ReviewReport      — full pipeline output: all stages + aggregated verdict
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class FindingSeverity(str, Enum):
    """ISO 26262 / ASPICE aligned finding severity levels."""
    CRITICAL    = "CRITICAL"   # Blocks approval — safety gap, KW error, test failure
    MAJOR       = "MAJOR"      # Must fix before release — quality / coverage deficit
    MINOR       = "MINOR"      # Observation / improvement opportunity
    INFO        = "INFO"       # Metric, statistics, note


class ReviewVerdict(str, Enum):
    APPROVED    = "APPROVED"    # 0 critical, 0 major findings
    CONDITIONAL = "CONDITIONAL" # 0 critical, ≥1 major (waiver required)
    REJECTED    = "REJECTED"    # ≥1 critical finding
    INCOMPLETE  = "INCOMPLETE"  # Pipeline did not finish


class ReviewNodeStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    PASSED   = "passed"
    FAILED   = "failed"
    SKIPPED  = "skipped"


# ── Finding ───────────────────────────────────────────────────────────────────

@dataclass
class ReviewFinding:
    """Single reviewer observation linked to a specific artifact location."""
    stage_id:     str                       # e.g. "R6N1"
    severity:     FindingSeverity
    category:     str                       # e.g. "TRACEABILITY", "KW_ERROR", "COVERAGE"
    description:  str                       # Reviewer prose
    artifact_ref: str          = ""         # Artifact file name/section
    item_ref:     str          = ""         # Requirement ID, test case ID, KW ID, etc.
    line_ref:     int          = 0          # Line number when applicable
    standard_ref: str          = ""         # ISO 26262 clause / ASPICE PA reference

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id":     self.stage_id,
            "severity":     self.severity.value,
            "category":     self.category,
            "description":  self.description,
            "artifact_ref": self.artifact_ref,
            "item_ref":     self.item_ref,
            "line_ref":     self.line_ref,
            "standard_ref": self.standard_ref,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReviewFinding":
        return cls(
            stage_id     = d.get("stage_id", ""),
            severity     = FindingSeverity(d.get("severity", "INFO")),
            category     = d.get("category", ""),
            description  = d.get("description", ""),
            artifact_ref = d.get("artifact_ref", ""),
            item_ref     = d.get("item_ref", ""),
            line_ref     = int(d.get("line_ref", 0)),
            standard_ref = d.get("standard_ref", ""),
        )


# ── Stage result ──────────────────────────────────────────────────────────────

@dataclass
class StageResult:
    """Output of a single review node in the pipeline."""
    node_id:      str
    label:        str
    status:       ReviewNodeStatus
    findings:     list[ReviewFinding]        = field(default_factory=list)
    metrics:      dict[str, Any]             = field(default_factory=dict)
    raw_response: str                        = ""
    errors:       list[str]                  = field(default_factory=list)

    # Convenience counters
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)

    @property
    def major_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.MAJOR)

    @property
    def minor_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.MINOR)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":      self.node_id,
            "label":        self.label,
            "status":       self.status.value,
            "findings":     [f.to_dict() for f in self.findings],
            "metrics":      self.metrics,
            "errors":       self.errors,
            "critical":     self.critical_count,
            "major":        self.major_count,
            "minor":        self.minor_count,
        }


# ── Review report ─────────────────────────────────────────────────────────────

@dataclass
class ReviewReport:
    """Full pipeline output — serialisable to JSON and renderable as Markdown."""
    swc_name:      str
    reviewer:      str
    timestamp:     str                        = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    verdict:       ReviewVerdict              = ReviewVerdict.INCOMPLETE
    stage_results: list[StageResult]         = field(default_factory=list)
    summary:       str                        = ""
    artifacts_dir: str                        = ""

    # Aggregate convenience helpers
    @property
    def all_findings(self) -> list[ReviewFinding]:
        out: list[ReviewFinding] = []
        for sr in self.stage_results:
            out.extend(sr.findings)
        return out

    @property
    def critical_count(self) -> int:
        return sum(s.critical_count for s in self.stage_results)

    @property
    def major_count(self) -> int:
        return sum(s.major_count for s in self.stage_results)

    @property
    def minor_count(self) -> int:
        return sum(s.minor_count for s in self.stage_results)

    @property
    def total_findings(self) -> int:
        return sum(len(s.findings) for s in self.stage_results)

    def compute_verdict(self) -> ReviewVerdict:
        """Derive verdict from finding counts — call after all stages finish."""
        failed = [s for s in self.stage_results if s.status == ReviewNodeStatus.FAILED]
        if any(s.critical_count > 0 for s in failed + self.stage_results):
            return ReviewVerdict.REJECTED
        if any(s.major_count > 0 for s in self.stage_results):
            return ReviewVerdict.CONDITIONAL
        pending = [s for s in self.stage_results
                   if s.status in (ReviewNodeStatus.PENDING, ReviewNodeStatus.RUNNING)]
        if pending:
            return ReviewVerdict.INCOMPLETE
        return ReviewVerdict.APPROVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "swc_name":     self.swc_name,
            "reviewer":     self.reviewer,
            "timestamp":    self.timestamp,
            "verdict":      self.verdict.value,
            "summary":      self.summary,
            "artifacts_dir":self.artifacts_dir,
            "totals": {
                "critical": self.critical_count,
                "major":    self.major_count,
                "minor":    self.minor_count,
                "total":    self.total_findings,
            },
            "stages": [s.to_dict() for s in self.stage_results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
