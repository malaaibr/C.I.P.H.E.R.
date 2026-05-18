"""
CIPHER REST + SSE routes for the VSCode webview surface.

Mounted on the existing A2A FastAPI app at /cipher and /events.
All operations are loopback-only; the headless host binds 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from cipher.interfaces.web.event_bridge import get_event_bridge

router = APIRouter()


# ── In-memory run registry (single-process headless host) ─────────────────────
_runs: dict[str, dict[str, Any]] = {}
_review_events: dict[str, threading.Event] = {}
_review_decisions: dict[str, bool] = {}
_config: dict[str, Any] = {}

_orchestrator_ref: Any = None  # injected by run_poc.py


def attach_orchestrator(orch: Any) -> None:
    """Inject the CipherOrchestrator so REST handlers can reach DevNex."""
    global _orchestrator_ref
    _orchestrator_ref = orch


def _devnex_orchestrator() -> Any:
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="CipherOrchestrator not attached")
    devnex = _orchestrator_ref.get_child("devnex")
    if devnex is None:
        # Lazy create on first call so headless mode mirrors GUI behavior.
        devnex = _create_devnex_lazy()
        _orchestrator_ref.register_child("devnex", devnex)
    return devnex


def _create_devnex_lazy() -> Any:
    """Construct DevNexOrchestrator from current config — runs once."""
    import sys
    from pathlib import Path

    devnex_root = Path(__file__).resolve().parents[3] / "agents" / "devnex_assistant"
    if str(devnex_root) not in sys.path:
        sys.path.insert(0, str(devnex_root))

    from core.run_context import DevNexRunContext  # type: ignore
    from core.orchestrator import DevNexOrchestrator  # type: ignore

    ctx = DevNexRunContext(
        swc_name=_config.get("SWC_name", "SWC"),
        workspace_path=_config.get("workspace_path", "."),
    )
    return DevNexOrchestrator(run_context=ctx)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReviewDecision(BaseModel):
    approved: bool


class RunIdResponse(BaseModel):
    runId: str


# ── Health + config ───────────────────────────────────────────────────────────

@router.get("/cipher/healthz")
async def healthz() -> dict:
    return {
        "ok": True,
        "service": "cipher-vsix-bridge",
        "orchestrator_attached": _orchestrator_ref is not None,
        "active_runs": list(_runs.keys()),
    }


@router.get("/cipher/config")
async def get_config() -> dict:
    return dict(_config)


@router.put("/cipher/config")
async def put_config(cfg: dict[str, Any]) -> dict:
    """Validate and persist config. Fails fast on bad workspace_path."""
    import os
    wp = cfg.get("workspace_path")
    if wp:
        if not os.path.exists(wp):
            raise HTTPException(
                status_code=400,
                detail=f"workspace_path does not exist: {wp!r}",
            )
        if not os.path.isdir(wp):
            raise HTTPException(
                status_code=400,
                detail=f"workspace_path is not a directory: {wp!r}",
            )
    target_asil = cfg.get("target_asil")
    if target_asil and target_asil not in ("QM", "ASIL-A", "ASIL-B", "ASIL-C", "ASIL-D"):
        raise HTTPException(status_code=400, detail=f"Invalid target_asil: {target_asil!r}")
    _config.clear()
    _config.update(cfg)
    get_event_bridge().emit_status("config.updated", keys=list(cfg.keys()))
    return {"ok": True, "keys": list(_config.keys())}


# ── Runs ──────────────────────────────────────────────────────────────────────

@router.post("/cipher/nodes/{node_id}/run", response_model=RunIdResponse)
async def run_node(node_id: str) -> RunIdResponse:
    orch = _devnex_orchestrator()
    run_id = str(uuid.uuid4())
    _runs[run_id] = {"kind": "node", "node_id": node_id, "status": "running"}

    bridge = get_event_bridge()

    def _runner() -> None:
        bridge.emit_node_started(node_id, run_id=run_id)
        try:
            _wire_orchestrator_callbacks(orch, bridge, run_id)
            result = orch.run_node(node_id)
            _runs[run_id]["status"] = "complete"
            bridge.emit_node_complete(node_id, result, run_id=run_id)
        except Exception as e:  # noqa: BLE001
            _runs[run_id]["status"] = "error"
            _runs[run_id]["error"] = str(e)
            bridge.emit_error(str(e), run_id=run_id, node_id=node_id)

    threading.Thread(target=_runner, daemon=True, name=f"cipher-run-{node_id}").start()
    return RunIdResponse(runId=run_id)


@router.post("/cipher/runs/full", response_model=RunIdResponse)
async def run_full() -> RunIdResponse:
    orch = _devnex_orchestrator()
    run_id = str(uuid.uuid4())
    _runs[run_id] = {"kind": "full", "status": "running"}

    bridge = get_event_bridge()

    def _runner() -> None:
        try:
            _wire_orchestrator_callbacks(orch, bridge, run_id)

            def _progress(pct: int, msg: str) -> None:
                bridge.emit_progress(pct, msg, run_id=run_id)

            results = orch.run_all(progress_callback=_progress)
            _runs[run_id]["status"] = "complete"
            bridge.emit_status("run.complete", runId=run_id, count=len(results) if hasattr(results, "__len__") else None)
        except Exception as e:  # noqa: BLE001
            _runs[run_id]["status"] = "error"
            _runs[run_id]["error"] = str(e)
            bridge.emit_error(str(e), run_id=run_id)

    threading.Thread(target=_runner, daemon=True, name="cipher-run-full").start()
    return RunIdResponse(runId=run_id)


@router.post("/cipher/runs/{run_id}/review")
async def submit_review(run_id: str, decision: ReviewDecision) -> dict:
    ev = _review_events.get(run_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="No pending review for run")
    _review_decisions[run_id] = decision.approved
    ev.set()
    return {"ok": True, "runId": run_id, "approved": decision.approved}


@router.post("/cipher/workflow/reset")
async def workflow_reset() -> dict:
    _runs.clear()
    _review_events.clear()
    _review_decisions.clear()
    get_event_bridge().emit_status("workflow.reset")
    return {"ok": True}


# ── Infra status (Sprint 3) ──────────────────────────────────────────────────

_INFRA_PORTS = {
    "Redis":    ("127.0.0.1",  6379),
    "Memgraph": ("127.0.0.1",  7687),
    "Qdrant":   ("127.0.0.1",  6333),
    "MinIO":    ("127.0.0.1",  9000),
    "NATS":     ("127.0.0.1",  4222),
    "OPA":      ("127.0.0.1",  8181),
    "Ollama":   ("127.0.0.1", 11434),
    "LLM-Gateway": ("127.0.0.1", 8200),
}


@router.get("/cipher/infra/status")
async def infra_status() -> dict:
    """Probe TCP reachability of each infra service. Cheap, ~50ms total."""
    import socket
    services: dict[str, bool] = {}
    for name, (host, port) in _INFRA_PORTS.items():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        try:
            s.connect((host, port))
            services[name] = True
        except Exception:
            services[name] = False
        finally:
            s.close()
    return {"services": services}


# ── Voice (Sprint 7 — real local backends) ────────────────────────────────────

@router.post("/cipher/voice/transcribe")
async def voice_transcribe(request: Request) -> dict:
    """STT via faster-whisper (lazy import).

    POST the raw audio bytes (webm/opus/wav/mp3) as the request body with
    Content-Type: application/octet-stream. Avoids the python-multipart dep.
    """
    from cipher.interfaces.web.voice import transcribe, VoiceBackendUnavailable

    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty body — POST raw audio bytes.")
    try:
        return transcribe(data)
    except VoiceBackendUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")


@router.post("/cipher/voice/speak")
async def voice_speak(body: dict[str, Any]) -> dict:
    """TTS via pyttsx3. Body: {text: str}. Synthesizes on the host's speaker."""
    from cipher.interfaces.web.voice import speak, VoiceBackendUnavailable

    text = (body or {}).get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Body must contain non-empty 'text'.")
    try:
        return speak(text)
    except VoiceBackendUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")


