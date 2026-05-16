"""LangGraph StateGraph workflow engine (T-020, replaces AF.json dispatch)."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph


class WorkflowState(TypedDict, total=False):
    """Shared state flowing through the workflow graph."""

    task_id: str
    skill_id: str
    prompt: str
    context: dict[str, Any]
    node_results: dict[str, Any]
    current_node: str
    status: str
    error: str | None


class WorkflowEngine:
    """
    Sequential workflow orchestrator using LangGraph StateGraph.

    Replaces DevNex's AF.json WorkflowEngine with checkpoint/resume
    via SQLite-backed LangGraph checkpointer.
    """

    def __init__(self, checkpoint_db: str = "deploy/local/data/sqlite/checkpoints.db") -> None:
        self._checkpoint_db = checkpoint_db
        self._graph: StateGraph | None = None
        self._nodes: list[str] = []

    def add_node(self, name: str, fn: Any) -> None:
        self._nodes.append(name)
        if self._graph is None:
            self._graph = StateGraph(WorkflowState)
        self._graph.add_node(name, fn)

    def build_sequential(self) -> None:
        assert self._graph is not None
        assert len(self._nodes) >= 1

        self._graph.set_entry_point(self._nodes[0])
        for i in range(len(self._nodes) - 1):
            self._graph.add_edge(self._nodes[i], self._nodes[i + 1])
        self._graph.add_edge(self._nodes[-1], END)

    async def run(
        self, initial_state: WorkflowState, thread_id: str = "default"
    ) -> WorkflowState:
        assert self._graph is not None
        async with AsyncSqliteSaver.from_conn_string(self._checkpoint_db) as saver:
            compiled = self._graph.compile(checkpointer=saver)
            config = {"configurable": {"thread_id": thread_id}}
            result = await compiled.ainvoke(initial_state, config=config)
            return result  # type: ignore[return-value]

    async def resume(self, thread_id: str) -> WorkflowState:
        assert self._graph is not None
        async with AsyncSqliteSaver.from_conn_string(self._checkpoint_db) as saver:
            compiled = self._graph.compile(checkpointer=saver)
            config = {"configurable": {"thread_id": thread_id}}
            result = await compiled.ainvoke(None, config=config)
            return result  # type: ignore[return-value]
