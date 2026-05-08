"""HTTP client to the DevNex Bridge VSIX running on localhost:37778."""

from __future__ import annotations

import inspect
from typing import List

import requests

from core.console_logging import format_console_log, utc_timestamp
from core.errors import GCABridgeError, GCANotAvailableError

MODULE_NAME = "DevNexBridge"

BRIDGE_URL       = "http://127.0.0.1:37778"
TIMEOUT_HEALTH   = 2
TIMEOUT_PROMPT   = 120


class DevNexBridge:
    """
    @brief HTTP relay client to the DevNex Bridge VSIX.

    @details
    The Bridge VSIX runs inside VS Code on :37778 and relays requests to
    vscode.commands.executeCommand('extension.llm.sendPrompt').
    This is the ONLY place in the DevNex Python codebase that communicates
    with the Bridge VSIX directly.
    """

    @staticmethod
    def _trace(message: str, level: str = "INFO") -> None:
        frame = inspect.currentframe()
        caller = frame.f_back.f_code.co_name if frame and frame.f_back else "<unknown>"
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    @staticmethod
    def send_prompt(prompt: str, attached_files: List[str] | None = None) -> str:
        """
        @brief Send a prompt to GCA via the Bridge VSIX and return llmResponse.

        @param prompt         Prompt text for the LLM.
        @param attached_files Absolute paths to inject as context files.
        @return Raw LLM response string.

        @raises GCANotAvailableError when the Bridge cannot be reached.
        @raises GCABridgeError       for other HTTP or response errors.
        """
        payload = {
            "prompt":        prompt,
            "attachedFiles": attached_files or [],
        }
        DevNexBridge._trace(f"POST {BRIDGE_URL}/sendPrompt (prompt={len(prompt)} chars, files={len(attached_files or [])}).")
        try:
            response = requests.post(
                f"{BRIDGE_URL}/sendPrompt",
                json=payload,
                timeout=TIMEOUT_PROMPT,
            )
            if response.status_code != 200:
                raise GCABridgeError(f"Bridge returned HTTP {response.status_code}: {response.text}")
            data = response.json()
            llm_response = data.get("llmResponse") or data.get("response", "")
            if not llm_response:
                raise GCABridgeError("Bridge returned empty response.")
            DevNexBridge._trace(f"Bridge response received ({len(llm_response)} chars).", level="SUCCESS")
            return llm_response

        except requests.exceptions.ConnectionError:
            raise GCANotAvailableError(
                f"Cannot reach DevNex Bridge at {BRIDGE_URL}.\n"
                "Ensure VS Code is open with the DevNex Bridge VSIX active."
            )
        except requests.exceptions.Timeout:
            raise GCABridgeError(f"GCA request timed out after {TIMEOUT_PROMPT}s.")
        except GCABridgeError:
            raise
        except Exception as e:
            raise GCABridgeError(f"Bridge error: {e}")

    @staticmethod
    def is_available() -> bool:
        """@brief Check if the Bridge VSIX is reachable."""
        try:
            r = requests.get(f"{BRIDGE_URL}/health", timeout=TIMEOUT_HEALTH)
            return r.status_code == 200
        except Exception:
            return False
