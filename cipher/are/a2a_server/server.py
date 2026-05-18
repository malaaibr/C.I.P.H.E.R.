"""A2A Server — FastAPI endpoints for task submission (T-021)."""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from cipher.core.otel import traced
from cipher.core.schemas.task_contract import TaskContract, TaskResult, TaskStatus

app = FastAPI(title="CIPHER A2A Server", version="0.1.0")

# Mount CIPHER VSIX bridge (REST + SSE for the VSCode webview).
from cipher.are.a2a_server.cipher_routes import router as _cipher_router  # noqa: E402

app.include_router(_cipher_router)

_tasks: dict[UUID, TaskContract] = {}
_results: dict[UUID, TaskResult] = {}
_events: dict[UUID, asyncio.Queue[str]] = {}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "a2a-server"}


@app.post("/v1/tasks", status_code=202)
@traced(name="a2a.submit_task", attributes={"layer": "are"})
async def submit_task(task: TaskContract) -> dict:
    _tasks[task.task_id] = task
    _events[task.task_id] = asyncio.Queue()
    asyncio.create_task(_dispatch_task(task))
    return {"task_id": str(task.task_id), "status": "PENDING"}


@app.get("/v1/tasks/{task_id}")
async def get_task_status(task_id: UUID) -> dict:
    if task_id in _results:
        return _results[task_id].model_dump(mode="json")
    if task_id in _tasks:
        return {"task_id": str(task_id), "status": "IN_PROGRESS"}
    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/v1/tasks/{task_id}/stream")
async def stream_task(task_id: UUID) -> StreamingResponse:
    if task_id not in _events:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        queue = _events[task_id]
        while True:
            msg = await queue.get()
            yield f"data: {msg}\n\n"
            if '"status":"COMPLETED"' in msg or '"status":"FAILED"' in msg:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _dispatch_task(task: TaskContract) -> None:
    from cipher.are.a2a_server.task_handler import handle_task

    queue = _events[task.task_id]
    await queue.put(f'{{"task_id": "{task.task_id}", "status": "IN_PROGRESS"}}')
    try:
        result = await handle_task(task)
        _results[task.task_id] = result
        await queue.put(result.model_dump_json())
    except Exception as e:
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
        )
        _results[task.task_id] = result
        await queue.put(result.model_dump_json())
