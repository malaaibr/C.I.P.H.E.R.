"""Unit tests for core.trace_model and core.trace_loader.

Run with:  pytest tests/test_trace_model.py -v
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

import pytest

from core.trace_model import NodeKind, TraceEdge, TraceGraph, TraceNode
from core.trace_loader import load_trace_graph, emit_trace_json


# ── TraceGraph / TraceNode / TraceEdge ────────────────────────────────────────

class TestTraceModel:
    def test_node_kind_values(self) -> None:
        assert NodeKind.HLD.value  == "HLD"
        assert NodeKind.LLD.value  == "LLD"
        assert NodeKind.CODE.value == "CODE"
        assert NodeKind.TEST.value == "TEST"
        assert NodeKind.UTD.value  == "UTD"

    def test_node_kind_from_string(self) -> None:
        assert NodeKind("CODE") == NodeKind.CODE

    def test_by_kind_filters_correctly(self) -> None:
        graph = TraceGraph(
            nodes=[
                TraceNode(id="H1", kind=NodeKind.HLD,  label="H1"),
                TraceNode(id="L1", kind=NodeKind.LLD,  label="L1"),
                TraceNode(id="H2", kind=NodeKind.HLD,  label="H2"),
            ]
        )
        hld_nodes = graph.by_kind(NodeKind.HLD)
        assert len(hld_nodes) == 2
        assert all(n.kind == NodeKind.HLD for n in hld_nodes)

    def test_by_kind_returns_empty_for_missing_column(self) -> None:
        graph = TraceGraph(nodes=[TraceNode(id="H1", kind=NodeKind.HLD, label="H1")])
        assert graph.by_kind(NodeKind.UTD) == []

    def test_neighbors_both_directions(self) -> None:
        graph = TraceGraph(
            nodes=[
                TraceNode(id="H1", kind=NodeKind.HLD,  label="H1"),
                TraceNode(id="L1", kind=NodeKind.LLD,  label="L1"),
                TraceNode(id="L2", kind=NodeKind.LLD,  label="L2"),
            ],
            edges=[
                TraceEdge(source_id="H1", target_id="L1"),
                TraceEdge(source_id="H1", target_id="L2"),
            ],
        )
        assert set(graph.neighbors("H1")) == {"L1", "L2"}
        assert "H1" in graph.neighbors("L1")

    def test_neighbors_isolated_node(self) -> None:
        graph = TraceGraph(nodes=[TraceNode(id="X", kind=NodeKind.CODE, label="X")])
        assert graph.neighbors("X") == []


# ── JSON round-trip ───────────────────────────────────────────────────────────

class TestJsonRoundTrip:
    def _make_graph(self) -> TraceGraph:
        return TraceGraph(
            nodes=[
                TraceNode(
                    id="HLD-001", kind=NodeKind.HLD, label="HLD-001",
                    sublabel="HLD REQ", title="Init torque syncing",
                    source_file="src/foo.c", line_no=42, asil="B",
                    metadata={"owner": "alice"},
                ),
                TraceNode(id="LLD-001", kind=NodeKind.LLD, label="LLD-001"),
            ],
            edges=[
                TraceEdge(source_id="HLD-001", target_id="LLD-001", kind="covers", confidence=0.9),
            ],
        )

    def test_to_json_structure(self) -> None:
        graph = self._make_graph()
        data  = graph.to_json()
        assert "nodes" in data and "edges" in data
        assert data["nodes"][0]["kind"] == "HLD"

    def test_from_json_identity(self) -> None:
        original = self._make_graph()
        restored = TraceGraph.from_json(original.to_json())

        assert len(restored.nodes) == len(original.nodes)
        assert len(restored.edges) == len(original.edges)

        n0 = restored.nodes[0]
        assert n0.id         == "HLD-001"
        assert n0.kind       == NodeKind.HLD
        assert n0.asil       == "B"
        assert n0.line_no    == 42
        assert n0.metadata   == {"owner": "alice"}

    def test_edge_confidence_preserved(self) -> None:
        original = self._make_graph()
        restored = TraceGraph.from_json(original.to_json())
        assert restored.edges[0].confidence == pytest.approx(0.9)

    def test_from_json_missing_keys_returns_empty(self) -> None:
        graph = TraceGraph.from_json({})
        assert graph.nodes == []
        assert graph.edges == []


# ── CSV → TraceGraph ──────────────────────────────────────────────────────────

class TestCsvLoading:
    def _write_csv(self, path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_hld_lld_happy_path(self, tmp_path: Path) -> None:
        self._write_csv(
            tmp_path / "HLD_LLD_Trace_Matrix.csv",
            rows=[
                {"HLD_ID": "HLD-001", "HLD_TITLE": "Init", "LLD_ID": "LLD-001", "LLD_TITLE": "Buf init", "LINK_TYPE": "covers", "CONFIDENCE": "1.0"},
                {"HLD_ID": "HLD-002", "HLD_TITLE": "Sync", "LLD_ID": "LLD-002", "LLD_TITLE": "Sync buf",  "LINK_TYPE": "covers", "CONFIDENCE": "0.8"},
            ],
            fieldnames=["HLD_ID", "HLD_TITLE", "LLD_ID", "LLD_TITLE", "LINK_TYPE", "CONFIDENCE"],
        )
        graph = load_trace_graph(tmp_path)
        assert len(graph.by_kind(NodeKind.HLD)) == 2
        assert len(graph.by_kind(NodeKind.LLD)) == 2
        assert len(graph.edges) == 2

    def test_multiple_csv_files(self, tmp_path: Path) -> None:
        self._write_csv(
            tmp_path / "HLD_LLD_Trace_Matrix.csv",
            rows=[{"HLD_ID": "H1", "HLD_TITLE": "", "LLD_ID": "L1", "LLD_TITLE": "", "LINK_TYPE": "link", "CONFIDENCE": "1.0"}],
            fieldnames=["HLD_ID", "HLD_TITLE", "LLD_ID", "LLD_TITLE", "LINK_TYPE", "CONFIDENCE"],
        )
        self._write_csv(
            tmp_path / "LLD_Code_Trace_Matrix.csv",
            rows=[{"LLD_ID": "L1", "LLD_TITLE": "", "CODE_ID": "C1", "CODE_TITLE": "", "LINK_TYPE": "link", "CONFIDENCE": "1.0"}],
            fieldnames=["LLD_ID", "LLD_TITLE", "CODE_ID", "CODE_TITLE", "LINK_TYPE", "CONFIDENCE"],
        )
        graph = load_trace_graph(tmp_path)
        # L1 deduped — appears in both CSVs
        lld_ids = [n.id for n in graph.by_kind(NodeKind.LLD)]
        assert lld_ids.count("L1") == 1
        assert len(graph.by_kind(NodeKind.CODE)) == 1

    def test_missing_files_returns_empty_graph(self, tmp_path: Path) -> None:
        graph = load_trace_graph(tmp_path)
        assert graph.nodes == []
        assert graph.edges == []

    def test_malformed_row_skipped_logged(self, tmp_path: Path, caplog) -> None:
        csv_path = tmp_path / "HLD_LLD_Trace_Matrix.csv"
        csv_path.write_text(
            "HLD_ID,HLD_TITLE,LLD_ID,LLD_TITLE,LINK_TYPE,CONFIDENCE\n"
            ",empty-hld-id,LLD-001,title,link,1.0\n"   # empty HLD_ID → skip
            "HLD-001,good,LLD-002,title,link,1.0\n",
            encoding="utf-8",
        )
        with caplog.at_level(logging.WARNING):
            graph = load_trace_graph(tmp_path)
        # Only the valid row produces nodes
        assert len(graph.by_kind(NodeKind.HLD)) == 1
        assert any("empty" in r.message.lower() or "skip" in r.message.lower() for r in caplog.records)

    def test_extra_csv_columns_ignored(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "HLD_LLD_Trace_Matrix.csv"
        csv_path.write_text(
            "HLD_ID,HLD_TITLE,LLD_ID,LLD_TITLE,LINK_TYPE,CONFIDENCE,EXTRA_COL\n"
            "H1,title,L1,title,link,1.0,ignored\n",
            encoding="utf-8",
        )
        graph = load_trace_graph(tmp_path)
        assert len(graph.nodes) == 2

    def test_trace_json_preferred_over_csv(self, tmp_path: Path) -> None:
        # Write a CSV with 1 node pair
        self._write_csv(
            tmp_path / "HLD_LLD_Trace_Matrix.csv",
            rows=[{"HLD_ID": "H1", "HLD_TITLE": "", "LLD_ID": "L1", "LLD_TITLE": "", "LINK_TYPE": "link", "CONFIDENCE": "1.0"}],
            fieldnames=["HLD_ID", "HLD_TITLE", "LLD_ID", "LLD_TITLE", "LINK_TYPE", "CONFIDENCE"],
        )
        # Write a trace_graph.json with 3 nodes
        json_graph = TraceGraph(
            nodes=[
                TraceNode(id="X1", kind=NodeKind.CODE, label="X1"),
                TraceNode(id="X2", kind=NodeKind.TEST, label="X2"),
                TraceNode(id="X3", kind=NodeKind.UTD,  label="X3"),
            ]
        )
        (tmp_path / "trace_graph.json").write_text(
            json.dumps(json_graph.to_json()), encoding="utf-8"
        )
        graph = load_trace_graph(tmp_path)
        # JSON wins — 3 nodes, not 2 from CSV
        assert len(graph.nodes) == 3

    def test_utd_links_json(self, tmp_path: Path) -> None:
        utd_data = {
            "links": [
                {"utd_id": "UTD-001", "lld_id": "L1", "test_id": "T1"},
            ]
        }
        (tmp_path / "UTD_LLD_Links.json").write_text(json.dumps(utd_data), encoding="utf-8")
        graph = load_trace_graph(tmp_path)
        assert any(n.kind == NodeKind.UTD  for n in graph.nodes)
        assert any(n.kind == NodeKind.TEST for n in graph.nodes)
        assert any(e.kind == "verifies" for e in graph.edges)
        assert any(e.kind == "covers"   for e in graph.edges)


# ── emit_trace_json ───────────────────────────────────────────────────────────

class TestEmitTraceJson:
    def test_creates_file(self, tmp_path: Path) -> None:
        emit_trace_json(tmp_path)
        assert (tmp_path / "trace_graph.json").exists()

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        emit_trace_json(tmp_path)
        data = json.loads((tmp_path / "trace_graph.json").read_text(encoding="utf-8"))
        assert "nodes" in data
        assert "edges" in data

    def test_roundtrip_from_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "HLD_LLD_Trace_Matrix.csv"
        csv_path.write_text(
            "HLD_ID,HLD_TITLE,LLD_ID,LLD_TITLE,LINK_TYPE,CONFIDENCE\n"
            "H1,title,L1,title,link,1.0\n",
            encoding="utf-8",
        )
        path = emit_trace_json(tmp_path)
        graph = TraceGraph.from_json(json.loads(path.read_text(encoding="utf-8")))
        assert len(graph.nodes) == 2
