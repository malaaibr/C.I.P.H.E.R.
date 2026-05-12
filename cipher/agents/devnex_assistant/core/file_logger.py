"""DevNex file logger — tees sys.stdout to a plain-text log file.

Usage
-----
Call ``setup_file_logging()`` once at process startup (main_gui.py / devnex.py).
Every subsequent ``print()`` — including all ``_trace()`` calls in the
orchestrator, GCA invoker, and review orchestrator — is captured automatically.

Log file location
-----------------
  <log_dir>/devnex_<YYYYMMDD_HHMMSS>.log        (timestamped, one per run)
  <log_dir>/devnex_latest.log                     (symlink / copy of latest)

The file contains the same structured format as the console but with ANSI
escape sequences stripped:
  [2026-05-12T21:05:38Z][DevNexOrchestrator][run_node][INFO] Starting S1N1.
"""

from __future__ import annotations

import io
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ANSI_RE = re.compile(r"\033\[[0-9;]*[A-Za-z]")

_DEFAULT_LOG_DIR = Path("generated_artifacts") / "logs"


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class _TeeStream(io.TextIOBase):
    """
    Wraps the original sys.stdout so every write goes to:
      1. The original terminal stream (unchanged, with ANSI colors).
      2. The log file (ANSI stripped, plain text).
    """

    def __init__(self, original: io.TextIOBase, log_file: io.TextIOWrapper) -> None:
        super().__init__()
        self._original = original
        self._log_file  = log_file

    # ── io.TextIOBase interface ───────────────────────────────────────────────

    def write(self, text: str) -> int:
        # Write to terminal as-is
        try:
            self._original.write(text)
            self._original.flush()
        except Exception:
            pass

        # Write stripped text to log file
        clean = _strip_ansi(text)
        if clean:
            try:
                self._log_file.write(clean)
                self._log_file.flush()
            except Exception:
                pass

        return len(text)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass
        try:
            self._log_file.flush()
        except Exception:
            pass

    @property
    def encoding(self) -> str:
        return getattr(self._original, "encoding", "utf-8") or "utf-8"

    @property
    def errors(self) -> str:
        return getattr(self._original, "errors", "replace") or "replace"

    def isatty(self) -> bool:
        return getattr(self._original, "isatty", lambda: False)()

    def fileno(self) -> int:
        return self._original.fileno()


# ── Public API ────────────────────────────────────────────────────────────────

_active_log_file: io.TextIOWrapper | None = None
_active_log_path: Path | None = None


def setup_file_logging(log_dir: Path | str | None = None) -> Path:
    """
    Install the stdout tee and open the session log file.

    Safe to call multiple times — subsequent calls are no-ops.

    Returns the path to the active log file.
    """
    global _active_log_file, _active_log_path

    if _active_log_file is not None:
        return _active_log_path  # type: ignore[return-value]

    target_dir = Path(log_dir) if log_dir else _DEFAULT_LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    ts         = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path   = target_dir / f"devnex_{ts}.log"
    latest_path= target_dir / "devnex_latest.log"

    log_file = open(log_path, "w", encoding="utf-8", buffering=1)  # line-buffered

    # Write session header
    session_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_file.write(
        f"{'=' * 72}\n"
        f"DevNex Session Log  —  started {session_ts}\n"
        f"{'=' * 72}\n"
    )
    log_file.flush()

    # Tee stdout
    original_stdout = sys.stdout
    sys.stdout = _TeeStream(original_stdout, log_file)  # type: ignore[assignment]

    # Keep a symlink/copy at devnex_latest.log for easy access
    try:
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        # Try symlink first; fall back to a plain file reference note
        try:
            os.symlink(log_path.name, latest_path)
        except (OSError, NotImplementedError):
            latest_path.write_text(
                f"Latest log: {log_path.name}\n", encoding="utf-8"
            )
    except Exception:
        pass

    _active_log_file = log_file
    _active_log_path = log_path
    return log_path


def get_log_path() -> Path | None:
    """Return the path of the currently active log file, or None."""
    return _active_log_path


def close_file_logging() -> None:
    """Flush and close the log file (call on clean shutdown)."""
    global _active_log_file
    if _active_log_file is not None:
        try:
            _active_log_file.flush()
            _active_log_file.close()
        except Exception:
            pass
        _active_log_file = None
