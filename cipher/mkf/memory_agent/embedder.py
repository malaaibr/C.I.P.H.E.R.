"""EmbeddingModel adapter (T-017, WRAP from raglab_core)."""

from __future__ import annotations

import os

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Wraps sentence-transformers for embedding generation."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or os.environ.get(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def vector_size(self) -> int:
        return self.model.get_sentence_embedding_dimension()  # type: ignore[return-value]

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        return self.encode([query])[0]