# ── SSE event stream ──────────────────────────────────────────────────────────

@router.get("/events/sse")
async def events_sse() -> StreamingResponse:
    bridge = get_event_bridge()
    bridge.attach_loop(asyncio.get_running_loop())
    queue = bridge.subscribe()

    async def gen():
        try:
            # Initial hello so the client knows the stream is live.
            yield 'event: hello\ndata: {"ok":true}\n\n'
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        finally:
            bridge.unsubscribe(queue)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wire_orchestrator_callbacks(orch: Any, bridge, run_id: str) -> None:
    """Attach non-Qt callbacks so DevNex orchestrator publishes to EventBridge."""
    orch.on_log = lambda msg, lvl="INFO": bridge.emit_log(msg, level=lvl, run_id=run_id)
    orch.on_node_started = lambda nid: bridge.emit_node_started(nid, run_id=run_id)
    orch.on_node_complete = lambda res: bridge.emit_node_complete(
        getattr(res, "node_id", "?"), res, run_id=run_id
    )

    def _human_review(node_id: str, message: str) -> bool:
        ev = threading.Event()
        _review_events[run_id] = ev
        bridge.emit_review_needed(node_id, message, run_id=run_id)
        ev.wait()
        approved = _review_decisions.pop(run_id, False)
        _review_events.pop(run_id, None)
        return approved

    orch.on_human_review = _human_review
