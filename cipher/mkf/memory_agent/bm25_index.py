"""BM25Index — sparse retrieval adapter (T-016, WRAP from raglab_core)."""

from __future__ import annotations

from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi


@dataclass
class BM25Result:
    document: str
    score: float
    index: int


class BM25Index:
    """Sparse keyword retrieval using BM25Okapi."""

    def __init__(self) -> None:
        self._corpus: list[str] = []
        self._tokenized: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def fit(self, documents: list[str]) -> None:
        self._corpus = documents
        self._tokenized = [doc.lower().split() for doc in documents]
        self._bm25 = BM25Okapi(self._tokenized)

    def search(self, query: str, top_k: int = 5) -> list[BM25Result]:
        if self._bm25 is None:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            BM25Result(document=self._corpus[idx], score=score, index=idx)
            for idx, score in ranked
            if score > 0
        ]
