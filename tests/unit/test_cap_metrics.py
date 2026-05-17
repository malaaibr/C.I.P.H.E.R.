"""Tests for CAP Metrics computation."""

import pytest

from cipher.core.cap_metrics import (
    aspice_evidence_completeness,
    attribution_precision,
    attribution_recall,
    citation_coverage,
    compute_metrics,
    determinism_score,
)
from cipher.core.schemas.crc import (
    CRCChain,
    CRCStep,
    Citation,
    Claim,
    ClaimKind,
    EvidenceType,
)


def _chain(n_steps=3, uri_prefix="mkf://Dio"):
    steps = []
    for i in range(1, n_steps + 1):
        steps.append(
            CRCStep(
                i=i,
                thought=f"Step {i} analysis",
                citations=[
                    Citation(
                        artifact_uri=f"{uri_prefix}.c#L{i*10}",
                        evidence_type=EvidenceType.PRIOR_DESIGN,
                    )
                ],
                claim=Claim(kind=ClaimKind.FUNCTION_SIGNATURE, fields={"name": f"fn_{i}"}),
            )
        )
    return CRCChain(
        target_artifact="LLD-Test:v1",
        target_asil="B",
        phase="SWE.3",
        steps=steps,
    )


class TestCitationCoverage:
    def test_full_coverage(self):
        assert citation_coverage(_chain()) == 1.0

    def test_empty_chain(self):
        chain = CRCChain(
            target_artifact="LLD-Test:v1",
            steps=[
                CRCStep(
                    i=1,
                    thought="t",
                    citations=[Citation(artifact_uri="mkf://x", evidence_type=EvidenceType.REQUIREMENT)],
                    claim=Claim(kind=ClaimKind.REVIEW_NEEDED),
                )
            ],
        )
        assert citation_coverage(chain) == 1.0


class TestAttributionMetrics:
    def test_perfect_match(self):
        model = {"mkf://a", "mkf://b"}
        gold = {"mkf://a", "mkf://b"}
        assert attribution_precision(model, gold) == 1.0
        assert attribution_recall(model, gold) == 1.0

    def test_partial_match(self):
        model = {"mkf://a", "mkf://b", "mkf://c"}
        gold = {"mkf://a", "mkf://b"}
        assert attribution_precision(model, gold) == pytest.approx(2 / 3)
        assert attribution_recall(model, gold) == 1.0

    def test_no_match(self):
        assert attribution_precision({"mkf://a"}, {"mkf://b"}) == 0.0

    def test_empty_sets(self):
        assert attribution_precision(set(), {"mkf://a"}) == 0.0
        assert attribution_recall({"mkf://a"}, set()) == 0.0


class TestDeterminismScore:
    def test_identical_chains(self):
        c1 = _chain()
        c2 = _chain()
        assert determinism_score([c1, c2]) == 1.0

    def test_different_chains(self):
        c1 = _chain(uri_prefix="mkf://Dio")
        c2 = _chain(uri_prefix="mkf://Port")
        ds = determinism_score([c1, c2])
        assert ds < 1.0

    def test_single_chain(self):
        assert determinism_score([_chain()]) == 1.0


class TestASPICECompleteness:
    def test_full_completeness(self):
        required = {"LLD_CSV", "TRACE_MATRIX", "REVIEW_RECORD"}
        present = {"LLD_CSV", "TRACE_MATRIX", "REVIEW_RECORD"}
        assert aspice_evidence_completeness(present, required) == 1.0

    def test_partial_completeness(self):
        required = {"LLD_CSV", "TRACE_MATRIX", "REVIEW_RECORD"}
        present = {"LLD_CSV"}
        assert aspice_evidence_completeness(present, required) == pytest.approx(1 / 3)


class TestComputeMetrics:
    def test_basic_metrics(self):
        chain = _chain()
        report = compute_metrics(chain)
        assert report.citation_coverage == 1.0
        assert report.citation_support_rate == 1.0
        assert report.determinism_score == 1.0
        assert report.hallucination_rate == 0.0
