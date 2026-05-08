"""DevNex GCA Invoker — adapted from Int_Agent VscodeGeminiInvoker.

Fix: GeminiController(vs_path=...) uses workspace-based registry lookup, but VS Code
stores the workspace path in a different format (URI / different casing on Windows),
so _select_instance returns None → client=None → 'NoneType'.get() crash.

Solution: poll ~/.gca_instances.json directly, detect the new instance at the moment
its port is open, open the WebSocket immediately (before any race), and communicate
directly — no GeminiController re-initialization after detection.
"""

from __future__ import annotations

import inspect
import json
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import websocket as _ws

from core.console_logging import format_console_log, utc_timestamp

MODULE_NAME = "DevNexGCAInvoker"

_GCA_REGISTRY      = Path.home() / ".gca_instances.json"
_GCA_WAIT_TIMEOUT  = 90   # seconds to wait for the extension to register
_GCA_POLL_INTERVAL = 2    # seconds between registry polls
_GCA_SEND_RETRIES  = 5    # retries when sendPrompt returns error/empty
_GCA_RETRY_BACKOFF = 5    # seconds between send retries


@dataclass(slots=True)
class GCAInvocationResult:
    """
    @brief Captures raw response and metadata for one GCA invocation attempt.
    """
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
        self._ws = _ws.WebSocket()
        self._ws.connect(f"ws://localhost:{port}")

    def _send(self, command: str, payload: Any = None) -> Dict[str, Any]:
        msg = json.dumps({
            "command":    command,
            "payload":    payload or {},
            "instanceId": self._instance_id,
        })
        self._ws.send(msg)
        return json.loads(self._ws.recv())

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


# ── Registry helpers ───────────────────────────────────────────────────────────

