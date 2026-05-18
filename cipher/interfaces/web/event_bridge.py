"""
EventBridge — non-Qt publish/subscribe bus.

Mirrors the pyqtSignal set used by NodeWorker / FullRunWorker so the same
worker logic can drive either the PyQt6 GUI (Qt signals) or the VSCode webview
(SSE-delivered JSON envelopes), without coupling the worker to QtCore.
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class Event:
    """One event envelope, ready for SSE serialization."""
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    node_id: str | None = None
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps({
            "ts": self.ts,
            "kind": self.kind,
            "runId": self.run_id,
            "nodeId": self.node_id,
            "payload": self.payload,
        })


class EventBridge:
    """
    Thread-safe pub/sub. Producers (workers, orchestrator callbacks) call
    `publish()` from any thread; subscribers (SSE endpoint) receive via async
    queues.

    Event kinds (mirror pyqtSignal set):
      - log              payload: {message, level}
      - node.started     payload: {}
      - node.complete    payload: {result}
      - review.needed    payload: {message}
      - progress         payload: {pct, message}
      - error            payload: {message}
      - status           payload: {state}
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[asyncio.Queue[str]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind to the FastAPI event loop so cross-thread `publish` can hop in."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1024)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event: Event) -> None:
        """Broadcast to all subscribers. Safe to call from any thread."""
        msg = event.to_json()
        loop = self._loop
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._try_put, q, msg)
            else:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass

    @staticmethod
    def _try_put(q: asyncio.Queue[str], msg: str) -> None:
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass

    # Convenience helpers ----------------------------------------------------

    def emit_log(self, message: str, level: str = "INFO", run_id: str | UUID | None = None, node_id: str | None = None) -> None:
        self.publish(Event(
            kind="log",
            payload={"message": message, "level": level},
            run_id=str(run_id) if run_id else None,
            node_id=node_id,
        ))

    def emit_node_started(self, node_id: str, run_id: str | UUID | None = None) -> None:
        self.publish(Event(kind="node.started", run_id=str(run_id) if run_id else None, node_id=node_id))

    def emit_node_complete(self, node_id: str, result: Any, run_id: str | UUID | None = None) -> None:
        self.publish(Event(
            kind="node.complete",
            payload={"result": _safe_serialize(result)},
            run_id=str(run_id) if run_id else None,
            node_id=node_id,
        ))

    def emit_review_needed(self, node_id: str, message: str, run_id: str | UUID | None = None) -> None:
        self.publish(Event(
            kind="review.needed",
            payload={"message": message},
            run_id=str(run_id) if run_id else None,
            node_id=node_id,
        ))

    def emit_progress(self, pct: int, message: str, run_id: str | UUID | None = None) -> None:
        self.publish(Event(
            kind="progress",
            payload={"pct": pct, "message": message},
            run_id=str(run_id) if run_id else None,
        ))

    def emit_error(self, message: str, run_id: str | UUID | None = None, node_id: str | None = None) -> None:
        self.publish(Event(
            kind="error",
            payload={"message": message},
            run_id=str(run_id) if run_id else None,
            node_id=node_id,
        ))

    def emit_status(self, state: str, **extra: Any) -> None:
        self.publish(Event(kind="status", payload={"state": state, **extra}))


def _safe_serialize(obj: Any) -> Any:
    """Best-effort JSON-serializable dump for arbitrary worker results."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    # Pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            pass
    # dataclass
    if hasattr(obj, "__dict__"):
        try:
            return {k: _safe_serialize(v) for k, v in vars(obj).items() if not k.startswith("_")}
        except Exception:
            pass
    return repr(obj)


_bridge: EventBridge | None = None


def get_event_bridge() -> EventBridge:
    """Process-wide singleton."""
    global _bridge
    if _bridge is None:
        _bridge = EventBridge()
    return _bridge
