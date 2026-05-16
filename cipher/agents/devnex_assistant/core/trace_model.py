"""TraceGraph data model — nodes, edges, and JSON serialisation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class NodeKind(str, Enum):
    """V-cycle column identifier used by TraceNode and the graph canvas."""

    HLD  = "HLD"
    LLD  = "LLD"
    CODE = "CODE"
    TEST = "TEST"
    UTD  = "UTD"


@dataclass
class TraceNode:
    """Single artifact node in the traceability graph."""

    id:          str
    kind:        NodeKind
    label:       str
    sublabel:    str             = ""
    title:       str             = ""
    source_file: str             = ""
    line_no:     int             = 0
    asil:        str             = ""
    metadata:    Dict[str, str]  = field(default_factory=dict)


@dataclass
class TraceEdge:
    """Directed link between two TraceNodes."""

    source_id:  str
    target_id:  str
    kind:       str   = "link"   # "link" | "covers" | "verifies"
    confidence: float = 1.0      # 0..1 — dim weak links


@dataclass
class TraceGraph:
    """Complete traceability graph (nodes + edges)."""

    nodes: List[TraceNode] = field(default_factory=list)
    edges: List[TraceEdge] = field(default_factory=list)

    # ── Query helpers ─────────────────────────────────────────────────────────

    def by_kind(self, kind: NodeKind) -> List[TraceNode]:
        """Return all nodes whose kind matches *kind*."""
        return [n for n in self.nodes if n.kind == kind]

    def neighbors(self, node_id: str) -> List[str]:
        """Return all neighbor IDs (both directions) for *node_id*."""
        return [
            e.target_id for e in self.edges if e.source_id == node_id
        ] + [
            e.source_id for e in self.edges if e.target_id == node_id
        ]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_json(self) -> dict:
        """Serialise to a JSON-safe dict (compatible with json.dumps)."""
        return {
            "nodes": [
                {**n.__dict__, "kind": n.kind.value}
                for n in self.nodes
            ],
            "edges": [e.__dict__ for e in self.edges],
        }

    @classmethod
    def from_json(cls, data: dict) -> "TraceGraph":
        """Deserialise from the dict produced by :meth:`to_json`."""
        nodes = [
            TraceNode(**(row | {"kind": NodeKind(row["kind"])}))
            for row in data.get("nodes", [])
        ]
        edges = [TraceEdge(**row) for row in data.get("edges", [])]
        return cls(nodes=nodes, edges=edges)
