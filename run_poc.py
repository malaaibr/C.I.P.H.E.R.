"""
CIPHER POC Runner — Launches LLM Gateway, A2A Server, and (optionally) GUI.

Usage:
  python run_poc.py              # Full PyQt6 GUI + servers (default)
  python run_poc.py --headless   # Servers only — for VSCode VSIX extension host

Requires: Ollama running with a model pulled, Docker Compose stack up.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import threading
import time

import uvicorn

from cipher.are.a2a_server.server import app as a2a_app
from cipher.are.a2a_server.cipher_routes import attach_orchestrator
from cipher.are.skill_loader.loader import get_skill_loader
from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill
from cipher.core.orchestrator import CipherOrchestrator
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


def _bootstrap_common() -> CipherOrchestrator:
    """Register skills, build the mother orchestrator, start both servers."""
    loader = get_skill_loader()
    loader.register(S1N1Skill())
    print(f"[CIPHER] Registered skills: {loader.list_skills()}")

    orchestrator = CipherOrchestrator()
    attach_orchestrator(orchestrator)
    print("[CIPHER] CipherOrchestrator initialized and attached to VSIX bridge")

    threading.Thread(
        target=start_server, args=(gateway_app, GATEWAY_PORT), daemon=True,
        name="cipher-llm-gateway",
    ).start()
    print(f"[CIPHER] LLM Gateway starting on http://127.0.0.1:{GATEWAY_PORT}")

    threading.Thread(
        target=start_server, args=(a2a_app, A2A_PORT), daemon=True,
        name="cipher-a2a-server",
    ).start()
    print(f"[CIPHER] A2A Server starting on http://127.0.0.1:{A2A_PORT}")
    print(f"[CIPHER] VSIX bridge ready at  http://127.0.0.1:{A2A_PORT}/cipher/healthz")
    return orchestrator


def main_headless() -> None:
    """Headless entry point — used by the VSCode VSIX extension host."""
    _bootstrap_common()
    print("[CIPHER] Headless mode — servers only. Press Ctrl-C to exit.", flush=True)

    stop_event = threading.Event()

    def _on_signal(signum, frame):  # noqa: ARG001
        print(f"[CIPHER] Received signal {signum}, shutting down.", flush=True)
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, _on_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _on_signal)
    except Exception:
        pass

    # Keep main thread alive; daemon servers exit with process.
    while not stop_event.is_set():
        time.sleep(0.5)
    print("[CIPHER] Headless host exited cleanly.", flush=True)


def main_gui() -> None:
    """Full GUI launch — keeps the legacy PyQt6 surface working."""
    from PyQt6.QtWidgets import QApplication  # noqa: F401  (kept for parity)
    from cipher.gui.app import create_app
    from cipher.gui.main_window import CipherMainWindow
    from cipher.gui.splash import SplashScreen

    orchestrator = _bootstrap_common()

    qt_app = create_app()

    try:
        window = CipherMainWindow(parent_orchestrator=orchestrator)
    except TypeError:
        # Backwards-compat: window not yet updated to accept parent_orchestrator.
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


def main() -> None:
    parser = argparse.ArgumentParser(description="CIPHER POC runner")
    parser.add_argument(
        "--headless", action="store_true",
        help="Run servers only (no PyQt6 GUI). Used by the VSCode extension host.",
    )
    args = parser.parse_args()
    if args.headless:
        main_headless()
    else:
        main_gui()


if __name__ == "__main__":
    main()
