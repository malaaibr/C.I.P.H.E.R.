"""Console log formatting helpers with ANSI colors for better debugging visibility."""

from __future__ import annotations

import os
import re
import sys
import ctypes
from datetime import UTC, datetime


ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"


QUOTED_PATH_PATTERN = re.compile(r"'([^']*[\\/][^']*)'")


def _try_enable_windows_vt_mode() -> bool:
    """
    @brief Enable ANSI escape support for Windows console handles when possible.

    @return `True` when ANSI virtual terminal mode is available.
    """
    if os.name != "nt":
        return True
    kernel32 = getattr(ctypes, "windll", None)
    if kernel32 is None:
        return False
    try:
        handle = kernel32.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        if handle in (0, -1):
            return False
        mode = ctypes.c_uint32()
        if kernel32.kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if kernel32.kernel32.SetConsoleMode(handle, mode.value | 0x0004) == 0:
            return False
        return True
    except Exception:
        return False


def _supports_color() -> bool:
    """
    @brief Determine whether ANSI color output should be enabled.

    @return `True` when colored output is supported and not disabled.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not bool(getattr(sys.stdout, "isatty", lambda: False)()):
        return False
    return _try_enable_windows_vt_mode()


def _colorize_path_segments(message: str, enable_color: bool) -> str:
    """
    @brief Apply color highlighting to quoted path-like segments.

    @param message Raw log message text.
    @param enable_color Flag indicating whether color is enabled.

    @return Message with path segments colorized when enabled.
    """
    if not enable_color:
        return message

    def _replace_path(match: re.Match[str]) -> str:
        quoted_path = match.group(0)
        return f"{ANSI_BLUE}{quoted_path}{ANSI_RESET}"

    return QUOTED_PATH_PATTERN.sub(_replace_path, message)


def _level_color(level: str) -> str:
    """
    @brief Map log levels to ANSI color codes.

    @param level Log level name.

    @return ANSI color escape sequence for the level.
    """
    normalized_level = level.upper()
    if normalized_level == "ERROR":
        return ANSI_RED
    if normalized_level == "WARN":
        return ANSI_YELLOW
    if normalized_level == "SUCCESS":
        return ANSI_GREEN
    return ANSI_CYAN


def utc_timestamp() -> str:
    """
    @brief Build UTC timestamp for log-line prefixes.

    @return UTC timestamp in `%Y-%m-%dT%H:%M:%SZ` format.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_console_log(
    module_name: str,
    level: str,
    message: str,
    timestamp: str | None = None,
    function_name: str | None = None,
) -> str:
    """
    @brief Build a structured console log line.

    @param module_name Logical module emitting the log line.
    @param level Log severity text.
    @param message Human-readable log message.
    @param timestamp Optional precomputed timestamp.
    @param function_name Optional function name for call-site tracing.

    @return Fully formatted console log line.
    """
    effective_timestamp = timestamp or utc_timestamp()
    enable_color = _supports_color()
    level_text = level.upper()
    formatted_message = _colorize_path_segments(message, enable_color=enable_color)
    normalized_function_name = function_name.strip() if function_name else None
    function_segment_plain = f"[{normalized_function_name}]" if normalized_function_name else ""
    if not enable_color:
        return f"[{effective_timestamp}][{module_name}]{function_segment_plain}[{level_text}] {formatted_message}"
    level_segment = f"{_level_color(level_text)}[{level_text}]{ANSI_RESET}"
    timestamp_segment = f"{ANSI_CYAN}[{effective_timestamp}]{ANSI_RESET}"
    module_segment = f"{ANSI_BOLD}{ANSI_MAGENTA}[{module_name}]{ANSI_RESET}"
    function_segment = (
        f"{ANSI_BOLD}{ANSI_BLUE}[{normalized_function_name}]{ANSI_RESET}" if normalized_function_name else ""
    )
    return f"{timestamp_segment}{module_segment}{function_segment}{level_segment} {formatted_message}"
