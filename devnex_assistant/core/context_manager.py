"""WorkingContext builder for DevNex Assistant."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Optional

from core.console_logging import format_console_log, utc_timestamp
from persistence.state_store import StateStore
from persistence.config_store import ConfigStore

MODULE_NAME = "ContextManager"


@dataclass
class WorkingContext:
    workflow_state: dict
    config:         dict
    workspace_path: str
    interface_type: str
    active_file:    Optional[str] = None
    selection:      Optional[str] = None


class ContextManager:
    def __init__(self) -> None:
        self._state_store  = StateStore()
        self._config_store = ConfigStore()

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def build(self, request) -> WorkingContext:
        """@brief Build a WorkingContext from a UserRequest and persisted state."""
        self._trace("Building WorkingContext.")
        state  = self._state_store.load()
        config = self._config_store.load()
        ctx = WorkingContext(
            workflow_state=state,
            config=config,
            workspace_path=config.get("workspace_path", "."),
            interface_type=getattr(request, "interface_type", "CLI"),
            active_file=getattr(request, "params", {}).get("file"),
            selection=getattr(request, "params", {}).get("selection"),
        )
        self._trace(f"WorkingContext built — SWC='{config.get('SWC_name', '')}'.")
        return ctx
