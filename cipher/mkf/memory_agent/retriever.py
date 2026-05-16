"""HybridWeightedRetriever — combines vector + BM25 (T-018, ADR-0004)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cipher.mkf.memory_agent.bm25_index import BM25Index
from cipher.mkf.memory_agent.embedder import EmbeddingModel
from cipher.mkf.memory_agent.qdrant_index import QdrantIndex


@dataclass
class RetrievalResult:
    document: str
    score: float
    source: str
    metadata: dict[str, Any]


class HybridWeightedRetriever:
    """
    Hybrid retrieval combining dense (Qdrant) and sparse (BM25) scores.

    Final score = alpha * vector_score + (1 - alpha) * bm25_score
    Default alpha=0.5 per ADR-0004.
    """

    def __init__(
        self,
        qdrant_index: QdrantIndex,
        bm25_index: BM25Index,
        embedder: EmbeddingModel,
        alpha: float = 0.5,
    ) -> None:
        self._qdrant = qdrant_index
        self._bm25 = bm25_index
        self._embedder = embedder
        self._alpha = alpha

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        query_vec = self._embedder.encode_query(query)
        vector_results = self._qdrant.search(query_vec, top_k=top_k * 2)

        bm25_results = self._bm25.search(query, top_k=top_k * 2)

        doc_scores: dict[str, dict[str, Any]] = {}

        for vr in vector_results:
            doc = vr["document"]
            doc_scores[doc] = {
                "vector_score": vr["score"],
                "bm25_score": 0.0,
                "metadata": vr.get("metadata", {}),
            }

        for br in bm25_results:
            if br.document in doc_scores:
                doc_scores[br.document]["bm25_score"] = br.score
            else:
                doc_scores[br.document] = {
                    "vector_score": 0.0,
                    "bm25_score": br.score,
                    "metadata": {},
                }

        max_bm25 = max(
            (d["bm25_score"] for d in doc_scores.values()), default=1.0
        ) or 1.0

        results: list[RetrievalResult] = []
        for doc, scores in doc_scores.items():
            norm_bm25 = scores["bm25_score"] / max_bm25
            combined = self._alpha * scores["vector_score"] + (1 - self._alpha) * norm_bm25
            results.append(
                RetrievalResult(
                    document=doc,
                    score=combined,
                    source="hybrid",
                    metadata=scores["metadata"],
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
