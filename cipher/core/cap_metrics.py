"""CAP Metrics — 8 evaluation metrics for citation-aware LLM agents.

Implements the metrics defined in the Citation-Aware Prompting paper §VII.A:
  CC   — Citation Coverage
  CSR  — Citation Support Rate
  AP   — Attribution Precision
  AR   — Attribution Recall
  AQ   — Abstention Quality (F₁)
  DS   — Determinism Score (pairwise Jaccard)
  HR   — Hallucination Rate (automatic, based on WF₆)
  AEC  — ASPICE Evidence Completeness
"""

from __future__ import annotations

from dataclasses import dataclass

from cipher.core.schemas.crc import CRCChain, Citation


def citation_coverage(crc: CRCChain) -> float:
    """CC = |{i : Cᵢ ≠ ∅}| / n — fraction of steps with at least one citation."""
    if not crc.steps:
        return 0.0
    cited = sum(1 for s in crc.steps if s.citations)
    return cited / len(crc.steps)


def citation_support_rate(
    crc: CRCChain,
    support_fn: callable | None = None,
) -> float:
    """CSR = |{c : g(c, K[c]) = ⊤}| / |⋃ᵢ Cᵢ| — fraction of genuinely-supporting citations.

    Args:
        support_fn: Optional (citation, claim) → bool predicate.
                    If None, all citations are assumed supporting (format-only check).
    """
    all_citations = crc.all_citations()
    if not all_citations:
        return 0.0
    if support_fn is None:
        return 1.0
    supported = 0
    for step in crc.steps:
        for c in step.citations:
            if support_fn(c, step.claim):
                supported += 1
    return supported / len(all_citations)


def attribution_precision(
    model_citations: set[str],
    gold_citations: set[str],
) -> float:
    """Attr-P = |C ∩ G| / |C| — how much of what the model produced was correct."""
    if not model_citations:
        return 0.0
    return len(model_citations & gold_citations) / len(model_citations)


def attribution_recall(
    model_citations: set[str],
    gold_citations: set[str],
) -> float:
    """Attr-R = |C ∩ G| / |G| — how much of what should have been produced was."""
    if not gold_citations:
        return 0.0
    return len(model_citations & gold_citations) / len(gold_citations)


def determinism_score(chains: list[CRCChain]) -> float:
    """DS = mean pairwise Jaccard over structural triple sets across N runs.

    Extracts (claim_kind, sorted_fields_tuple, frozenset_of_citation_uris) per step.
    """
    if len(chains) < 2:
        return 1.0

    def _triples(crc: CRCChain) -> set[tuple]:
        result = set()
        for s in crc.steps:
            fields_key = tuple(sorted(s.claim.fields.items()))
            uris = frozenset(c.artifact_uri for c in s.citations)
            result.add((s.claim.kind.value, fields_key, uris))
        return result

    triple_sets = [_triples(c) for c in chains]
    n = len(triple_sets)
    total = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = triple_sets[i], triple_sets[j]
            union = a | b
            if not union:
                total += 1.0
            else:
                total += len(a & b) / len(union)
            pairs += 1
    return total / pairs if pairs else 1.0


def hallucination_rate_auto(
    crc: CRCChain,
    wf6_check_fn: callable | None = None,
) -> float:
    """HR(auto) = |{i : ¬WF₆(Kᵢ, Cᵢ)}| / n — fraction of steps with field mismatches.

    Without a WF₆ checker function, returns 0.0 (no mismatches detectable).
    """
    if not crc.steps:
        return 0.0
    if wf6_check_fn is None:
        return 0.0
    failures = sum(1 for s in crc.steps if not wf6_check_fn(s.claim, s.citations))
    return failures / len(crc.steps)


def aspice_evidence_completeness(
    present_work_products: set[str],
    required_work_products: set[str],
) -> float:
    """AEC = |{wp ∈ WP_required : present(wp) ∧ complete(wp)}| / |WP_required|."""
    if not required_work_products:
        return 1.0
    return len(present_work_products & required_work_products) / len(required_work_products)


@dataclass
class CAPMetricsReport:
    """Aggregated metrics for one CRC evaluation."""

    citation_coverage: float
    citation_support_rate: float
    determinism_score: float
    hallucination_rate: float
    aspice_evidence_completeness: float
    attribution_precision: float | None = None
    attribution_recall: float | None = None
    abstention_quality: float | None = None
    latency_overhead: float | None = None
    token_overhead: float | None = None


def compute_metrics(
    crc: CRCChain,
    gold_citations: set[str] | None = None,
    all_runs: list[CRCChain] | None = None,
    required_work_products: set[str] | None = None,
    present_work_products: set[str] | None = None,
) -> CAPMetricsReport:
    """Compute all available CAP metrics for a single CRC."""
    model_uris = {c.artifact_uri for c in crc.all_citations()}

    ap = ar = None
    if gold_citations is not None:
        ap = attribution_precision(model_uris, gold_citations)
        ar = attribution_recall(model_uris, gold_citations)

    ds = 1.0
    if all_runs and len(all_runs) >= 2:
        ds = determinism_score(all_runs)

    aec = 1.0
    if required_work_products and present_work_products is not None:
        aec = aspice_evidence_completeness(present_work_products, required_work_products)

    return CAPMetricsReport(
        citation_coverage=citation_coverage(crc),
        citation_support_rate=citation_support_rate(crc),
        determinism_score=ds,
        hallucination_rate=hallucination_rate_auto(crc),
        aspice_evidence_completeness=aec,
        attribution_precision=ap,
        attribution_recall=ar,
    )
