"""SWC project configuration persistence — load/save config.json."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_FILE = Path("generated_artifacts") / "config.json"

DEFAULT_CONFIG: dict = {
    "SWC_name":             "",
    "G_SWDD_TEMP":          "",
    "SWC_name_C":           "",
    "SWC_name_H":           "",
    "SWC_name_TEMP_LLD":    "",
    "SWC_name_FUNC_req":    "",
    "SWC_nameInspBaseLLD":  "",
    "SWC_name_HLD":         "",
    "Linker File":          "",
    "map_file":             "",
    "workspace_path":       ".",
}


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or CONFIG_FILE

    def load(self) -> dict:
        if self._path.exists():
            try:
                loaded = json.loads(self._path.read_text(encoding="utf-8"))
                return {**DEFAULT_CONFIG, **loaded}
            except json.JSONDecodeError:
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def save(self, config: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
