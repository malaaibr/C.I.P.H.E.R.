"""Tests for the CRC (Cited Reasoning Chain) schema — cipher.cap.crc.v1."""

import pytest
from pydantic import ValidationError

from cipher.core.schemas.crc import (
    CRCChain,
    CRCStep,
    Citation,
    Claim,
    ClaimKind,
    EvidenceType,
)


def _make_citation(**overrides):
    defaults = {
        "artifact_uri": "mkf://Dio.c#L10-L20",
        "span": "L10-L20",
        "evidence_type": EvidenceType.PRIOR_DESIGN,
    }
    defaults.update(overrides)
    return Citation(**defaults)


def _make_step(i=1, **overrides):
    defaults = {
        "i": i,
        "thought": "Dio_Init initializes port shadow registers.",
        "citations": [_make_citation()],
        "claim": Claim(kind=ClaimKind.FUNCTION_SIGNATURE, fields={"name": "Dio_Init"}),
    }
    defaults.update(overrides)
    return CRCStep(**defaults)


def _make_chain(**overrides):
    defaults = {
        "target_artifact": "LLD-Dio:v1",
        "target_asil": "B",
        "phase": "SWE.3",
        "steps": [_make_step()],
    }
    defaults.update(overrides)
    return CRCChain(**defaults)


class TestCitation:
    def test_valid_citation(self):
        c = _make_citation()
        assert c.artifact_uri == "mkf://Dio.c#L10-L20"
        assert c.evidence_type == EvidenceType.PRIOR_DESIGN

    def test_all_evidence_types(self):
        for et in EvidenceType:
            c = _make_citation(evidence_type=et)
            assert c.evidence_type == et


class TestCRCStep:
    def test_valid_step(self):
        s = _make_step()
        assert s.i == 1
        assert len(s.citations) == 1

    def test_step_requires_citation(self):
        with pytest.raises(ValidationError):
            _make_step(citations=[])

    def test_step_requires_thought(self):
        with pytest.raises(ValidationError):
            _make_step(thought="")

    def test_step_index_must_be_positive(self):
        with pytest.raises(ValidationError):
            _make_step(i=0)


class TestCRCChain:
    def test_valid_chain(self):
        chain = _make_chain()
        assert chain.schema_id == "cipher.cap.crc.v1"
        assert chain.step_count == 1
        assert chain.target_asil == "B"

    def test_chain_requires_steps(self):
        with pytest.raises(ValidationError):
            _make_chain(steps=[])

    def test_all_citations(self):
        chain = _make_chain(
            steps=[
                _make_step(i=1),
                _make_step(
                    i=2,
                    citations=[_make_citation(), _make_citation(artifact_uri="mkf://Dio_HLD.md#REQ-001")],
                ),
            ]
        )
        all_c = chain.all_citations()
        assert len(all_c) == 3

    def test_serialization_roundtrip(self):
        chain = _make_chain()
        json_str = chain.model_dump_json()
        restored = CRCChain.model_validate_json(json_str)
        assert restored.target_artifact == chain.target_artifact
        assert restored.steps[0].thought == chain.steps[0].thought


class TestClaimKinds:
    def test_all_claim_kinds_valid(self):
        for ck in ClaimKind:
            claim = Claim(kind=ck, fields={"test": "value"})
            assert claim.kind == ck
