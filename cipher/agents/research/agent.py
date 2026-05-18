"""
ResearchAgent (E-014, companion to MemoryAgent).

Given a `ContextGapReport` from MemoryAgent, propose candidate URIs that
might fill each gap. Strategies (cheapest → most expensive):

  1. Filename match in workspace_path
  2. Sibling-artifact lookup (same node_id, different artifact type)
  3. (Future) full-text retrieval via MKF/Qdrant

v1 implements (1) and (2). Real (3) plugs in when MKF retrieval is online.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cipher.agents.memory_agent.agent import ContextGapReport


@dataclass
class ResearchProposal:
    gap_uri: str
    candidates: list[str] = field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""


class ResearchAgent:
    def __init__(self, workspace_path: str | Path | None = None) -> None:
        self._workspace = Path(workspace_path) if workspace_path else None

    def propose(self, report: ContextGapReport) -> list[ResearchProposal]:
        out: list[ResearchProposal] = []
        for gap in report.gaps:
            candidates: list[str] = []
            name = gap.rsplit("/", 1)[-1].split("#", 1)[0]
            if self._workspace and self._workspace.exists():
                for p in self._workspace.rglob(name):
                    candidates.append(f"file://{p.as_posix()}")
                    if len(candidates) >= 5:
                        break
            confidence = 0.6 if candidates else 0.0
            out.append(ResearchProposal(
                gap_uri=gap,
                candidates=candidates,
                confidence=confidence,
                rationale=(
                    f"Filename '{name}' matched in workspace" if candidates else
                    "No filename match; consider MKF retrieval (offline in v1)."
                ),
            ))
        return out
