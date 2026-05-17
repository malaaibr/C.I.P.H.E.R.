"""
CIPHER POC Runner — Launches LLM Gateway, A2A Server, and Unified GUI.

Usage: python run_poc.py
Requires: Ollama running with a model pulled, Docker Compose stack up.
"""

from __future__ import annotations

import asyncio
import sys
import threading

import uvicorn
from PyQt6.QtWidgets import QApplication

from cipher.are.a2a_server.server import app as a2a_app
from cipher.are.skill_loader.loader import get_skill_loader
from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill
from cipher.core.orchestrator import CipherOrchestrator
from cipher.gui.app import create_app
from cipher.gui.main_window import CipherMainWindow
from cipher.gui.splash import SplashScreen
from cipher.trf.mcp_servers.llm_gateway.server import app as gateway_app


A2A_PORT = 8100
GATEWAY_PORT = 8200


def start_server(app, port: int) -> None:
    """Run a uvicorn server in a daemon thread."""
    try:
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
    except Exception as e:
        print(f"[CIPHER] Server on port {port} failed: {e}", flush=True)


def main() -> None:
    # Register skills
    loader = get_skill_loader()
    loader.register(S1N1Skill())
    print(f"[CIPHER] Registered skills: {loader.list_skills()}")

    # Create mother orchestrator
    orchestrator = CipherOrchestrator()
    print("[CIPHER] CipherOrchestrator initialized")

    # Start LLM Gateway server
    gw_thread = threading.Thread(
        target=start_server, args=(gateway_app, GATEWAY_PORT), daemon=True
    )
    gw_thread.start()
    print(f"[CIPHER] LLM Gateway starting on http://127.0.0.1:{GATEWAY_PORT}")

    # Start A2A server
    a2a_thread = threading.Thread(
        target=start_server, args=(a2a_app, A2A_PORT), daemon=True
    )
    a2a_thread.start()
    print(f"[CIPHER] A2A Server starting on http://127.0.0.1:{A2A_PORT}")

    # Launch unified GUI
    qt_app = create_app()

    try:
        window = CipherMainWindow()
    except Exception as e:
        print(f"[CIPHER] FATAL: MainWindow creation failed: {e}")
        sys.exit(1)

    def _on_splash_done() -> None:
        try:
            window.show()
            window.raise_()
            window.activateWindow()
            window.append_log("LLM Gateway online — :8200", level="SUCCESS")
            window.append_log("A2A Server online — :8100", level="SUCCESS")
            window.append_log("C.I.P.H.E.R ready. Use HUD or open DevNex workspace.", level="INFO")
            qt_app.setQuitOnLastWindowClosed(True)
            print("[CIPHER] Main window shown successfully", flush=True)
        except Exception as e:
            print(f"[CIPHER] ERROR in _on_splash_done: {e}", flush=True)
            import traceback
            traceback.print_exc()

    splash = SplashScreen()
    splash.finished.connect(_on_splash_done)
    splash.show()

    print("[CIPHER] Unified GUI launched — CIPHER HUD + DevNex Workspace", flush=True)
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
