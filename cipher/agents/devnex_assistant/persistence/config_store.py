"""SWC project configuration persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILE = Path("generated_artifacts") / "config.json"
LINKER_FILE_KEY = "lds_file"
LEGACY_LINKER_FILE_KEY = "Linker File"

ConfigData = dict[str, Any]

DEFAULT_CONFIG: ConfigData = {
    "SWC_name": "",
    "G_SWDD_TEMP": "",
    "SWC_name_C": "",
    "SWC_name_H": "",
    "SWC_name_TEMP_LLD": "",
    "SWC_name_FUNC_req": "",
    "SWC_nameInspBaseLLD": "",
    "SWC_name_HLD": "",
    LINKER_FILE_KEY: "",
    "map_file": "",
    "workspace_path": ".",
}


class ConfigStore:
    """
    @brief JSON-backed store for SWC project configuration.

    @details
    The store returns a complete configuration dictionary by merging saved
    values over `DEFAULT_CONFIG`. It also normalizes older config files that
    used the display label `Linker File` as a persisted key.
    """

    def __init__(self, path: Path | None = None) -> None:
        """
        @brief Create a config store bound to one JSON file.

        @param path Optional override path used by tests or isolated callers.
        """
        self._path = path or CONFIG_FILE

    def load(self) -> ConfigData:
        """
        @brief Load configuration from disk.

        @return A config dictionary containing every key from `DEFAULT_CONFIG`.
        Missing or invalid files return defaults.
        """
        if not self._path.exists():
            return dict(DEFAULT_CONFIG)

        try:
            loaded_config = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return dict(DEFAULT_CONFIG)

        if not isinstance(loaded_config, dict):
            return dict(DEFAULT_CONFIG)

        normalized_config = self._normalize_config(loaded_config)
        return {**DEFAULT_CONFIG, **normalized_config}

    def save(self, config: ConfigData) -> None:
        """
        @brief Persist project configuration as formatted JSON.

        @param config Project configuration values keyed by internal config IDs.
        """
        normalized_config = self._normalize_config(config)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(normalized_config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_config(config: ConfigData) -> ConfigData:
        """
        @brief Convert legacy display-label keys into stable internal keys.

        @param config Raw config dictionary loaded from disk or collected from UI.
        @return A copy of the config with known legacy aliases normalized.
        """
        normalized_config = dict(config)
        legacy_value = normalized_config.pop(LEGACY_LINKER_FILE_KEY, None)
        if legacy_value is not None and not normalized_config.get(LINKER_FILE_KEY):
            normalized_config[LINKER_FILE_KEY] = legacy_value
        return normalized_config
