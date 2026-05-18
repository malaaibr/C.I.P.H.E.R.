"""
MemoryAgent (E-014) — context-gap detection over MKF.

Given a PromptContract's evidence list, the MemoryAgent reports which URIs
were resolvable in MKF and which are *gaps* — missing artifacts that would
make the upcoming CRC fail WF₂ (URI resolution). Gaps are handed to the
ResearchAgent, which proposes new evidence URIs to attach.

This is a thin v1: in-memory MKF stand-in. A real backend (Memgraph / Qdrant)
plugs in by replacing `MkfClient` with the corresponding adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class MkfClient(Protocol):
    def has(self, uri: str) -> bool: ...
    def list_for_node(self, node_id: str) -> list[str]: ...


class InMemoryMkf:
    """Default MKF stand-in keyed by uri prefix → set of uris present."""

    def __init__(self, known: set[str] | None = None) -> None:
        self._known: set[str] = set(known or ())

    def add(self, uri: str) -> None:
        self._known.add(uri)

    def has(self, uri: str) -> bool:
        return uri in self._known

    def list_for_node(self, node_id: str) -> list[str]:
        return [u for u in self._known if node_id.lower() in u.lower()]


@dataclass
class ContextGapReport:
    node_id: str
    requested: list[str]
    resolved: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def has_gaps(self) -> bool:
        return bool(self.gaps)


class MemoryAgent:
    """Detect context gaps in an upcoming CRC's evidence set."""

    def __init__(self, mkf: MkfClient | None = None) -> None:
        self._mkf: MkfClient = mkf or build_default_mkf()

    def check(self, node_id: str, evidence_uris: list[str]) -> ContextGapReport:
        resolved = [u for u in evidence_uris if self._mkf.has(u)]
        gaps = [u for u in evidence_uris if not self._mkf.has(u)]
        return ContextGapReport(
            node_id=node_id, requested=evidence_uris, resolved=resolved, gaps=gaps,
        )


def build_default_mkf() -> MkfClient:
    """
    Strategy: prefer real Memgraph when reachable; else fall back to in-memory.

    The fallback keeps unit tests, CI, and offline development functional
    without requiring Docker to be up.
    """
    try:
        from cipher.agents.memory_agent.memgraph_mkf import (
            MemgraphMkf, memgraph_reachable,
        )
        if memgraph_reachable():
            return MemgraphMkf()
    except Exception:
        pass
    return InMemoryMkf()
