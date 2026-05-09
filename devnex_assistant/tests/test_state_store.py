# tests/test_state_store.py
from pathlib import Path

import pytest

from persistence.state_store import StateStore


def test_set_and_get_node_status(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "workflow_state.json")
    store.set_node_status("S1N1", "complete")
    statuses = store.get_node_statuses()
    assert statuses["S1N1"] == "complete"


def test_multiple_nodes(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "workflow_state.json")
    store.set_node_status("S1N1", "complete")
    store.set_node_status("S1N2", "waiting")
    store.set_node_status("S2N1", "error")
    statuses = store.get_node_statuses()
    assert statuses["S1N1"] == "complete"
    assert statuses["S1N2"] == "waiting"
    assert statuses["S2N1"] == "error"


def test_reset_clears_all(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "workflow_state.json")
    store.set_node_status("S1N1", "complete")
    store.set_node_status("S9N1", "complete")
    store.reset()
    statuses = store.get_node_statuses()
    assert statuses == {}


def test_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "workflow_state.json"
    store1 = StateStore(path=path)
    store1.set_node_status("S3N1", "done")

    store2 = StateStore(path=path)
    statuses = store2.get_node_statuses()
    assert statuses["S3N1"] == "done"


def test_load_returns_empty_when_file_missing(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "no_such_file.json")
    assert store.get_node_statuses() == {}
