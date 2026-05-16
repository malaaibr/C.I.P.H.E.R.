"""QdrantIndex — vector store REWRITE replacing ChromaDB (T-015, ADR-0004)."""

from __future__ import annotations

import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantIndex:
    """
    Vector index backed by Qdrant.

    Interface mirrors the ChromaIndex from RagLab (add, search, delete_collection)
    but uses Qdrant as the backend per §1.3 hard constraint.
    """

    def __init__(
        self,
        collection_name: str = "cipher_memory",
        url: str | None = None,
        vector_size: int = 384,
    ) -> None:
        self._url = url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        self._collection = collection_name
        self._vector_size = vector_size
        self._client = QdrantClient(url=self._url)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self._client.get_collections().collections]
        if self._collection not in collections:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=Distance.COSINE
                ),
            )

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        points = [
            PointStruct(
                id=idx,
                vector=emb,
                payload={
                    "document": doc,
                    **(meta if meta else {}),
                },
            )
            for idx, (emb, doc, meta) in enumerate(
                zip(
                    embeddings,
                    documents,
                    metadatas or [{}] * len(documents),
                )
            )
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def search(
        self, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "document": hit.payload.get("document", "") if hit.payload else "",
                "metadata": {
                    k: v
                    for k, v in (hit.payload or {}).items()
                    if k != "document"
                },
            }
            for hit in results.points
        ]

    def delete_collection(self) -> None:
        self._client.delete_collection(self._collection)
