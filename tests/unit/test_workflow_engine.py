"""Unit tests for WorkflowEngine (T-020)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


# Mock langgraph for unit tests (heavy dependency)
mock_langgraph = MagicMock()
mock_checkpoint = MagicMock()
sys.modules.setdefault("langgraph", mock_langgraph)
sys.modules.setdefault("langgraph.graph", mock_langgraph.graph)
sys.modules.setdefault("langgraph.checkpoint", mock_checkpoint)
sys.modules.setdefault("langgraph.checkpoint.sqlite", mock_checkpoint.sqlite)
sys.modules.setdefault("langgraph.checkpoint.sqlite.aio", mock_checkpoint.sqlite.aio)

# Provide END constant
mock_langgraph.graph.END = "__end__"

# Provide StateGraph mock
mock_sg_instance = MagicMock()
mock_langgraph.graph.StateGraph = MagicMock(return_value=mock_sg_instance)

from cipher.pkl.workflow.workflow_engine import WorkflowEngine, WorkflowState


class TestWorkflowEngine:
    def test_add_node(self) -> None:
        engine = WorkflowEngine()

        def node_fn(state: WorkflowState) -> WorkflowState:
            return state

        engine.add_node("step1", node_fn)
        assert "step1" in engine._nodes

    def test_build_sequential(self) -> None:
        engine = WorkflowEngine()

        def n1(s: WorkflowState) -> WorkflowState:
            return s

        def n2(s: WorkflowState) -> WorkflowState:
            return s

        engine.add_node("n1", n1)
        engine.add_node("n2", n2)
        engine.build_sequential()

        assert engine._graph is not None
        mock_sg_instance.set_entry_point.assert_called_with("n1")
        mock_sg_instance.add_edge.assert_any_call("n1", "n2")

    def test_initial_state_type(self) -> None:
        state: WorkflowState = {
            "task_id": "abc",
            "skill_id": "vcycle_s1n1",
            "prompt": "generate LLD",
            "context": {},
            "node_results": {},
            "current_node": "start",
            "status": "PENDING",
            "error": None,
        }
        assert state["task_id"] == "abc"
        assert state["status"] == "PENDING"
