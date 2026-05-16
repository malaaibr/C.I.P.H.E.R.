"""LLM Gateway FastAPI server scaffold (T-010)."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cipher.core.schemas.task_contract import TaskClass

app = FastAPI(title="CIPHER LLM Gateway", version="0.1.0")


class CompletionRequest(BaseModel):
    prompt: str
    task_class: TaskClass
    context: dict = {}


class CompletionResponse(BaseModel):
    text: str
    backend_id: str
    task_class: str
    duration_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "llm-gateway"}


@app.post("/v1/complete", response_model=CompletionResponse)
async def complete(req: CompletionRequest) -> CompletionResponse:
    from cipher.trf.mcp_servers.llm_gateway.router import get_router

    router = get_router()
    try:
        response = await router.route(req.prompt, req.task_class, req.context)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return CompletionResponse(
        text=response.text,
        backend_id=response.backend_id,
        task_class=response.task_class,
        duration_ms=response.duration_ms,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
    )
