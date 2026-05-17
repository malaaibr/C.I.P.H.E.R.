"""Tests for the CAP Validator — WF₁–WF₆ well-formedness checks."""

import pytest

from cipher.core.schemas.context_manifest import (
    ArtifactType,
    ContextManifest,
    EvidenceItem,
)
from cipher.core.schemas.crc import (
    CRCChain,
    CRCStep,
    Citation,
    Claim,
    ClaimKind,
    EvidenceType,
)
from cipher.core.schemas.issue_report import ValidationVerdict, ViolationType
from cipher.gcl.cap_validator.validator import CAPValidator


def _citation(uri="mkf://Dio.c", etype=EvidenceType.PRIOR_DESIGN, span=""):
    return Citation(artifact_uri=uri, span=span, evidence_type=etype)


def _step(i=1, citations=None, kind=ClaimKind.FUNCTION_SIGNATURE):
    return CRCStep(
        i=i,
        thought="Test thought",
        citations=citations or [_citation()],
        claim=Claim(kind=kind, fields={}),
    )


def _chain(steps=None, target_asil="B", phase="SWE.3"):
    return CRCChain(
        target_artifact="LLD-Test:v1",
        target_asil=target_asil,
        phase=phase,
        steps=steps or [_step()],
    )


def _manifest(*uris_and_asils):
    items = []
    for uri, asil in uris_and_asils:
        items.append(
            EvidenceItem(uri=uri, artifact_type=ArtifactType.SOURCE_CODE, asil_level=asil)
        )
    return ContextManifest(evidence_items=items)


class TestWF2Unresolved:
    def test_pass_when_uri_in_manifest(self):
        manifest = _manifest(("mkf://Dio.c", "B"))
        v = CAPValidator(manifest=manifest)
        report = v.validate(_chain())
        assert report.is_pass

    def test_fail_when_uri_not_in_manifest(self):
        manifest = _manifest(("mkf://Port.c", "B"))
        v = CAPValidator(manifest=manifest)
        report = v.validate(_chain())
        assert not report.is_pass
        assert any(viol.violation_type == ViolationType.UNRESOLVED for viol in report.violations)

    def test_skip_when_no_manifest(self):
        v = CAPValidator(manifest=None)
        report = v.validate(_chain())
        assert report.is_pass


class TestWF3TypeMismatch:
    def test_pass_when_type_permitted(self):
        v = CAPValidator(domain_pack="iso26262_asil_b")
        chain = _chain(steps=[_step(kind=ClaimKind.FUNCTION_SIGNATURE)])
        report = v.validate(chain)
        wf3_viols = [v for v in report.violations if v.violation_type == ViolationType.TYPE_MISMATCH]
        assert len(wf3_viols) == 0

    def test_fail_when_type_not_permitted(self):
        v = CAPValidator(domain_pack="iso26262_asil_b")
        chain = _chain(
            steps=[
                _step(
                    kind=ClaimKind.TIMING_PARAM,
                    citations=[_citation(etype=EvidenceType.TEST_VECTOR)],
                )
            ]
        )
        report = v.validate(chain)
        wf3_viols = [v for v in report.violations if v.violation_type == ViolationType.TYPE_MISMATCH]
        assert len(wf3_viols) > 0


class TestWF4ASILDowncast:
    def test_pass_when_asil_sufficient(self):
        manifest = _manifest(("mkf://Dio.c", "B"))
        v = CAPValidator(manifest=manifest)
        chain = _chain(target_asil="B")
        report = v.validate(chain)
        asil_viols = [v for v in report.violations if v.violation_type == ViolationType.ASIL_DOWNCAST]
        assert len(asil_viols) == 0

    def test_fail_when_asil_insufficient(self):
        manifest = _manifest(("mkf://Dio.c", "QM"))
        v = CAPValidator(manifest=manifest)
        chain = _chain(target_asil="B")
        report = v.validate(chain)
        asil_viols = [v for v in report.violations if v.violation_type == ViolationType.ASIL_DOWNCAST]
        assert len(asil_viols) > 0


class TestWF5PhaseViolation:
    def test_pass_when_kind_allowed_in_phase(self):
        v = CAPValidator(domain_pack="iso26262_asil_b")
        chain = _chain(
            phase="SWE.3",
            steps=[_step(kind=ClaimKind.FUNCTION_SIGNATURE)],
        )
        report = v.validate(chain)
        phase_viols = [v for v in report.violations if v.violation_type == ViolationType.PHASE_VIOLATION]
        assert len(phase_viols) == 0


class TestFullValidation:
    def test_all_pass(self):
        manifest = _manifest(("mkf://Dio.c", "B"))
        v = CAPValidator(manifest=manifest, domain_pack="iso26262_asil_b")
        chain = _chain(target_asil="B", phase="SWE.3")
        report = v.validate(chain)
        assert report.is_pass
        assert report.violation_count == 0

    def test_multiple_violations(self):
        manifest = _manifest(("mkf://Port.c", "QM"))
        v = CAPValidator(manifest=manifest, domain_pack="iso26262_asil_b")
        chain = _chain(target_asil="C")
        report = v.validate(chain)
        assert not report.is_pass
        assert report.violation_count >= 1
