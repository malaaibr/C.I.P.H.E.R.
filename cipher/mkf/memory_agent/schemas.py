"""Memory Agent request/response schemas (T-019)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: str = "cipher_memory"


class MemoryResult(BaseModel):
    document: str
    score: float
    source: str
    metadata: dict[str, str] = Field(default_factory=dict)


class MemoryQueryResponse(BaseModel):
    results: list[MemoryResult]
    query: str
    total: int
