"""Workflow state persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_FILE = Path.home() / ".devnex" / "workflow_state.json"
WorkflowState = dict[str, Any]


class StateStore:
    """
    @brief JSON-backed persistence for workflow execution state.

    @details
    The current state model stores node statuses under the `node_statuses`
    dictionary. The implementation is intentionally file-based for local
    desktop and CLI usage.
    """

    def __init__(self, path: Path | None = None) -> None:
        """
        @brief Create a state store bound to one JSON file.

        @param path Optional override path used by tests.
        """
        self._path = path or STATE_FILE

    def load(self) -> WorkflowState:
        """
        @brief Load persisted workflow state.

        @return Workflow state dictionary, or an empty dict when missing/invalid.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            return {}

        try:
            loaded_state = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        return loaded_state if isinstance(loaded_state, dict) else {}

    def save(self, state: WorkflowState) -> None:
        """
        @brief Persist workflow state to disk.

        @param state Complete workflow state payload to write.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def set_node_status(self, node_id: str, status: str) -> None:
        """
        @brief Update one node status in persisted workflow state.

        @param node_id V-cycle node identifier such as `S1N1`.
        @param status New status string to store for the node.
        """
        workflow_state = self.load()
        workflow_state.setdefault("node_statuses", {})[node_id] = status
        self.save(workflow_state)

    def get_node_statuses(self) -> dict[str, str]:
        """
        @brief Return all persisted node statuses.

        @return Mapping of node IDs to status strings.
        """
        statuses = self.load().get("node_statuses", {})
        return statuses if isinstance(statuses, dict) else {}

    def reset(self) -> None:
        """@brief Clear all persisted workflow state."""
        self.save({})
