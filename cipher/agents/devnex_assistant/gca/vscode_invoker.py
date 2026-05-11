"""DevNex GCA Invoker — singleton VS Code / GCA WebSocket connection.

BUG FIX (serious): the original implementation created a fresh temp workspace
and launched a NEW VS Code window on every invoke_prompt() call, so each stage
opened its own instance with its own GCA connection.

New strategy
────────────
1. Probe the persisted ``_client`` — if the WebSocket is still alive, reuse it.
2. Scan ``~/.gca_instances.json`` for any already-running GCA instance with an
   open port and connect to it (no new VS Code window needed).
3. Only launch a new VS Code window when neither (1) nor (2) succeeds.
4. Hold the single connection for the lifetime of the DevNexGCAInvoker object,
   so all S1–S9 stages share the same VS Code instance.
"""

from __future__ import annotations

import inspect
import json
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import websocket as _ws

from core.console_logging import format_console_log, utc_timestamp

MODULE_NAME = "DevNexGCAInvoker"

_GCA_REGISTRY      = Path.home() / ".gca_instances.json"
_GCA_WAIT_TIMEOUT  = 90   # seconds to wait for a new extension to register
_GCA_POLL_INTERVAL = 2    # seconds between registry polls
_GCA_SEND_RETRIES  = 5    # send-prompt retries
_GCA_RETRY_BACKOFF = 5    # seconds between send retries


@dataclass(slots=True)
class GCAInvocationResult:
    """Captures raw response and metadata for one GCA invocation attempt."""
    raw_response:          str
    is_response_valid:     bool
    started_vscode_window: bool


# ── Direct WebSocket client ────────────────────────────────────────────────────

class _DirectGCAClient:
    """
    Thin WebSocket wrapper connected to one gca-communication-layer instance.
    Port and instanceId are captured at construction time — no registry re-read.
    """

    def __init__(self, port: int, instance_id: str) -> None:
        self._instance_id = instance_id
        self._port        = port
        self._ws = _ws.WebSocket()
        self._ws.connect(f"ws://localhost:{port}")

    def _send(self, command: str, payload: Any = None) -> dict[str, Any]:
        message = json.dumps({
            "command":    command,
            "payload":    payload or {},
            "instanceId": self._instance_id,
        })
        self._ws.send(message)
        return json.loads(self._ws.recv())

    def ping(self) -> bool:
        """Return True if the WebSocket connection is still alive."""
        try:
            self._ws.ping()
            return True
        except Exception:
            return False

    def reset_chat(self) -> None:
        try:
            self._send("gca.resetChat")
        except Exception:
            pass

    def close_all_files(self) -> None:
        try:
            self._send("vscode.closeAllFiles")
        except Exception:
            pass

    def open_file(self, file_path: str) -> None:
        try:
            self._send("vscode.openFile", file_path)
        except Exception:
            pass

    def add_file_to_context(self, file_path: str) -> None:
        try:
            self._send("gca.addFileToContext", file_path)
        except Exception:
            pass

    def send_prompt(self, prompt: str) -> str:
        """Send prompt and return response text. Raises on failure after retries."""
        for attempt in range(1, _GCA_SEND_RETRIES + 1):
            try:
                result = self._send("gca.sendPrompt", {"prompt": prompt})
                if result.get("status") == "success":
                    text = str(result.get("response", "")).strip()
                    if text:
                        return text
            except Exception:
                pass
            if attempt < _GCA_SEND_RETRIES:
                time.sleep(_GCA_RETRY_BACKOFF)
        raise RuntimeError(
            f"GCA did not return a response after {_GCA_SEND_RETRIES} attempts."
        )

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


# ── Registry / port helpers ────────────────────────────────────────────────────

