"""trace_loader — builds a TraceGraph from CSV / JSON artifact files.

Preference order when loading:
  1. ``trace_graph.json``  — skill-emitted, authoritative source of truth
  2. Individual CSV files  — HLD_LLD_Trace_Matrix.csv, LLD_Code_Trace_Matrix.csv,
                             Full_Downstream_Trace.csv + UTD_LLD_Links.json

Always returns a valid (possibly empty) TraceGraph — never raises.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Set, Tuple

from core.trace_model import NodeKind, TraceEdge, TraceGraph, TraceNode

log = logging.getLogger(__name__)

# Maps filename → (src_kind, tgt_kind, src_id_col, src_title_col, tgt_id_col, tgt_title_col)
_CSV_MAP: dict[str, tuple] = {
    "HLD_LLD_Trace_Matrix.csv": (
        NodeKind.HLD, NodeKind.LLD,
        "HLD_ID", "HLD_TITLE", "LLD_ID", "LLD_TITLE",
    ),
    "LLD_Code_Trace_Matrix.csv": (
        NodeKind.LLD, NodeKind.CODE,
        "LLD_ID", "LLD_TITLE", "CODE_ID", "CODE_TITLE",
    ),
    "Full_Downstream_Trace.csv": (
        NodeKind.CODE, NodeKind.TEST,
        "CODE_ID", "CODE_TITLE", "TEST_ID", "TEST_TITLE",
    ),
}

_EdgeKey = Tuple[str, str, str]


def load_trace_graph(artifacts_dir: Path) -> TraceGraph:
    """
    Build a TraceGraph from artifact files inside *artifacts_dir*.

    Returns an empty TraceGraph when no artifacts are found.
    """
    artifacts_dir = Path(artifacts_dir)

    trace_json = artifacts_dir / "trace_graph.json"
    if trace_json.exists():
        try:
            data = json.loads(trace_json.read_text(encoding="utf-8"))
            graph = TraceGraph.from_json(data)
            log.info(
                "Loaded trace_graph.json — %d nodes / %d edges",
                len(graph.nodes), len(graph.edges),
            )
            return graph
        except Exception as exc:  # noqa: BLE001
            log.warning("trace_graph.json parse failed: %s — falling back to CSVs", exc)

    return _build_from_csvs(artifacts_dir)


def _node_key(kind: NodeKind, node_id: str) -> str:
    return f"{kind.value}::{node_id}"


def _build_from_csvs(artifacts_dir: Path) -> TraceGraph:
    nodes:      Dict[str, TraceNode]      = {}
    seen_edges: Set[_EdgeKey]             = set()
    edge_list:  list[TraceEdge]           = []

    def _upsert_node(kind: NodeKind, node_id: str, title: str) -> None:
        key = _node_key(kind, node_id)
        if key not in nodes:
            nodes[key] = TraceNode(
                id=node_id,
                kind=kind,
                label=node_id,
                sublabel=f"{kind.value} REQ",
                title=title,
            )

    def _upsert_edge(src_id: str, tgt_id: str, kind: str = "link", confidence: float = 1.0) -> None:
        key: _EdgeKey = (src_id, tgt_id, kind)
        if key not in seen_edges:
            seen_edges.add(key)
            edge_list.append(TraceEdge(source_id=src_id, target_id=tgt_id, kind=kind, confidence=confidence))

    for filename, (src_kind, tgt_kind, src_id_col, src_title_col, tgt_id_col, tgt_title_col) in _CSV_MAP.items():
        path = artifacts_dir / filename
        if not path.exists():
            log.debug("Artifact not found, skipping: %s", path)
            continue
        try:
            with path.open(encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row_num, row in enumerate(reader, start=1):
                    try:
                        src_id = (row.get(src_id_col) or "").strip()
                        tgt_id = (row.get(tgt_id_col) or "").strip()
                        if not src_id or not tgt_id:
                            log.warning("%s row %d: empty ID — skipping", filename, row_num)
                            continue
                        link_type  = (row.get("LINK_TYPE") or "link").strip() or "link"
                        try:
                            confidence = float(row.get("CONFIDENCE") or "1.0")
                        except ValueError:
                            confidence = 1.0
                        _upsert_node(src_kind, src_id, (row.get(src_title_col) or ""))
                        _upsert_node(tgt_kind, tgt_id, (row.get(tgt_title_col) or ""))
                        _upsert_edge(src_id, tgt_id, link_type, confidence)
                    except Exception as row_exc:  # noqa: BLE001
                        log.warning("%s row %d: %s — skipping", filename, row_num, row_exc)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to read %s: %s", path, exc)

    _load_utd_links(artifacts_dir, nodes, seen_edges, edge_list)

    graph = TraceGraph(nodes=list(nodes.values()), edges=edge_list)
    log.info(
        "Built TraceGraph from CSVs — %d nodes / %d edges",
        len(graph.nodes), len(graph.edges),
    )
    return graph


def _load_utd_links(
    artifacts_dir: Path,
    nodes:      Dict[str, TraceNode],
    seen_edges: Set[_EdgeKey],
    edge_list:  list[TraceEdge],
) -> None:
    """Merge UTD_LLD_Links.json into the in-progress node/edge collections."""
    path = artifacts_dir / "UTD_LLD_Links.json"
    if not path.exists():
        return
    try:
        data  = json.loads(path.read_text(encoding="utf-8"))
        links = data if isinstance(data, list) else data.get("links", [])
        for item in links:
            utd_id  = str(item.get("utd_id",  item.get("UTD_ID",  ""))).strip()
            lld_id  = str(item.get("lld_id",  item.get("LLD_ID",  ""))).strip()
            test_id = str(item.get("test_id", item.get("TEST_ID", ""))).strip()
            if not utd_id:
                continue

            utd_key = _node_key(NodeKind.UTD, utd_id)
            if utd_key not in nodes:
                nodes[utd_key] = TraceNode(id=utd_id, kind=NodeKind.UTD, label=utd_id, sublabel="UTD DOC")

            if lld_id:
                lld_key = _node_key(NodeKind.LLD, lld_id)
                if lld_key not in nodes:
                    nodes[lld_key] = TraceNode(id=lld_id, kind=NodeKind.LLD, label=lld_id, sublabel="LLD REQ")
                edge_key: _EdgeKey = (utd_id, lld_id, "verifies")
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edge_list.append(TraceEdge(source_id=utd_id, target_id=lld_id, kind="verifies"))

            if test_id:
                test_key = _node_key(NodeKind.TEST, test_id)
                if test_key not in nodes:
                    nodes[test_key] = TraceNode(id=test_id, kind=NodeKind.TEST, label=test_id, sublabel="TEST CASE")
                edge_key = (test_id, utd_id, "covers")
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edge_list.append(TraceEdge(source_id=test_id, target_id=utd_id, kind="covers"))
    except Exception as exc:  # noqa: BLE001
        log.warning("UTD_LLD_Links.json parse failed: %s", exc)


def emit_trace_json(artifacts_dir: Path) -> Path:
    """
    Build the current TraceGraph from CSVs and write ``trace_graph.json``.

    Uses atomic temp-file + rename so readers never see a partial write.
    Returns the path of the written file.
    """
    import tempfile, os
    graph      = _build_from_csvs(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    target     = artifacts_dir / "trace_graph.json"
    tmp_fd, tmp_path = tempfile.mkstemp(dir=artifacts_dir, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(graph.to_json(), fh, indent=2)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    log.info("Emitted %s (%d nodes, %d edges)", target, len(graph.nodes), len(graph.edges))
    return target
