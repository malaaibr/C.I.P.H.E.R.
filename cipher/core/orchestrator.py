"""
CipherOrchestrator — Mother orchestrator node.

Coordinates child orchestrators (DevNex, future agents) and
provides unified access to infrastructure (LLM Gateway, A2A, voice).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class CipherOrchestrator:
    """
    Top-level orchestrator — owns child orchestrators and shared resources.

    Children:
      - DevNexOrchestrator (V-Cycle pipeline)
      - GCA Invoker (VS Code bridge)
      - Voice Controller (TTS/STT)
      - Future agent orchestrators
    """

    def __init__(self) -> None:
        self._children: dict[str, Any] = {}
        self._llm_gateway_url = "http://127.0.0.1:8200"
        self._a2a_url = "http://127.0.0.1:8100"
        self._running = False
        log.info("CipherOrchestrator initialized")

    @property
    def llm_gateway_url(self) -> str:
        return self._llm_gateway_url

    @property
    def a2a_url(self) -> str:
        return self._a2a_url

    def register_child(self, name: str, orchestrator: Any) -> None:
        """Register a child orchestrator (e.g. 'devnex', 'review')."""
        self._children[name] = orchestrator
        log.info("Registered child orchestrator: %s", name)

    def get_child(self, name: str) -> Any | None:
        return self._children.get(name)

    @property
    def devnex(self) -> Any | None:
        return self._children.get("devnex")

    async def start(self) -> None:
        """Initialize all child orchestrators."""
        self._running = True
        log.info("CipherOrchestrator started — %d children", len(self._children))

    async def stop(self) -> None:
        """Gracefully shut down children."""
        self._running = False
        log.info("CipherOrchestrator stopped")

    @property
    def is_running(self) -> bool:
        return self._running
