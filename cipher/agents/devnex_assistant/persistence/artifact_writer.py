"""Artifact writer utilities — CSV, MD, JSON output helpers."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from core.console_logging import format_console_log, utc_timestamp

MODULE_NAME = "ArtifactWriter"


class ArtifactWriter:
    """
    @brief Thin write helpers for DevNex output artifacts.
    All writes are logged via _trace().
    """

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def write_text(self, path: Path, content: str) -> None:
        """@brief Write a text file (CSV or Markdown)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._trace(f"Text artifact written → '{path}'.", level="SUCCESS")

    def write_json(self, path: Path, data: object) -> None:
        """@brief Write a JSON artifact."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._trace(f"JSON artifact written → '{path}'.", level="SUCCESS")

    def read_text(self, path: Path) -> str:
        """@brief Read a text artifact; return empty string if missing."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        self._trace(f"Artifact not found: '{path}'.", level="WARN")
        return ""
