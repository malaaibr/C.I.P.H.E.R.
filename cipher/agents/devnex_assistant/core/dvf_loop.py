"""Draft-Verify-Finalize (DVF) loop for Citation-Aware Prompting.

Wraps the S1N1 LLD generation in a 3-state machine:
  DRAFT  → generate CRC via citation-aware prompt
  VERIFY → run CAP Validator (WF₁–WF₆)
  REVISE → re-prompt with typed IssueReport (max R_max iterations)
  FINALIZE → render CSV from validated CRC, persist ArtifactRelation edges

On R_max exceeded → escalate to HITL gate.
"""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from cipher.core.schemas.context_manifest import (
    ArtifactType,
    ContextManifest,
    EvidenceItem,
)
from cipher.core.schemas.crc import CRCChain, CRCStep
from cipher.core.schemas.issue_report import IssueReport, ValidationVerdict

logger = logging.getLogger(__name__)

ARTIFACT_TYPE_MAP = {
    "SWC_name_C": ArtifactType.SOURCE_CODE,
    "SWC_name_H": ArtifactType.HEADER,
    "G_SWDD_TEMP": ArtifactType.SWDD_TEMPLATE,
    "SWC_name_TEMP_LLD": ArtifactType.LLD_TEMPLATE,
    "SWC_name_HLD": ArtifactType.HLD,
    "lds_file": ArtifactType.LINKER_SCRIPT,
    "map_file": ArtifactType.LINKER_MAP,
}


class DVFState(StrEnum):
    DRAFT = "DRAFT"
    VERIFY = "VERIFY"
    REVISE = "REVISE"
    FINALIZE = "FINALIZE"
    HITL_ESCALATION = "HITL_ESCALATION"


def build_context_manifest(
    config: dict[str, str],
    resolved_paths: dict[str, Path],
    task_id: str = "",
) -> ContextManifest:
    """Build a ContextManifest from the resolved input file paths."""
    items = []
    for key, path in resolved_paths.items():
        if path.exists():
            items.append(
                EvidenceItem(
                    uri=f"mkf://{path.name}",
                    artifact_type=ARTIFACT_TYPE_MAP.get(key, ArtifactType.DESIGN_DOCUMENT),
                    asil_level=config.get("target_asil", "QM"),
                    line_count=sum(1 for _ in path.open(encoding="utf-8", errors="replace")),
                )
            )
    return ContextManifest(task_id=task_id, evidence_items=items)


def parse_crc_from_response(raw: str) -> CRCChain:
    """Parse a CRC JSON from the LLM response text.

    Handles cases where the LLM wraps JSON in markdown code fences.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines) - 1
        if lines[0].startswith("```json"):
            start = 1
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end])
    return CRCChain.model_validate_json(text)


def render_csv_from_crc(crc: CRCChain, swc_name: str) -> str:
    """Render a validated CRC into the standard LLD CSV format.

    The CSV is a deterministic view of the validated CRC — no longer
    LLM-generated. This is the operational shift described in CAP §VI.E.
    """
    header = "REQ_ID,FUNCTION_OR_ELEMENT,TYPE,DESCRIPTION,HLD_PARENT,MISRA_DEVIATION,SAFETY_LEVEL"
    rows = [header]

    for step in crc.steps:
        req_id = f"{swc_name}_LLD_REQ_{step.i:03d}"
        claim = step.claim
        kind = claim.kind.value.upper()
        fields = claim.fields

        element = fields.get("name", fields.get("variable", fields.get("function", "")))
        description = step.thought
        hld_parent = ""
        misra_dev = "None"
        safety = crc.target_asil

        for c in step.citations:
            if c.evidence_type.value == "REQUIREMENT":
                uri = c.artifact_uri
                if "#" in uri:
                    hld_parent = uri.split("#")[1]
                break

        if claim.kind.value == "misra_deviation":
            misra_dev = fields.get("rule", "Unknown") + " — " + fields.get("description", "")

        if claim.kind.value == "asil_declaration":
            safety = fields.get("asil", safety)

        desc_escaped = description.replace('"', '""')
        if "," in desc_escaped:
            desc_escaped = f'"{desc_escaped}"'

        rows.append(f"{req_id},{element},{kind},{desc_escaped},{hld_parent},{misra_dev},{safety}")

    return "\n".join(rows) + "\n"


def build_revise_prompt(
    original_prompt: str,
    issue_report: IssueReport,
    revision: int,
) -> str:
    """Append a typed IssueReport to the original prompt for a REVISE iteration."""
    violations_text = "\n".join(
        f"  - Step {v.step_index}: {v.violation_type.value} — {v.message} "
        f"(expected: {v.expected}, actual: {v.actual})"
        for v in issue_report.violations
    )
    return (
        f"{original_prompt}\n\n"
        f"## REVISION {revision} — VALIDATOR FEEDBACK\n\n"
        f"The previous CRC failed validation with {issue_report.violation_count} violation(s):\n"
        f"{violations_text}\n\n"
        f"Fix ONLY the failing steps. Keep all passing steps unchanged. "
        f"Output the complete corrected CRC JSON."
    )


class DVFLoop:
    """Draft-Verify-Finalize execution loop."""

    def __init__(
        self,
        invoke_fn: Callable[[str, list[str], str], Any],
        manifest: ContextManifest,
        max_revisions: int = 3,
        domain_pack: str = "iso26262_asil_b",
    ) -> None:
        self._invoke = invoke_fn
        self._manifest = manifest
        self._max_revisions = max_revisions
        self._domain_pack = domain_pack
        self.state = DVFState.DRAFT
        self.revision_count = 0
        self.final_crc: CRCChain | None = None
        self.reports: list[IssueReport] = []

    def run(
        self,
        prompt: str,
        attached_files: list[str],
        node_id: str = "S1N1",
    ) -> tuple[CRCChain, list[IssueReport]]:
        """Execute the full DVF loop. Returns (validated_crc, issue_reports)."""
        from cipher.gcl.cap_validator import CAPValidator

        validator = CAPValidator(
            manifest=self._manifest,
            domain_pack=self._domain_pack,
        )

        current_prompt = prompt
        self.state = DVFState.DRAFT

        while True:
            logger.info("DVF: state=%s, revision=%d", self.state, self.revision_count)

            result = self._invoke(current_prompt, attached_files, node_id)
            crc = parse_crc_from_response(result.raw_response)

            self.state = DVFState.VERIFY
            report = validator.validate(crc, revision=self.revision_count)
            self.reports.append(report)

            if report.is_pass:
                self.state = DVFState.FINALIZE
                self.final_crc = crc
                logger.info(
                    "DVF: FINALIZE — CRC validated after %d revision(s)",
                    self.revision_count,
                )
                return crc, self.reports

            self.revision_count += 1
            if self.revision_count > self._max_revisions:
                self.state = DVFState.HITL_ESCALATION
                logger.warning(
                    "DVF: HITL_ESCALATION — %d revisions exceeded R_max=%d",
                    self.revision_count,
                    self._max_revisions,
                )
                self.final_crc = crc
                return crc, self.reports

            self.state = DVFState.REVISE
            current_prompt = build_revise_prompt(
                prompt, report, self.revision_count
            )