def _read_registry_ids() -> set:
    try:
        data = json.loads(_GCA_REGISTRY.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {e.get("instanceId", "") for e in data}
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return set()


def _is_port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("localhost", port))
        return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def _wait_and_connect(before_ids: set, timeout: int) -> _DirectGCAClient:
    """
    Poll ~/.gca_instances.json until a new instance (not in before_ids) has an
    open port, then immediately open the WebSocket and return the live client.
    Raises RuntimeError on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = json.loads(_GCA_REGISTRY.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for entry in reversed(data):
                    iid  = entry.get("instanceId", "")
                    port = entry.get("port")
                    if iid not in before_ids and port and _is_port_open(port):
                        try:
                            return _DirectGCAClient(port=port, instance_id=iid)
                        except Exception:
                            pass  # port open but WS not ready yet — keep polling
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(_GCA_POLL_INTERVAL)
    raise RuntimeError(
        f"gca-communication-layer did not register within {timeout}s. "
        "Ensure the VSIX is installed and active."
    )


# ── DevNexGCAInvoker ───────────────────────────────────────────────────────────

class DevNexGCAInvoker:
    """
    @brief Invokes GCA via isolated VS Code workspace + direct WebSocket.

    @details
    Each invoke_prompt() creates a fresh temp workspace, launches VS Code,
    waits for the gca-communication-layer VSIX to register in
    ~/.gca_instances.json, then connects directly via WebSocket.

    BUG FIX — isolated workspace per invocation
    ─────────────────────────────────────────────
    Root cause: GeminiController(workspace_path) connects to the *first* VS Code
    instance that has workspace_path open.

    Fix: each invoke_prompt call creates a fresh temporary workspace directory.
    No existing VS Code window can have that directory open.

    BUG FIX — direct WebSocket instead of GeminiController re-initialization
    ──────────────────────────────────────────────────────────────────────────
    Root cause: GeminiController re-reads ~/.gca_instances.json in its __init__,
    which can race with the extension deregistering, leaving client=None and
    causing 'NoneType'.get() on send_prompt.

    Fix: open the WebSocket at the moment of detection (port + instanceId captured
    once) so no second registry read is needed.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    @staticmethod
    def _create_isolated_workspace() -> Path:
        return Path(tempfile.mkdtemp(prefix="devnex_ws_"))

    def _launch_vscode(self, isolated_workspace: Path) -> bool:
        for cmd in (
            ["code", "--new-window", str(isolated_workspace)],
            ["code.cmd", "--new-window", str(isolated_workspace)],
            ["code", "-n", str(isolated_workspace)],
            ["code.cmd", "-n", str(isolated_workspace)],
        ):
            try:
                subprocess.Popen(cmd, cwd=str(self.repo_path))
                return True
            except FileNotFoundError:
                continue
            except Exception:
                break
        return False

    def invoke_prompt(
        self,
        prompt: str,
        attached_files: List[str] | None = None,
        startup_sleep_seconds: int = 0,   # kept for API compatibility; no longer used
    ) -> GCAInvocationResult:
        """
        @brief Launch fresh VS Code window and submit one prompt via WebSocket.

        @param prompt          Prompt text for GCA.
        @param attached_files  Absolute paths to inject as context files.
        @return GCAInvocationResult with raw response and metadata.
        """
        isolated_workspace = self._create_isolated_workspace()
        self._trace(f"Isolated workspace: '{isolated_workspace}'.")

        # Snapshot the registry BEFORE launch to detect the new entry.
        before_ids = _read_registry_ids()

        started = self._launch_vscode(isolated_workspace)
        self._trace(f"VS Code launch {'succeeded' if started else 'failed'}.")

        self._trace(f"Waiting up to {_GCA_WAIT_TIMEOUT}s for gca-communication-layer…")
        try:
            client = _wait_and_connect(before_ids, timeout=_GCA_WAIT_TIMEOUT)
        except RuntimeError as exc:
            self._trace(str(exc), level="ERROR")
            return self._invoke_via_bridge(prompt, attached_files, started)

        try:
            # Activate: reset chat + clean editor + inject context files.
            self._prepare_context(client, attached_files or [])

            self._trace("Sending prompt to GCA via WebSocket.")
            raw_response = client.send_prompt(prompt)
            self._trace(f"GCA response received ({len(raw_response)} chars).")

            return GCAInvocationResult(
                raw_response=raw_response,
                is_response_valid=bool(raw_response),
                started_vscode_window=started,
            )

        except Exception as exc:
            self._trace(f"GCA invocation error: {exc} — falling back to bridge.", level="ERROR")
            return self._invoke_via_bridge(prompt, attached_files, started)

        finally:
            client.close()

    def _prepare_context(
        self,
        client: _DirectGCAClient,
        context_file_paths: List[str],
    ) -> None:
        """
        @brief Reset chat, close all files, then inject context files.

        Mirrors _prepare_gca_controller_context from the original invoker.
        """
        client.reset_chat()
        self._trace("GCA environment reset (reset_chat).")

        client.close_all_files()
        self._trace("All editor tabs closed.")

        successful = 0
        for file_path in context_file_paths:
            try:
                client.open_file(file_path)
                client.add_file_to_context(file_path)
                self._trace(f"Context file added: '{file_path}'.")
                successful += 1
            except Exception as exc:
                self._trace(f"Context file injection failed for '{file_path}': {exc}", level="WARN")

        if context_file_paths:
            self._trace(
                f"Context injection complete: {successful}/{len(context_file_paths)} file(s)."
            )

    def _invoke_via_bridge(
        self,
        prompt: str,
        attached_files: List[str] | None,
        started_vscode_window: bool,
    ) -> GCAInvocationResult:
        """@brief Fallback: invoke GCA via the DevNex Bridge VSIX HTTP relay."""
        from gca.bridge import DevNexBridge
        bridge = DevNexBridge()
        self._trace("Sending prompt via Bridge HTTP client.")
        response_text = bridge.send_prompt(prompt, attached_files or [])
        self._trace(f"Bridge response received ({len(response_text)} chars).")
        return GCAInvocationResult(
            raw_response=response_text,
            is_response_valid=bool(response_text),
            started_vscode_window=started_vscode_window,
        )

    def is_available(self) -> bool:
        """@brief Check VS Code CLI availability without launching a window."""
        try:
            result = subprocess.run(["code", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
