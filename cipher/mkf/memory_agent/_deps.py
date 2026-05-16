"""Dependency wiring for the Memory Agent service (T-019)."""

from __future__ import annotations

from cipher.mkf.memory_agent.bm25_index import BM25Index
from cipher.mkf.memory_agent.embedder import EmbeddingModel
from cipher.mkf.memory_agent.qdrant_index import QdrantIndex
from cipher.mkf.memory_agent.retriever import HybridWeightedRetriever

_retrievers: dict[str, HybridWeightedRetriever] = {}


def get_retriever(collection: str = "cipher_memory") -> HybridWeightedRetriever:
    if collection not in _retrievers:
        embedder = EmbeddingModel()
        qdrant_index = QdrantIndex(collection_name=collection, vector_size=embedder.vector_size)
        bm25_index = BM25Index()
        _retrievers[collection] = HybridWeightedRetriever(
            qdrant_index=qdrant_index,
            bm25_index=bm25_index,
            embedder=embedder,
        )
    return _retrievers[collection]
