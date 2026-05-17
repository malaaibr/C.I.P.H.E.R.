# -*- coding: utf-8 -*-
"""
verify_dio_demo_ready.py - Preflight checks for the CIPHER Dio demo trial.

Run from the CIPHER_Repo/ root:

    python scripts/verify_dio_demo_ready.py

Exit 0 if all critical checks pass, non-zero on any failure. Uses only the
Python standard library so it runs on any clean Python 3.11+ install on
Windows PowerShell. Output is plain ASCII (no colors, no Unicode glyphs).

Cross-refs:
  - docs/wbs/WBS-0002-dio-demo-trial.md (Sec. 4 Demo Prerequisites)
  - docs/DEMO_RUNBOOK_DIO.md (Sec. 1 Pre-flight)
  - deploy/local/docker-compose.yml (infra port map)
  - run_poc.py (CIPHER ports 8100 / 8200)
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

REQUIRED_KEYS = [
    "SWC_name", "G_SWDD_TEMP", "SWC_name_C", "SWC_name_H",
    "SWC_name_TEMP_LLD", "SWC_name_FUNC_req", "SWC_nameInspBaseLLD",
    "SWC_name_HLD", "lds_file", "map_file", "workspace_path",
]
# Keys whose value is a filename to resolve under workspace_path.
# SWC_name_FUNC_req and SWC_nameInspBaseLLD are intentionally empty.
FILE_KEYS = ["G_SWDD_TEMP", "SWC_name_C", "SWC_name_H", "SWC_name_TEMP_LLD",
             "SWC_name_HLD", "lds_file", "map_file"]
WORKSPACE_FILES = ["Dio.c", "Dio.h", "Dio_HLD.md", "Dio_TEMP_LLD.csv",
                   "G_SWDD_TEMP.md", "stm32h7xx_flash.ld", "firmware.map",
                   "cipher_config_dio.json"]
INFRA_PORTS = [(4222, "NATS"), (6333, "Qdrant"), (6379, "Redis"),
               (7687, "Memgraph"), (8181, "OPA"), (9000, "MinIO")]
CIPHER_PORTS = [(8100, "A2A Server"), (8200, "LLM Gateway")]


class Tally:
    def __init__(self) -> None:
        self.total = self.passed = self.failed = 0

    def ok(self, msg: str) -> None:
        self.total += 1; self.passed += 1
        print(f"[OK]   {msg}")

    def fail(self, msg: str) -> None:
        self.total += 1; self.failed += 1
        print(f"[FAIL] {msg}")

    def info(self, msg: str) -> None:
        print(f"[INFO] {msg}")


def _section(title: str) -> None:
    print(f"\n--- {title} ---")


def _tcp_probe(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_python(t: Tally) -> None:
    _section("1. Python version")
    v = sys.version_info
    label = f"{v.major}.{v.minor}.{v.micro}"
    (t.ok if v >= (3, 11) else t.fail)(
        f"Python {label} {'>=' if v >= (3, 11) else '<'} 3.11"
    )


def check_workspace_files(t: Tally, workspace: Path) -> None:
    _section("2. Demo workspace files")
    if not workspace.is_dir():
        t.fail(f"Workspace directory missing: {workspace}")
        return
    for name in WORKSPACE_FILES:
        p = workspace / name
        if p.is_file():
            t.ok(f"workspace file present: {name}")
        else:
            t.fail(f"workspace file missing: {p}")


def check_config_json(t: Tally, workspace: Path) -> None:
    _section("3. cipher_config_dio.json")
    cfg_path = workspace / "cipher_config_dio.json"
    if not cfg_path.is_file():
        t.fail(f"config not found: {cfg_path}")
        return
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        t.fail(f"config JSON parse error: {exc}")
        return
    if not isinstance(data, dict):
        t.fail("config root is not an object")
        return
    for key in REQUIRED_KEYS:
        (t.ok if key in data else t.fail)(
            f"key present: {key}" if key in data else f"missing required key: {key}"
        )
    ws_path = Path(data.get("workspace_path") or str(workspace))
    if not ws_path.is_dir():
        t.fail(f"workspace_path does not exist on disk: {ws_path}")
        return
    for key in FILE_KEYS:
        fname = (data.get(key) or "").strip()
        if not fname:
            t.fail(f"{key} is empty (expected a filename)")
            continue
        fpath = ws_path / fname
        if fpath.is_file():
            t.ok(f"{key} -> {fname} resolved")
        else:
            t.fail(f"{key} -> {fpath} not found on disk")


def check_docker_ports(t: Tally) -> None:
    _section("4. Docker infra ports (deploy/local/docker-compose.yml)")
    for port, name in INFRA_PORTS:
        if _tcp_probe("127.0.0.1", port):
            t.ok(f"{name} reachable on :{port}")
        else:
            t.fail(f"{name} unreachable on :{port} - is docker compose up?")


def check_ollama(t: Tally) -> None:
    _section("5. Ollama + qwen2.5-coder model")
    url = "http://localhost:11434/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        t.fail(f"Ollama unreachable at {url}: {exc}")
        return
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        t.fail(f"Ollama returned non-JSON: {exc}")
        return
    models = payload.get("models", []) if isinstance(payload, dict) else []
    matches = [m.get("name", "") for m in models
               if isinstance(m, dict) and str(m.get("name", "")).startswith("qwen2.5-coder")]
    if matches:
        t.ok(f"qwen2.5-coder model present: {matches[0]}")
    else:
        t.fail("no qwen2.5-coder* model installed - run: ollama pull qwen2.5-coder:1.5b")


def check_cipher_ports(t: Tally) -> None:
    _section("6. CIPHER ports (informational)")
    for port, name in CIPHER_PORTS:
        if _tcp_probe("127.0.0.1", port):
            t.info(f"port {port} already bound ({name}) - CIPHER may already be running")
        else:
            t.info(f"port {port} free ({name}) - run_poc.py can bind")


def main() -> int:
    here = Path(__file__).resolve().parent
    workspace = (here.parent / "generated_artifacts" / "dio_demo_workspace").resolve()
    print("CIPHER Dio demo preflight")
    print(f"  script:    {Path(__file__).resolve()}")
    print(f"  workspace: {workspace}")
    t = Tally()
    check_python(t)
    check_workspace_files(t, workspace)
    check_config_json(t, workspace)
    check_docker_ports(t)
    check_ollama(t)
    check_cipher_ports(t)  # informational only - never fails
    _section("Summary")
    print(f"  total : {t.total}")
    print(f"  passed: {t.passed}")
    print(f"  failed: {t.failed}")
    if t.failed == 0:
        print("\nRESULT: READY - proceed with `python run_poc.py`.")
        return 0
    print("\nRESULT: NOT READY - resolve the [FAIL] lines above before starting the demo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
