# tests/test_orchestrator.py
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.orchestrator import DevNexOrchestrator, NodeResult
from core.run_context import DevNexRunContext


class TestDevNexOrchestrator(unittest.TestCase):

    def setUp(self):
        self.run_dir = Path("./test_devnex_run").resolve()
        self.run_dir.mkdir(exist_ok=True)
        self.ctx = DevNexRunContext(
            swc_name="DLT",
            workspace_path=str(self.run_dir),
        )
        self.orch = DevNexOrchestrator(run_context=self.ctx)
        # Seed config so validation passes
        self.orch.config = {
            "SWC_name": "DLT",
            "G_SWDD_TEMP": "G_SWDD_TEMP.csv",
            "SWC_name_C": "DLT.c",
            "SWC_name_H": "DLT.h",
            "SWC_name_TEMP_LLD": "DLT_TEMP_LLD.csv",
            "SWC_name_FUNC_req": "DLT_FUNC_req.csv",
            "SWC_nameInspBaseLLD": "DLTInspBaseLLD.csv",
            "SWC_name_HLD": "DLT_HLD.csv",
            "lds_file": "Linkerscript",
            "map_file": "map File",
            "workspace_path": str(self.run_dir),
        }

    def tearDown(self):
        import shutil
        if self.run_dir.exists():
            try:
                shutil.rmtree(self.run_dir)
            except (PermissionError, OSError):
                # FUSE-mounted filesystems may disallow rmdir — tests still pass
                pass

    def test_run_node_unknown_id_raises(self):
        from core.errors import NodeExecutionError
        with self.assertRaises(NodeExecutionError):
            self.orch.run_node("S99N99")

    @patch("core.orchestrator.StateStore")
    def test_run_s1n2_review_approved(self, _mock_ss):
        self.orch.on_human_review = lambda nid, msg: True
        result = self.orch._run_s1n2_review()
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.node_id, "S1N2")

    @patch("core.orchestrator.StateStore")
    def test_run_s1n2_review_aborted(self, _mock_ss):
        from core.errors import WorkflowAbortedError
        self.orch.on_human_review = lambda nid, msg: False
        with self.assertRaises(WorkflowAbortedError):
            self.orch._run_s1n2_review()

    @patch("core.orchestrator.StateStore")
    def test_run_s1n3_review_approved(self, _mock_ss):
        self.orch.on_human_review = lambda nid, msg: True
        result = self.orch._run_s1n3_review()
        self.assertEqual(result.status, "complete")

    def test_validate_config_raises_on_missing(self):
        from core.errors import ConfigValidationError
        self.orch.config = {"SWC_name": ""}
        with self.assertRaises(ConfigValidationError):
            self.orch._validate_config(["SWC_name"])

    def test_validate_config_passes_when_present(self):
        self.orch.config = {"SWC_name": "DLT"}
        self.orch._validate_config(["SWC_name"])   # should not raise

    def test_render_prompt_replaces_placeholders(self):
        template = "SWC is {{SWC_name}} at {{workspace_path}}."
        rendered = self.orch._render_prompt(template, {"SWC_name": "DLT", "workspace_path": "/tmp"})
        self.assertEqual(rendered, "SWC is DLT at /tmp.")

    def test_load_prompt_returns_fallback_when_missing(self):
        text = self.orch._load_prompt("nonexistent_prompt.md")
        self.assertIn("not found", text)

    @patch("core.orchestrator.DevNexOrchestrator.gca_invoker", new_callable=lambda: property(
        lambda self: MagicMock(invoke_prompt=MagicMock(
            return_value=MagicMock(is_response_valid=True, raw_response="HLD_ID,LLD_ID\nH1,L1")
        ))
    ))
    def test_run_s4n1_writes_artifact(self, _mock_gca):
        artifacts_dir = self.orch._artifacts_dir
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "DLT_FUNC_req.csv").write_text("REQ_ID\nL1", encoding="utf-8")
        result = self.orch._run_s4n1()
        self.assertEqual(result.node_id, "S4N1")
        self.assertEqual(result.status, "complete")


if __name__ == "__main__":
    unittest.main()
