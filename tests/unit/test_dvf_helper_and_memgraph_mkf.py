"""Tests for the generic DVF helper + Memgraph-backed MkfClient strategy."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_DEVNEX_ROOT = Path(__file__).resolve().parents[2] / "cipher" / "agents" / "devnex_assistant"
if str(_DEVNEX_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEVNEX_ROOT))


# ── DVF helper utilities ─────────────────────────────────────────────────────

def test_path_context_with_content_packs_attached_tail():
    from cipher.agents.devnex_assistant.core.orchestrator import path_context_with_content
    ctx = path_context_with_content({"a": "1"}, ["\n\n### FILE: x.c\n```\nint x;\n```"])
    assert ctx["a"] == "1"
    assert "## Attached Input Files" in ctx["__attached_content__"]
    assert "x.c" in ctx["__attached_content__"]


def test_render_crc_as_json_default_renderer():
    from cipher.agents.devnex_assistant.core.orchestrator import _render_crc_as_json
    # Object that exposes model_dump — mimics CRCChain interface.
    class _FakeCRC:
        def model_dump(self, mode="json"):  # noqa: ARG002
            return {"steps": [], "target_asil": "ASIL-B"}
    out = _render_crc_as_json(_FakeCRC(), "Dio")
    assert '"target_asil": "ASIL-B"' in out


# ── Memgraph reachability probe ──────────────────────────────────────────────

def test_memgraph_reachability_probe_returns_bool():
    from cipher.agents.memory_agent.memgraph_mkf import memgraph_reachable
    # Without a running Memgraph this returns False; with one it returns True.
    # Either way the call must not raise and must return a bool.
    result = memgraph_reachable("bolt://127.0.0.1:1")  # unreachable port
    assert result is False


def test_build_default_mkf_falls_back_to_in_memory_when_memgraph_down(monkeypatch):
    from cipher.agents.memory_agent import agent as mod
    from cipher.agents.memory_agent.agent import build_default_mkf, InMemoryMkf

    # Force the reachability probe to report DOWN.
    from cipher.agents.memory_agent import memgraph_mkf as mm
    monkeypatch.setattr(mm, "memgraph_reachable", lambda *_a, **_k: False)

    mkf = build_default_mkf()
    assert isinstance(mkf, InMemoryMkf), f"Expected fallback InMemoryMkf, got {type(mkf)}"


def test_memgraph_mkf_swallows_query_errors_gracefully():
    """A query against an unreachable Memgraph must return [] not raise."""
    from cipher.agents.memory_agent.memgraph_mkf import MemgraphMkf
    mkf = MemgraphMkf(uri="bolt://127.0.0.1:1")  # nothing listens there
    assert mkf.has("mkf://nonexistent") is False
    assert mkf.list_for_node("S1N1") == []
