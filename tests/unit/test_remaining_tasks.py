"""Unit tests for T-028 through T-034."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cipher.core.schemas.devnex_types import (
    BridgeRequest,
    BridgeResponse,
    NodeResult,
    NodeStatus,
    SkillManifest,
    VCycleStage,
    WorkflowDefinition,
)
from cipher.gui.panels.devnex.panel_descriptor import DEVNEX_PANEL, PanelDescriptor


class TestLangfuseCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        from cipher.pkl.observability.langfuse_check import langfuse_health_check

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await langfuse_health_check("http://localhost:3000")
            assert result is True


class TestDevNexTypes:
    def test_node_result_round_trip(self) -> None:
        nr = NodeResult(
            node_id="s1n1",
            stage=VCycleStage.S1N1,
            status=NodeStatus.COMPLETED,
            output={"rows": 5},
            duration_ms=1200.0,
        )
        restored = NodeResult.model_validate_json(nr.model_dump_json())
        assert restored.stage == VCycleStage.S1N1
        assert restored.status == NodeStatus.COMPLETED

    def test_skill_manifest(self) -> None:
        sm = SkillManifest(
            skill_id="vcycle_s1n1",
            name="S1N1 LLD Generation",
            description="Generates LLD from HLD",
            v_cycle_stages=[VCycleStage.S1N1],
            required_backends=["gca_http"],
        )
        assert sm.version == "0.1.0"
        payload = sm.model_dump_json()
        restored = SkillManifest.model_validate_json(payload)
        assert restored.required_backends == ["gca_http"]

    def test_workflow_definition(self) -> None:
        wd = WorkflowDefinition(
            workflow_id="poc-spine",
            name="POC Spine",
            description="Sequential S1N1 workflow",
            nodes=["classify", "generate", "store"],
            edges=[("classify", "generate"), ("generate", "store")],
            entry_point="classify",
        )
        restored = WorkflowDefinition.model_validate_json(wd.model_dump_json())
        assert len(restored.edges) == 2

    def test_bridge_request_response(self) -> None:
        req = BridgeRequest(prompt="generate LLD", workspace_hint="/ws")
        assert req.timeout_s == 300.0

        resp = BridgeResponse(
            text="generated code",
            instance_id="abc",
            duration_ms=1500.0,
            request_id=req.request_id,
        )
        assert resp.request_id == req.request_id


class TestPanelDescriptor:
    def test_devnex_panel_descriptor(self) -> None:
        assert DEVNEX_PANEL.panel_id == "devnex-workflow"
        assert DEVNEX_PANEL.agent_id == "devnex-001"
        assert DEVNEX_PANEL.title == "DevNex V-Cycle"


class TestCipherShell:
    def test_shell_creates(self, qtbot) -> None:
        from cipher.gui.shell.main_window import CipherShell

        shell = CipherShell()
        qtbot.addWidget(shell)
        assert shell.windowTitle() == "C.I.P.H.E.R — Agentic Development Platform"
        assert shell.list_panels() == []

    def test_mount_and_unmount_panel(self, qtbot) -> None:
        from PyQt6.QtWidgets import QLabel

        from cipher.gui.shell.main_window import CipherShell

        shell = CipherShell()
        qtbot.addWidget(shell)

        panel_widget = QLabel("Test Panel Content")
        shell.mount_panel("test-panel", panel_widget, "Test Panel")
        assert "test-panel" in shell.list_panels()

        shell.unmount_panel("test-panel")
        assert shell.list_panels() == []


class TestDevNexWorkflowWidget:
    def test_widget_creates(self, qtbot) -> None:
        from cipher.gui.panels.devnex.workflow_widget import DevNexWorkflowWidget

        widget = DevNexWorkflowWidget()
        qtbot.addWidget(widget)
        assert widget._submit_btn.text() == "Generate LLD"

    def test_submit_emits_signal(self, qtbot) -> None:
        from cipher.gui.panels.devnex.workflow_widget import DevNexWorkflowWidget

        widget = DevNexWorkflowWidget()
        qtbot.addWidget(widget)
        widget._prompt_input.setPlainText("Test HLD prompt")

        with qtbot.waitSignal(widget.task_submitted, timeout=1000):
            widget._submit_btn.click()


class TestCipherShellClient:
    @pytest.mark.asyncio
    async def test_submit_task(self) -> None:
        from cipher.core.schemas.task_contract import TaskClass, TaskContract
        from cipher.gui.client.a2a_client import CipherShellClient

        task = TaskContract(
            task_class=TaskClass.CODE_GEN,
            skill_id="vcycle_s1n1",
            prompt="test",
            requester_agent_id="shell",
            target_agent_id="devnex",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"task_id": str(task.task_id)}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            client = CipherShellClient("http://localhost:8000")
            result_id = await client.submit_task(task)
            assert result_id == task.task_id
