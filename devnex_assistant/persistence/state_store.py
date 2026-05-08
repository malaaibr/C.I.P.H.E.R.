"""Workflow state persistence — load/save workflow_state.json."""

from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = Path.home() / ".devnex" / "workflow_state.json"


class StateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or STATE_FILE

    def load(self) -> dict:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def save(self, state: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def set_node_status(self, node_id: str, status: str) -> None:
        state = self.load()
        state.setdefault("node_statuses", {})[node_id] = status
        self.save(state)

    def get_node_statuses(self) -> dict[str, str]:
        return self.load().get("node_statuses", {})

    def reset(self) -> None:
        self.save({})
