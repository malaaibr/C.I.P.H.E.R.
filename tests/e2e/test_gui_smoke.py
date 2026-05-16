"""
GUI E2E Smoke Test (T-034).

Verifies: Shell launches, DevNex panel loads, workflow submission works.
Uses pytest-qt for headless widget testing.
"""

from __future__ import annotations

import pytest

from cipher.gui.panels.devnex.panel_descriptor import DEVNEX_PANEL
from cipher.gui.panels.devnex.workflow_widget import DevNexWorkflowWidget
from cipher.gui.shell.main_window import CipherShell


pytestmark = pytest.mark.e2e


class TestGUISmoke:
    def test_shell_launches(self, qtbot) -> None:
        shell = CipherShell()
        qtbot.addWidget(shell)
        assert shell.isVisible() is False  # not shown until .show()
        shell.show()
        assert shell.windowTitle() == "C.I.P.H.E.R — Agentic Development Platform"
        assert shell.minimumWidth() == 1280

    def test_devnex_panel_mounts(self, qtbot) -> None:
        shell = CipherShell()
        qtbot.addWidget(shell)

        widget = DevNexWorkflowWidget()
        shell.mount_panel(
            DEVNEX_PANEL.panel_id,
            widget,
            DEVNEX_PANEL.title,
        )
        assert DEVNEX_PANEL.panel_id in shell.list_panels()

    def test_workflow_submission_signal(self, qtbot) -> None:
        widget = DevNexWorkflowWidget()
        qtbot.addWidget(widget)

        widget._prompt_input.setPlainText(
            "Generate LLD for automotive ECU power management module"
        )

        with qtbot.waitSignal(widget.task_submitted, timeout=1000) as sig:
            widget._submit_btn.click()

        assert "ECU" in sig.args[0]
        assert widget._status_label.text() == "Status: Submitting..."

    def test_panel_unmount(self, qtbot) -> None:
        shell = CipherShell()
        qtbot.addWidget(shell)

        widget = DevNexWorkflowWidget()
        shell.mount_panel("test-panel", widget, "Test")
        assert "test-panel" in shell.list_panels()

        shell.unmount_panel("test-panel")
        assert shell.list_panels() == []
