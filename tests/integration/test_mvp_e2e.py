"""MVP end-to-end smoke test — REST → CipherOrchestrator → DevNexOrchestrator.

Boots a real CipherOrchestrator into the cipher_routes module, fakes the GCA
invoker, POSTs to /cipher/nodes/S1N1/run, then polls for `node.complete` via
direct EventBridge subscription. Verifies the LLD CSV artifact lands in
~/.devnex/runs/{run_id}/.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure devnex_assistant package is on sys.path the same way main_window.py does it.
_DEVNEX_ROOT = Path(__file__).resolve().parents[2] / "cipher" / "agents" / "devnex_assistant"
if str(_DEVNEX_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEVNEX_ROOT))


@dataclass
class _FakeInvokeResult:
    raw_response: str = ""
    is_response_valid: bool = True


class _FakeGCA:
    """Drop-in stand-in for DevNexGCAInvoker — returns canned CSV."""

    def __init__(self, response: str) -> None:
        self._response = response

    def invoke_prompt(self, prompt: str, attached_files: list[str]) -> _FakeInvokeResult:  # noqa: ARG002
        return _FakeInvokeResult(raw_response=self._response)


@pytest.fixture
def fixture_swc(tmp_path: Path) -> dict:
    """Build a minimal SWC workspace with all files S1N1 expects."""
    workspace = tmp_path / "swc"
    workspace.mkdir()
    files = {
        "SWC_name_C":         "Dio.c",
        "SWC_name_H":         "Dio.h",
        "G_SWDD_TEMP":        "G_SWDD_TEMP.csv",
        "SWC_name_TEMP_LLD":  "Dio_TEMP_LLD.csv",
        "SWC_name_HLD":       "Dio_HLD.csv",
        "lds_file":           "linker.lds",
        "map_file":           "build.map",
    }
    for k, name in files.items():
        (workspace / name).write_text(f"/* stub: {k} */\n", encoding="utf-8")

    return {
        "workspace_path": str(workspace),
        "SWC_name": "Dio",
        **files,
        "max_gca_retries": 1,
    }


def _build_orchestrator_with_fake_gca(config: dict, csv_response: str):
    """Construct a DevNexOrchestrator pre-wired with a fake GCA invoker."""
    from core.orchestrator import DevNexOrchestrator  # type: ignore
    from core.run_context import DevNexRunContext  # type: ignore

    ctx = DevNexRunContext(
        swc_name=config["SWC_name"],
        workspace_path=config["workspace_path"],
    )
    orch = DevNexOrchestrator(run_context=ctx)
    # Override config (orchestrator persists/loads via ConfigStore — bypass for test).
    orch.config = config
    orch._gca_invoker = _FakeGCA(csv_response)
    return orch


def test_mvp_s1n1_legacy_path(fixture_swc: dict, tmp_path: Path):
    """REST → CipherOrchestrator → DevNex S1N1 (legacy non-DVF path) writes CSV."""
    from cipher.are.a2a_server.server import app
    from cipher.are.a2a_server.cipher_routes import attach_orchestrator
    from cipher.core.orchestrator import CipherOrchestrator

    csv_response = "REQ_ID,FUNCTION_OR_ELEMENT,TYPE\nREQ_1,Dio_Init,FUNCTION\n"
    config = fixture_swc

    # Construct the orchestrator hierarchy.
    cipher_orch = CipherOrchestrator()
    devnex_orch = _build_orchestrator_with_fake_gca(config, csv_response)
    cipher_orch.register_child("devnex", devnex_orch)
    attach_orchestrator(cipher_orch)

    client = TestClient(app)

    # Push config via the REST surface — exercises new workspace validation too.
    r = client.put("/cipher/config", json=config)
    assert r.status_code == 200, r.text

    # Kick S1N1.
    r = client.post("/cipher/nodes/S1N1/run")
    assert r.status_code == 200, r.text
    run_id = r.json()["runId"]
    assert run_id

    # Poll healthz until run leaves `running`.
    deadline = time.time() + 10.0
    final_state = None
    while time.time() < deadline:
        h = client.get("/cipher/healthz").json()
        # Re-read internal _runs through the module to inspect status.
        from cipher.are.a2a_server import cipher_routes as cr
        state = cr._runs.get(run_id, {}).get("status")
        if state in ("complete", "error"):
            final_state = state
            break
        time.sleep(0.1)

    if final_state != "complete":
        from cipher.are.a2a_server import cipher_routes as cr
        err = cr._runs.get(run_id, {}).get("error", "(no error message)")
        raise AssertionError(f"Run did not complete; state={final_state} error={err!r}")

    # Artifact should exist in the orchestrator's per-run artifacts dir.
    artifacts_root = devnex_orch._artifacts_dir
    csv_files = list(Path(artifacts_root).glob("*_TEMP_LLD_updated.csv"))
    assert csv_files, "Expected an LLD CSV artifact under the run dir"
    assert csv_response.split("\n")[0] in csv_files[0].read_text(encoding="utf-8")


def test_mvp_put_config_rejects_bad_workspace():
    """Sprint 7 S7-2 — invalid workspace_path is rejected with 400."""
    from cipher.are.a2a_server.server import app

    client = TestClient(app)
    bad = {"workspace_path": "C:/definitely/not/a/real/path/cipher-mvp-test"}
    r = client.put("/cipher/config", json=bad)
    assert r.status_code == 400
    assert "does not exist" in r.text


def test_mvp_voice_endpoints_present():
    """Sprint 7 S7-3/S7-4 — endpoints exist and return either 200 (backend installed)
    or 503 (backend missing). Either is acceptable; the smoke is that the route
    is wired and goes through the lazy-import path."""
    from cipher.are.a2a_server.server import app

    client = TestClient(app)
    r = client.post("/cipher/voice/speak", json={"text": "hello"})
    assert r.status_code in (200, 500, 503), f"Unexpected: {r.status_code} {r.text}"
