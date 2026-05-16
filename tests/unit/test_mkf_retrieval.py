"""Unit tests for MKF retrieval components (T-015, T-016, T-017, T-018)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cipher.mkf.memory_agent.bm25_index import BM25Index


class TestBM25Index:
    def test_fit_and_search(self) -> None:
        index = BM25Index()
        docs = [
            "automotive embedded software requirements",
            "unit testing best practices for C code",
            "AUTOSAR Classic platform architecture",
            "python asyncio event loop internals",
        ]
        index.fit(docs)

        results = index.search("AUTOSAR architecture", top_k=2)
        assert len(results) >= 1
        assert "AUTOSAR" in results[0].document

    def test_search_before_fit_returns_empty(self) -> None:
        index = BM25Index()
        results = index.search("anything")
        assert results == []

    def test_no_results_for_unrelated_query(self) -> None:
        index = BM25Index()
        index.fit(["hello world", "foo bar baz"])
        results = index.search("quantum physics relativity")
        assert len(results) == 0


class TestQdrantIndex:
    def test_add_and_search_mocked(self) -> None:
        with patch("cipher.mkf.memory_agent.qdrant_index.QdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_client.create_collection = MagicMock()
            mock_cls.return_value = mock_client

            from cipher.mkf.memory_agent.qdrant_index import QdrantIndex

            idx = QdrantIndex(collection_name="test_col", vector_size=4)
            mock_client.create_collection.assert_called_once()

            idx.add(
                ids=["a", "b"],
                embeddings=[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]],
                documents=["doc a", "doc b"],
            )
            mock_client.upsert.assert_called_once()

    def test_delete_collection_mocked(self) -> None:
        with patch("cipher.mkf.memory_agent.qdrant_index.QdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MagicMock(
                collections=[MagicMock(name="test_col")]
            )
            mock_cls.return_value = mock_client

            from cipher.mkf.memory_agent.qdrant_index import QdrantIndex

            idx = QdrantIndex(collection_name="test_col", vector_size=4)
            idx.delete_collection()
            mock_client.delete_collection.assert_called_once_with("test_col")


class TestHybridRetriever:
    def test_retrieve_combines_scores(self) -> None:
        # Mock sentence_transformers before importing retriever
        import sys
        mock_st = MagicMock()
        sys.modules.setdefault("sentence_transformers", mock_st)

        mock_qdrant = MagicMock()
        mock_qdrant.search.return_value = [
            {"document": "doc A", "score": 0.9, "metadata": {}},
            {"document": "doc B", "score": 0.5, "metadata": {}},
        ]

        mock_bm25 = MagicMock()
        from cipher.mkf.memory_agent.bm25_index import BM25Result

        mock_bm25.search.return_value = [
            BM25Result(document="doc A", score=2.0, index=0),
            BM25Result(document="doc C", score=3.0, index=2),
        ]

        mock_embedder = MagicMock()
        mock_embedder.encode_query.return_value = [0.1, 0.2, 0.3]

        from cipher.mkf.memory_agent.retriever import HybridWeightedRetriever

        retriever = HybridWeightedRetriever(
            qdrant_index=mock_qdrant,
            bm25_index=mock_bm25,
            embedder=mock_embedder,
            alpha=0.5,
        )

        results = retriever.retrieve("test query", top_k=3)
        assert len(results) >= 1
        assert results[0].document == "doc A"
        assert results[0].source == "hybrid"