def _read_registry() -> list[dict]:
    """Return the list of entries from ~/.gca_instances.json, or []."""
    try:
        data = json.loads(_GCA_REGISTRY.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _read_registry_ids() -> set[str]:
    return {e.get("instanceId", "") for e in _read_registry()}


def _is_port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("localhost", port))
        return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def _find_any_live_instance() -> _DirectGCAClient | None:
    """
    Scan ~/.gca_instances.json and return a connected client for the first
    entry that has an open port. Returns None if no instance is reachable.
    """
    for entry in reversed(_read_registry()):
        port        = entry.get("port")
        instance_id = entry.get("instanceId", "")
        if port and instance_id and _is_port_open(port):
            try:
                return _DirectGCAClient(port=port, instance_id=instance_id)
            except Exception:
                continue
    return None


def _wait_and_connect(before_ids: set[str], timeout: int) -> _DirectGCAClient:
    """
    Poll ~/.gca_instances.json until a NEW instance (not in before_ids) has
    an open port, then immediately open the WebSocket and return the client.
    Raises RuntimeError on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        for entry in reversed(_read_registry()):
            instance_id = entry.get("instanceId", "")
            port        = entry.get("port")
            if instance_id not in before_ids and port and _is_port_open(port):
                try:
                    return _DirectGCAClient(port=port, instance_id=instance_id)
                except Exception:
                    pass  # port open but WS not ready yet — keep polling
        time.sleep(_GCA_POLL_INTERVAL)
    raise RuntimeError(
        f"gca-communication-layer did not register within {timeout}s. "
        "Ensure the VSIX is installed and active."
    )


# ── DevNexGCAInvoker ───────────────────────────────────────────────────────────

class DevNexGCAInvoker:
    """
    @brief Invokes GCA via a single, shared VS Code WebSocket connection.

    @details
    A single DevNexGCAInvoker instance is created per run (by the orchestrator)
    and reused for every stage S1–S9.  All stages therefore share one VS Code
    window and one WebSocket — no new windows are opened between stages.

    Connection acquisition order on each invoke_prompt():
      1. Probe the persisted _client WebSocket — reuse if still alive.
      2. Scan ~/.gca_instances.json for any already-running GCA instance.
      3. Launch a new VS Code window only if (1) and (2) both fail.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self._client:  _DirectGCAClient | None = None
        self._lock:    threading.Lock           = threading.Lock()

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame  = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    # ── Connection management ─────────────────────────────────────────────────

    def _acquire_client(self) -> tuple[_DirectGCAClient, bool]:
        """
        Return (client, launched_new_window).

        Tries in order:
          1. Existing persistent WebSocket (ping check).
          2. Any live registry entry (no new window).
          3. Launch a new VS Code window (last resort).
        """
        # 1. Reuse existing persistent connection
        if self._client is not None:
            if self._client.ping():
                self._trace(
                    f"Reusing persistent GCA connection (instance={self._client._instance_id})."
                )
                return self._client, False
            # Dead — drop it
            self._trace("Persistent WebSocket dropped — reconnecting.", level="WARN")
            self._client.close()
            self._client = None

        # 2. Find any already-running GCA instance (no new VS Code window)
        client = _find_any_live_instance()
        if client is not None:
            self._trace(
                f"Connected to existing GCA instance "
                f"(port={client._port}, instance={client._instance_id})."
            )
            self._client = client
            return client, False

        # 3. No existing instance — launch a new VS Code window
        self._trace("No existing GCA instance found — launching VS Code.", level="WARN")
        isolated_workspace = Path(tempfile.mkdtemp(prefix="devnex_ws_"))
        self._trace(f"Isolated workspace: '{isolated_workspace}'.")

        before_ids = _read_registry_ids()
        started    = self._launch_vscode(isolated_workspace)
        self._trace(f"VS Code launch {'succeeded' if started else 'failed (code not on PATH)'}.")

        self._trace(f"Waiting up to {_GCA_WAIT_TIMEOUT}s for gca-communication-layer…")
        client = _wait_and_connect(before_ids, timeout=_GCA_WAIT_TIMEOUT)
        self._trace(
            f"New GCA instance connected "
            f"(port={client._port}, instance={client._instance_id}).",
            level="SUCCESS",
        )
        self._client = client
        return client, started

    def _launch_vscode(self, isolated_workspace: Path) -> bool:
        for command in (
            ["code", "--new-window", str(isolated_workspace)],
            ["code.cmd", "--new-window", str(isolated_workspace)],
            ["code", "-n", str(isolated_workspace)],
            ["code.cmd", "-n", str(isolated_workspace)],
        ):
            try:
                subprocess.Popen(command, cwd=str(self.repo_path))
                return True
            except FileNotFoundError:
                continue
            except Exception:
                break
        return False

    # ── Public API ────────────────────────────────────────────────────────────

    def invoke_prompt(
        self,
        prompt: str,
        attached_files: list[str] | None = None,
        startup_sleep_seconds: int = 0,   # kept for API compatibility; no longer used
    ) -> GCAInvocationResult:
        """
        @brief Submit one prompt to GCA, reusing the existing VS Code instance.

        @param prompt          Prompt text for GCA.
        @param attached_files  Absolute paths to inject as context files.
        @return GCAInvocationResult with raw response and metadata.
        """
        with self._lock:
            started = False
            try:
                client, started = self._acquire_client()
            except RuntimeError as exc:
                self._trace(str(exc), level="ERROR")
                return self._invoke_via_bridge(prompt, attached_files, False)

            try:
                self._prepare_context(client, attached_files or [])
                self._trace("Sending prompt to GCA via WebSocket.")
                raw_response = client.send_prompt(prompt)
                self._trace(
                    f"GCA response received ({len(raw_response)} chars).",
                    level="SUCCESS",
                )
                return GCAInvocationResult(
                    raw_response=raw_response,
                    is_response_valid=bool(raw_response),
                    started_vscode_window=started,
                )

            except Exception as exc:
                self._trace(
                    f"GCA invocation error: {exc} — invalidating connection, falling back to bridge.",
                    level="ERROR",
                )
                # Invalidate the dead client so next call triggers reconnect
                self._client = None
                try:
                    client.close()
                except Exception:
                    pass
                return self._invoke_via_bridge(prompt, attached_files, started)

    def _prepare_context(
        self,
        client: _DirectGCAClient,
        context_file_paths: list[str],
    ) -> None:
        """Reset chat, close all editor tabs, then inject context files."""
        client.reset_chat()
        self._trace("GCA chat reset.")

        client.close_all_files()
        self._trace("Editor tabs cleared.")

        successful = 0
        for file_path in context_file_paths:
            try:
                client.open_file(file_path)
                client.add_file_to_context(file_path)
                self._trace(f"Context file added: '{file_path}'.")
                successful += 1
            except Exception as exc:
                self._trace(
                    f"Context file injection failed for '{file_path}': {exc}",
                    level="WARN",
                )

        if context_file_paths:
            self._trace(
                f"Context injection complete: {successful}/{len(context_file_paths)} file(s)."
            )

    def _invoke_via_bridge(
        self,
        prompt: str,
        attached_files: list[str] | None,
        started_vscode_window: bool,
    ) -> GCAInvocationResult:
        """Fallback: invoke GCA via the DevNex Bridge VSIX HTTP relay."""
        from gca.bridge import DevNexBridge
        self._trace("Sending prompt via Bridge HTTP fallback.")
        response_text = DevNexBridge.send_prompt(prompt, attached_files or [])
        self._trace(f"Bridge response received ({len(response_text)} chars).")
        return GCAInvocationResult(
            raw_response=response_text,
            is_response_valid=bool(response_text),
            started_vscode_window=started_vscode_window,
        )

    def disconnect(self) -> None:
        """Explicitly close the persistent WebSocket (call on shutdown)."""
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None
                self._trace("GCA WebSocket connection closed.")

    def is_available(self) -> bool:
        """Check VS Code CLI availability without launching a window."""
        try:
            result = subprocess.run(["code", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
