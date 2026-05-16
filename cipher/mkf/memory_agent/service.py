"""Memory Agent FastAPI service (T-019)."""

from __future__ import annotations

from fastapi import FastAPI

from cipher.core.otel import traced
from cipher.mkf.memory_agent.schemas import (
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryResult,
)

app = FastAPI(title="CIPHER Memory Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "memory-agent"}


@app.post("/v1/memory/query", response_model=MemoryQueryResponse)
@traced(name="memory_agent.query", attributes={"layer": "mkf"})
async def query_memory(req: MemoryQueryRequest) -> MemoryQueryResponse:
    from cipher.mkf.memory_agent._deps import get_retriever

    retriever = get_retriever(req.collection)
    results = retriever.retrieve(req.query, top_k=req.top_k)
    return MemoryQueryResponse(
        results=[
            MemoryResult(
                document=r.document,
                score=r.score,
                source=r.source,
                metadata={k: str(v) for k, v in r.metadata.items()},
            )
            for r in results
        ],
        query=req.query,
        total=len(results),
    )
