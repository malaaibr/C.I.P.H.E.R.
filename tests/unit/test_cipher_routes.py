"""Smoke tests for the VSIX bridge — REST + SSE on the headless host."""

from __future__ import annotations

import json
from fastapi.testclient import TestClient

from cipher.are.a2a_server.server import app
from cipher.are.a2a_server.cipher_routes import attach_orchestrator
from cipher.core.orchestrator import CipherOrchestrator
from cipher.interfaces.web.event_bridge import EventBridge, Event, get_event_bridge


def test_healthz_without_orchestrator():
    client = TestClient(app)
    r = client.get("/cipher/healthz")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert "orchestrator_attached" in j


def test_healthz_with_orchestrator():
    attach_orchestrator(CipherOrchestrator())
    client = TestClient(app)
    r = client.get("/cipher/healthz")
    assert r.json()["orchestrator_attached"] is True


def test_config_round_trip(tmp_path):
    client = TestClient(app)
    cfg = {"SWC_name": "Dio", "workspace_path": str(tmp_path)}
    r = client.put("/cipher/config", json=cfg)
    assert r.status_code == 200
    assert set(r.json()["keys"]) == set(cfg.keys())

    r2 = client.get("/cipher/config")
    assert r2.status_code == 200
    assert r2.json() == cfg


def test_workflow_reset():
    client = TestClient(app)
    r = client.post("/cipher/workflow/reset")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_event_envelope_serialization():
    e = Event(kind="log", payload={"message": "hello", "level": "INFO"},
              run_id="r1", node_id="S1N1")
    j = json.loads(e.to_json())
    assert j["kind"] == "log"
    assert j["runId"] == "r1"
    assert j["nodeId"] == "S1N1"
    assert j["payload"]["message"] == "hello"


def test_event_bridge_pub_sub_no_loop():
    """Without an attached loop, publish falls back to put_nowait."""
    b = EventBridge()
    # No subscribers: silent no-op.
    b.publish(Event(kind="log", payload={"message": "x"}))


def test_event_bridge_singleton():
    a = get_event_bridge()
    b = get_event_bridge()
    assert a is b
