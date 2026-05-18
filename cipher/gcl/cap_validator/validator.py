"""CAP Validator — implements WF₁–WF₆ well-formedness predicates.

Runs on every CRC chain before FINALIZE. Each check is O(1) per citation,
total cost O(Σ|Cᵢ|) — well below LLM inference cost.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cipher.core.schemas.context_manifest import ContextManifest
from cipher.core.schemas.crc import CRCChain, CRCStep, ClaimKind, EvidenceType
from cipher.core.schemas.issue_report import (
    IssueReport,
    ValidationVerdict,
    ViolationType,
    WellFormednessViolation,
)

logger = logging.getLogger(__name__)

ASIL_ORDER = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}

_DOMAIN_PACK_DIR = Path(__file__).resolve().parent.parent / "domain_packs"


def _load_json(pack: str, filename: str) -> dict[str, Any]:
    path = _DOMAIN_PACK_DIR / pack / "schemas" / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


class CAPValidator:
    """Stateless validator that checks a CRC chain against 6 well-formedness predicates."""

    def __init__(
        self,
        manifest: ContextManifest | None = None,
        domain_pack: str = "iso26262_asil_b",
    ) -> None:
        self._manifest = manifest
        self._uri_set = manifest.uri_set() if manifest else set()
        self._permitted_types: dict[str, list[str]] = _load_json(
            domain_pack, "permitted_types.json"
        )
        self._phase_kinds: dict[str, list[str]] = _load_json(
            domain_pack, "phase_kinds.json"
        )

    def validate(self, crc: CRCChain, revision: int = 0) -> IssueReport:
        violations: list[WellFormednessViolation] = []

        for step in crc.steps:
            violations.extend(self._check_wf1(step))
            violations.extend(self._check_wf2(step))
            violations.extend(self._check_wf3(step))
            violations.extend(self._check_wf4(step, crc.target_asil))
            violations.extend(self._check_wf5(step, crc.phase))
            violations.extend(self._check_wf6(step))

        verdict = ValidationVerdict.PASS if not violations else ValidationVerdict.FAIL

        return IssueReport(
            crc_target_artifact=crc.target_artifact,
            verdict=verdict,
            violations=violations,
            revision_number=revision,
        )

    def _check_wf1(self, step: CRCStep) -> list[WellFormednessViolation]:
        """WF₁: Every step must have at least one citation."""
        if not step.citations:
            return [
                WellFormednessViolation(
                    step_index=step.i,
                    violation_type=ViolationType.UNCITED,
                    message=f"Step {step.i} has no citations",
                    expected="≥1 citation",
                    actual="0 citations",
                )
            ]
        return []

    def _check_wf2(self, step: CRCStep) -> list[WellFormednessViolation]:
        """WF₂: Every citation URI must resolve in the manifest."""
        if not self._manifest:
            return []
        violations = []
        for c in step.citations:
            base_uri = c.artifact_uri.split("#")[0]
            if base_uri not in self._uri_set:
                violations.append(
                    WellFormednessViolation(
                        step_index=step.i,
                        violation_type=ViolationType.UNRESOLVED,
                        message=f"Citation URI '{c.artifact_uri}' does not resolve",
                        expected="URI in manifest",
                        actual=c.artifact_uri,
                        citation_uri=c.artifact_uri,
                    )
                )
        return violations

    def _check_wf3(self, step: CRCStep) -> list[WellFormednessViolation]:
        """WF₃: Evidence type must be permitted for the claim kind."""
        if not self._permitted_types:
            return []
        allowed = self._permitted_types.get(step.claim.kind.value, [])
        if not allowed:
            return []
        violations = []
        for c in step.citations:
            if c.evidence_type.value not in allowed:
                violations.append(
                    WellFormednessViolation(
                        step_index=step.i,
                        violation_type=ViolationType.TYPE_MISMATCH,
                        message=(
                            f"Evidence type '{c.evidence_type}' not permitted "
                            f"for claim kind '{step.claim.kind}'"
                        ),
                        expected=str(allowed),
                        actual=c.evidence_type.value,
                        citation_uri=c.artifact_uri,
                    )
                )
        return violations

    def _check_wf4(
        self, step: CRCStep, target_asil: str
    ) -> list[WellFormednessViolation]:
        """WF₄: Cited artifact ASIL must be ≥ claim target ASIL."""
        if not self._manifest:
            return []
        target_rank = ASIL_ORDER.get(target_asil, 0)
        if target_rank == 0:
            return []
        violations = []
        for c in step.citations:
            base_uri = c.artifact_uri.split("#")[0]
            item = self._manifest.resolve(base_uri)
            if item:
                item_rank = ASIL_ORDER.get(item.asil_level, 0)
                if item_rank < target_rank:
                    violations.append(
                        WellFormednessViolation(
                            step_index=step.i,
                            violation_type=ViolationType.ASIL_DOWNCAST,
                            message=(
                                f"Cited artifact ASIL '{item.asil_level}' < "
                                f"target ASIL '{target_asil}'"
                            ),
                            expected=f"≥ {target_asil}",
                            actual=item.asil_level,
                            citation_uri=c.artifact_uri,
                        )
                    )
        return violations

    def _check_wf5(
        self, step: CRCStep, phase: str
    ) -> list[WellFormednessViolation]:
        """WF₅: Claim kind must be allowed in the current ASPICE phase."""
        if not self._phase_kinds:
            return []
        allowed = self._phase_kinds.get(phase, [])
        if not allowed:
            return []
        if step.claim.kind.value not in allowed:
            return [
                WellFormednessViolation(
                    step_index=step.i,
                    violation_type=ViolationType.PHASE_VIOLATION,
                    message=(
                        f"Claim kind '{step.claim.kind}' not allowed "
                        f"in phase '{phase}'"
                    ),
                    expected=str(allowed),
                    actual=step.claim.kind.value,
                )
            ]
        return []

    def _check_wf6(self, step: CRCStep) -> list[WellFormednessViolation]:
        """WF₆: Shared structured fields between claim and cited artifact must agree.

        Full implementation requires the MKF Knowledge Graph runtime to resolve
        each citation's artifact_uri to its structured fields. Until MKF is
        reachable from the validator we perform a claim-internal consistency
        check: when the same key appears in `claim.fields` and in a citation's
        `span` metadata, the values must match.
        """
        violations: list[WellFormednessViolation] = []
        claim_fields = step.claim.fields or {}
        for c in step.citations:
            span = getattr(c, "span", None)
            span_meta = getattr(span, "metadata", None) if span else None
            if not isinstance(span_meta, dict):
                continue
            for k, v in span_meta.items():
                if k in claim_fields and claim_fields[k] != v:
                    violations.append(
                        WellFormednessViolation(
                            step_index=step.i,
                            violation_type=ViolationType.FIELD_MISMATCH,
                            message=(
                                f"Claim field '{k}' = {claim_fields[k]!r} "
                                f"contradicts citation span metadata = {v!r}"
                            ),
                            expected=str(v),
                            actual=str(claim_fields[k]),
                            citation_uri=c.artifact_uri,
                        )
                    )
        return violations
