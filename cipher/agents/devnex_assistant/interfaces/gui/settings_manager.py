"""JSON-based settings manager for DevNex GUI — copied from Int_Agent SettingsManager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsManager:
    """Persist GUI settings in ~/.devnex/gui_settings.json."""

    KEY_WINDOW_GEOMETRY   = "window/geometry"
    KEY_WINDOW_STATE      = "window/state"
    KEY_LAST_WORKSPACE    = "run/last_workspace"
    KEY_SIDEBAR_COLLAPSED = "window/sidebar_collapsed"
    KEY_THEME             = "appearance/theme"
    KEY_FONT_SIZE         = "appearance/font_size"
    KEY_RUN_STORAGE_DIR   = "paths/run_storage"
    KEY_LOG_DIR           = "paths/log_dir"
    KEY_DEBUG_LOGGING     = "advanced/debug_logging"

    def __init__(self) -> None:
        self._settings_path = Path.home() / ".devnex" / "gui_settings.json"
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._settings_path.exists():
                raw = self._settings_path.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    self._data = loaded
        except Exception:
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def value(self, key: str, default: Any = None) -> Any:
        return self.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def set_value(self, key: str, value: Any) -> None:
        self.set(key, value)

    def save(self) -> None:
        try:
            self._settings_path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def save_window_state(self, geometry: Any, state: Any) -> None:  # noqa: ARG002
        pass

    def load_window_geometry(self) -> None:
        return None

    def load_window_state(self) -> None:
        return None
