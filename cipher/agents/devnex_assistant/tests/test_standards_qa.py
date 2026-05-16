"""test_standards_qa.py — UC 4.1: Standards Q&A Hybrid RAG test suite.

Classes:
  TestHybridRetriever  — BM25 keyword search, score fusion, normalisation
  TestSourceChunk      — Dataclass and score computation
  TestStandardsQASkill — answer() method with mocked backends
  TestIndexLoading     — load_index() correctness
  TestCitationFormat   — Source citation output structure
"""
from __future__ import annotations

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from skills.automotive.standards_qa_skill import (
    HybridRetriever, SourceChunk, StandardsQASkill, QAAnswer, DEFAULT_ALPHA, TOP_K,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_DOCS = [
    {"id": "iso-1", "text": "ASIL-D requires the highest level of software integrity measures including MC/DC coverage.", "source": "ISO 26262-6:2018 §5.4"},
    {"id": "iso-2", "text": "Software unit testing shall be performed according to ASIL-D requirements including 100% MC/DC.", "source": "ISO 26262-6:2018 §9.4"},
    {"id": "misra-1", "text": "Rule R11.8: A cast shall not remove any const or volatile qualification from the type pointed to by a pointer.", "source": "MISRA-C:2012 Rule 11.8"},
    {"id": "misra-2", "text": "Rule R1.3: There shall be no occurrence of undefined or critical unspecified behaviour.", "source": "MISRA-C:2012 Rule 1.3"},
    {"id": "autosar-1", "text": "The AUTOSAR BSW module NvM provides services for reading and writing to non-volatile memory.", "source": "AUTOSAR SWS_NvM R21-11 §7.1"},
]


# ─────────────────────────────────────────────────────────────────────────────
# TestHybridRetriever
# ─────────────────────────────────────────────────────────────────────────────
class TestHybridRetriever:
    def setup_method(self):
        self.retriever = HybridRetriever(index_key="iso26262", alpha=0.7)
        self.retriever.load_documents(SAMPLE_DOCS)

    def test_bm25_returns_results(self):
        results = self.retriever._bm25_search("MC/DC coverage ASIL", top_k=3)
        assert len(results) > 0

    def test_bm25_top_result_is_relevant(self):
        results = self.retriever._bm25_search("MC/DC coverage ASIL", top_k=3)
        texts = " ".join(r.text for r in results[:2])
        assert "MC/DC" in texts

    def test_bm25_scores_normalised_between_0_and_1(self):
        results = self.retriever._bm25_search("ASIL-D", top_k=5)
        for r in results:
            assert 0.0 <= r.bm25_score <= 1.0 + 1e-6

    def test_retrieve_returns_up_to_top_k(self):
        results = self.retriever.retrieve("ASIL-D software testing", top_k=3)
        assert len(results) <= 3

    def test_retrieve_hybrid_score_computed(self):
        results = self.retriever.retrieve("ASIL", top_k=5)
        for r in results:
            # hybrid_score = alpha * dense + (1-alpha) * bm25
            # dense=0 (Qdrant unavailable), so hybrid = (1-alpha)*bm25
            expected = round((1 - DEFAULT_ALPHA) * r.bm25_score, 6)
            assert abs(r.hybrid_score - expected) < 0.001

    def test_misra_r11_retrieved_for_cast_query(self):
        results = self.retriever.retrieve("cast volatile qualification", top_k=3)
        sources = [r.source for r in results]
        assert any("MISRA" in s for s in sources)

    def test_empty_store_returns_empty(self):
        r = HybridRetriever()
        results = r._bm25_search("anything", top_k=5)
        assert results == []

    def test_retrieve_sorted_by_hybrid_score_desc(self):
        results = self.retriever.retrieve("ASIL software testing", top_k=5)
        scores = [r.hybrid_score for r in results]
        assert scores == sorted(scores, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# TestSourceChunk
# ─────────────────────────────────────────────────────────────────────────────
class TestSourceChunk:
    def test_hybrid_score_manual_calculation(self):
        chunk = SourceChunk(
            doc_id="x", text="test", source="ISO",
            dense_score=0.8, bm25_score=0.6, hybrid_score=0.0,
        )
        alpha = 0.7
        chunk.hybrid_score = alpha * chunk.dense_score + (1 - alpha) * chunk.bm25_score
        assert abs(chunk.hybrid_score - 0.74) < 0.001

    def test_default_scores_are_zero(self):
        chunk = SourceChunk(doc_id="y", text="t", source="s")
        assert chunk.dense_score == 0.0
        assert chunk.bm25_score == 0.0
        assert chunk.hybrid_score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TestStandardsQASkill
# ─────────────────────────────────────────────────────────────────────────────
class TestStandardsQASkill:
    def setup_method(self):
        self.skill = StandardsQASkill(index_key="iso26262")
        self.skill.load_index(SAMPLE_DOCS)

    def test_answer_returns_qa_answer(self):
        with patch.object(self.skill, "_generate_answer", return_value="ASIL-D requires MC/DC."):
            result = self.skill.answer("What does ASIL-D require for testing?")
        assert isinstance(result, QAAnswer)

    def test_answer_contains_sources(self):
        with patch.object(self.skill, "_generate_answer", return_value="Answer text."):
            result = self.skill.answer("ASIL-D unit testing requirements")
        assert isinstance(result.sources, list)
        assert len(result.sources) > 0

    def test_answer_sources_have_required_fields(self):
        with patch.object(self.skill, "_generate_answer", return_value="Ans"):
            result = self.skill.answer("ASIL-D MC/DC")
        for src in result.sources:
            assert "source" in src
            assert "excerpt" in src
            assert "score" in src

    def test_answer_score_is_float(self):
        with patch.object(self.skill, "_generate_answer", return_value="Ans"):
            result = self.skill.answer("ASIL-D")
        for src in result.sources:
            assert isinstance(src["score"], float)

    def test_scope_filter_applied_in_query(self):
        """scope_filter should be prepended to the query string."""
        with patch.object(self.skill.retriever, "retrieve", return_value=[]) as mock_ret:
            with patch.object(self.skill, "_fallback_answer", return_value="fallback"):
                self.skill.answer("coverage requirements", scope_filter="Part 6")
        call_args = mock_ret.call_args[0][0]
        assert "Part 6" in call_args

    def test_no_documents_returns_fallback(self):
        skill = StandardsQASkill(index_key="empty_idx")
        result = skill.answer("any question")
        assert "No indexed documents" in result.answer

    def test_answer_uses_index_key(self):
        skill = StandardsQASkill(index_key="misra_c")
        skill.load_index(SAMPLE_DOCS)
        with patch.object(skill, "_generate_answer", return_value="ans"):
            result = skill.answer("volatile cast rule")
        assert result.index_used == "misra_c"


# ─────────────────────────────────────────────────────────────────────────────
# TestIndexLoading
# ─────────────────────────────────────────────────────────────────────────────
class TestIndexLoading:
    def test_load_index_populates_mem_store(self):
        skill = StandardsQASkill()
        skill.load_index(SAMPLE_DOCS)
        assert len(skill.retriever._mem_store) == len(SAMPLE_DOCS)

    def test_load_index_overwrites_previous(self):
        skill = StandardsQASkill()
        skill.load_index(SAMPLE_DOCS)
        skill.load_index([SAMPLE_DOCS[0]])
        assert len(skill.retriever._mem_store) == 1

    def test_empty_load_clears_store(self):
        skill = StandardsQASkill()
        skill.load_index(SAMPLE_DOCS)
        skill.load_index([])
        assert len(skill.retriever._mem_store) == 0


# ─────────────────────────────────────────────────────────────────────────────
# TestCitationFormat
# ─────────────────────────────────────────────────────────────────────────────
class TestCitationFormat:
    def test_sources_ordered_by_score_desc(self):
        skill = StandardsQASkill()
        skill.load_index(SAMPLE_DOCS)
        with patch.object(skill, "_generate_answer", return_value="ans"):
            result = skill.answer("ASIL MC/DC software unit testing")
        scores = [s["score"] for s in result.sources]
        assert scores == sorted(scores, reverse=True)

    def test_excerpt_max_300_chars(self):
        long_doc = [{"id": "long-1", "text": "A" * 500, "source": "TEST §1"}]
        skill = StandardsQASkill()
        skill.load_index(long_doc)
        with patch.object(skill, "_generate_answer", return_value="ans"):
            result = skill.answer("test")
        for src in result.sources:
            assert len(src["excerpt"]) <= 300

    def test_answer_top_k_reported_correctly(self):
        skill = StandardsQASkill()
        skill.load_index(SAMPLE_DOCS)
        with patch.object(skill, "_generate_answer", return_value="ans"):
            result = skill.answer("ASIL-D", )
        assert result.top_k == len(result.sources)
