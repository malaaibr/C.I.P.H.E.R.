"""Unit tests for Memory Agent service schemas (T-019)."""

from __future__ import annotations

from cipher.mkf.memory_agent.schemas import (
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryResult,
)


class TestMemorySchemas:
    def test_request_defaults(self) -> None:
        req = MemoryQueryRequest(query="AUTOSAR requirements")
        assert req.top_k == 5
        assert req.collection == "cipher_memory"

    def test_response_round_trip(self) -> None:
        resp = MemoryQueryResponse(
            results=[
                MemoryResult(
                    document="test doc",
                    score=0.85,
                    source="hybrid",
                    metadata={"stage": "S1N1"},
                )
            ],
            query="test",
            total=1,
        )
        restored = MemoryQueryResponse.model_validate_json(resp.model_dump_json())
        assert restored.total == 1
        assert restored.results[0].score == 0.85
