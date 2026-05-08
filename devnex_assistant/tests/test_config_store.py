# tests/test_config_store.py
from pathlib import Path

import pytest

from persistence.config_store import ConfigStore


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(path=tmp_path / "config.json")
    data = {"SWC_name": "TSYN", "workspace_path": "/tmp/work"}
    store.save(data)
    loaded = store.load()
    assert loaded["SWC_name"] == "TSYN"
    assert loaded["workspace_path"] == "/tmp/work"


def test_load_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    store = ConfigStore(path=tmp_path / "nonexistent.json")
    config = store.load()
    assert isinstance(config, dict)
    assert "SWC_name" in config


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    store = ConfigStore(path=tmp_path / "deep" / "nested" / "config.json")
    store.save({"SWC_name": "X"})
    assert (tmp_path / "deep" / "nested" / "config.json").exists()


def test_partial_save_preserves_other_keys(tmp_path: Path) -> None:
    store = ConfigStore(path=tmp_path / "config.json")
    store.save({"SWC_name": "A", "workspace_path": "/x"})
    store.save({"SWC_name": "B", "workspace_path": "/x"})
    loaded = store.load()
    assert loaded["SWC_name"] == "B"
