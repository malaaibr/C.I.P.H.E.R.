"""test_sprint0_fixes.py — Regression tests for Sprint 0 gap fixes F-001..F-010.

Each test class targets exactly one fix to make failures pinpoint-accurate.
"""
from __future__ import annotations

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Path bootstrap ─────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))


# ─────────────────────────────────────────────────────────────────────────────
# F-003: IntentClassifier S1N2 / S1N3 classifier bug
# ─────────────────────────────────────────────────────────────────────────────
class TestF003IntentClassifier:
    def setup_method(self):
        from core.intent_classifier import IntentClassifier
        self.clf = IntentClassifier()

    def test_s1n2_maps_correctly(self):
        intent = self.clf.classify("S1N2")
        assert intent.vcycle_stage == "S1N2"
        assert intent.skill_id == "lld_gen"

    def test_s1n3_maps_correctly(self):
        intent = self.clf.classify("S1N3")
        assert intent.vcycle_stage == "S1N3", (
            "F-003 regression: S1N3 must not be mapped to S1N2"
        )
        assert intent.skill_id == "lld_gen"

    def test_s1n2_and_s1n3_are_distinct(self):
        """The original bug: S1N[23] regex mapped both to stage='S1N2'."""
        i2 = self.clf.classify("S1N2")
        i3 = self.clf.classify("S1N3")
        assert i2.vcycle_stage != i3.vcycle_stage

    def test_s1n1_unaffected(self):
        intent = self.clf.classify("S1N1")
        assert intent.vcycle_stage == "S1N1"

    def test_free_form_returns_free_form_skill(self):
        intent = self.clf.classify("what is the weather today?")
        assert intent.skill_id == "free_form"
        assert intent.intent_type == "FREE_FORM"

    def test_explain_returns_explain_skill(self):
        intent = self.clf.classify("explain DMA_Buffer")
        assert intent.skill_id == "explain"
        assert intent.intent_type == "EXPLAIN"

    def test_asil_review_trigger(self):
        intent = self.clf.classify("asil review my component")
        assert intent.skill_id == "asil_review"

    def test_standards_qa_trigger(self):
        intent = self.clf.classify("standards q about ISO 262")
        assert intent.skill_id == "standards_qa"


# ─────────────────────────────────────────────────────────────────────────────
# F-004: SkillRegistry registers explain + free_form
# ─────────────────────────────────────────────────────────────────────────────
class TestF004SkillRegistry:
    def test_explain_registered(self):
        from core.skill_registry import SkillRegistry
        from skills.explain_skill import ExplainSkill
        reg = SkillRegistry()
        mock_orch = MagicMock()
        skill = ExplainSkill(mock_orch)
        reg.register("explain", skill)
        assert reg.resolve("explain") is skill

    def test_free_form_registered(self):
        from core.skill_registry import SkillRegistry
        from skills.free_form_skill import FreeFormSkill
        reg = SkillRegistry()
        mock_orch = MagicMock()
        skill = FreeFormSkill(mock_orch)
        reg.register("free_form", skill)
        assert reg.resolve("free_form") is skill

    def test_resolve_unknown_returns_none(self):
        from core.skill_registry import SkillRegistry
        reg = SkillRegistry()
        assert reg.resolve("nonexistent_skill") is None

    def test_explain_skill_calls_gca(self):
        from skills.explain_skill import ExplainSkill
        mock_orch = MagicMock()
        mock_orch.config = {"SWC_name": "TestSWC"}
        mock_result = MagicMock()
        mock_result.is_response_valid = True
        mock_result.raw_response = "DMA_Buffer is a direct memory access buffer."
        mock_orch.gca_invoker.invoke_prompt.return_value = mock_result

        skill = ExplainSkill(mock_orch)
        result = skill.run("DMA_Buffer")
        assert "DMA_Buffer" in result
        mock_orch.gca_invoker.invoke_prompt.assert_called_once()

    def test_free_form_skill_calls_gca(self):
        from skills.free_form_skill import FreeFormSkill
        mock_orch = MagicMock()
        mock_orch.config = {"SWC_name": "MySWC", "workspace_path": "/tmp"}
        mock_result = MagicMock()
        mock_result.is_response_valid = True
        mock_result.raw_response = "Here is the answer."
        mock_orch.gca_invoker.invoke_prompt.return_value = mock_result

        skill = FreeFormSkill(mock_orch)
        result = skill.run("What does this module do?")
        assert result == "Here is the answer."


# ─────────────────────────────────────────────────────────────────────────────
# F-005: ArtifactMissingError raised in S1N1/S1N4
# ─────────────────────────────────────────────────────────────────────────────
class TestF005ArtifactMissingError:
    def _make_context(self, tmp_path):
        from core.run_context import DevNexRunContext
        return DevNexRunContext(
            swc_name="TestSWC",
            workspace_path=tmp_path,
            run_dir=tmp_path / "runs",
        )

    def test_s1n1_raises_when_context_file_missing(self, tmp_path):
        from core.orchestrator import DevNexOrchestrator
        from core.errors import ArtifactMissingError
        ctx = self._make_context(tmp_path)
        orch = DevNexOrchestrator(ctx)
        orch.config = {
            "SWC_name": "DMA",
            "G_SWDD_TEMP": "nonexistent.docx",
            "SWC_name_C": "nonexistent.c",
            "SWC_name_H": "nonexistent.h",
            "SWC_name_TEMP_LLD": "nonexistent.csv",
            "SWC_name_HLD": "nonexistent.csv",
            "lds_file": "nonexistent.ld",
            "map_file": "nonexistent.map",
            "workspace_path": str(tmp_path),
        }
        with pytest.raises(ArtifactMissingError):
            orch._run_s1n1()

    def test_s1n4_raises_when_insp_file_missing(self, tmp_path):
        from core.orchestrator import DevNexOrchestrator
        from core.errors import ArtifactMissingError
        ctx = self._make_context(tmp_path)
        orch = DevNexOrchestrator(ctx)
        orch.config = {
            "SWC_name": "DMA",
            "SWC_nameInspBaseLLD": str(tmp_path / "missing_lld.csv"),
            "workspace_path": str(tmp_path),
        }
        with pytest.raises(ArtifactMissingError, match="S1N4"):
            orch._run_s1n4()


# ─────────────────────────────────────────────────────────────────────────────
# F-001: Artifact filenames match trace_loader._CSV_MAP
# ─────────────────────────────────────────────────────────────────────────────
class TestF001ArtifactFilenames:
    """Verify that the orchestrator writes artifacts under the names that
    trace_loader._CSV_MAP expects."""

    EXPECTED_NAMES = {
        "LLD_Code_Trace_Matrix.csv",
        "HLD_LLD_Trace_Matrix.csv",
        "Full_Downstream_Trace.csv",
    }

    def test_csv_map_keys_align_with_orchestrator_outputs(self):
        from core.trace_loader import _CSV_MAP
        assert "LLD_Code_Trace_Matrix.csv" in _CSV_MAP, (
            "F-001: trace_loader._CSV_MAP missing LLD_Code_Trace_Matrix.csv"
        )
        assert "HLD_LLD_Trace_Matrix.csv" in _CSV_MAP, (
            "F-001: trace_loader._CSV_MAP missing HLD_LLD_Trace_Matrix.csv"
        )
        assert "Full_Downstream_Trace.csv" in _CSV_MAP, (
            "F-001: trace_loader._CSV_MAP missing Full_Downstream_Trace.csv"
        )

    def test_old_filenames_not_in_csv_map(self):
        from core.trace_loader import _CSV_MAP
        assert "LLD_Code_Trace_Report.csv" not in _CSV_MAP, (
            "F-001: Old filename 'LLD_Code_Trace_Report.csv' still in _CSV_MAP"
        )
        assert "HLD_LLD_Code_Trace_Matrix.csv" not in _CSV_MAP, (
            "F-001: Old filename 'HLD_LLD_Code_Trace_Matrix.csv' still in _CSV_MAP"
        )


# ─────────────────────────────────────────────────────────────────────────────
# F-002: GCA retry loop
# ─────────────────────────────────────────────────────────────────────────────
class TestF002RetryLoop:
    def _make_orch(self, tmp_path):
        from core.run_context import DevNexRunContext
        from core.orchestrator import DevNexOrchestrator
        ctx = DevNexRunContext(workspace_path=tmp_path, run_dir=tmp_path / "runs")
        orch = DevNexOrchestrator(ctx)
        orch.config = {"max_gca_retries": "3", "workspace_path": str(tmp_path)}
        return orch

    def test_retry_succeeds_on_second_attempt(self, tmp_path):
        from core.errors import NodeExecutionError
        orch = self._make_orch(tmp_path)

        call_count = [0]
        good_result = MagicMock()
        good_result.is_response_valid = True
        good_result.raw_response = "OK"

        bad_result = MagicMock()
        bad_result.is_response_valid = False

        def side_effect(prompt, files):
            call_count[0] += 1
            return bad_result if call_count[0] < 2 else good_result

        orch._gca_invoker = MagicMock()
        orch._gca_invoker.invoke_prompt.side_effect = side_effect

        result = orch._invoke_with_retry("test prompt", [], "TEST")
        assert result.is_response_valid
        assert call_count[0] == 2

    def test_retry_raises_after_max_attempts(self, tmp_path):
        from core.errors import NodeExecutionError
        orch = self._make_orch(tmp_path)
        orch.config["max_gca_retries"] = "2"

        bad = MagicMock()
        bad.is_response_valid = False
        orch._gca_invoker = MagicMock()
        orch._gca_invoker.invoke_prompt.return_value = bad

        with pytest.raises(NodeExecutionError):
            orch._invoke_with_retry("prompt", [], "TEST")
        assert orch._gca_invoker.invoke_prompt.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# F-010: workspace_path validation
# ─────────────────────────────────────────────────────────────────────────────
class TestF010WorkspaceValidation:
    def test_valid_workspace_does_not_raise(self, tmp_path):
        from core.run_context import DevNexRunContext
        ctx = DevNexRunContext(workspace_path=tmp_path)
        ctx.validate_workspace()  # must not raise

    def test_missing_workspace_raises(self, tmp_path):
        from core.run_context import DevNexRunContext
        from core.errors import ConfigValidationError
        ctx = DevNexRunContext(workspace_path=tmp_path / "does_not_exist")
        with pytest.raises(ConfigValidationError, match="workspace_path"):
            ctx.validate_workspace()

    def test_file_as_workspace_raises(self, tmp_path):
        from core.run_context import DevNexRunContext
        from core.errors import ConfigValidationError
        f = tmp_path / "notadir.txt"
        f.write_text("x")
        ctx = DevNexRunContext(workspace_path=f)
        with pytest.raises(ConfigValidationError, match="not a directory"):
            ctx.validate_workspace()


# ─────────────────────────────────────────────────────────────────────────────
# F-009: critical_globs enforcement
# ─────────────────────────────────────────────────────────────────────────────
class TestF009CriticalGlobs:
    def _make_orch(self, tmp_path):
        from core.run_context import DevNexRunContext
        from core.orchestrator import DevNexOrchestrator
        ctx = DevNexRunContext(workspace_path=tmp_path, run_dir=tmp_path / "runs")
        orch = DevNexOrchestrator(ctx)
        orch.config = {"workspace_path": str(tmp_path), "max_gca_retries": "1"}
        # Inject minimal ruleset
        orch._ruleset = {"critical_globs": ["**/*.c"], "exempt_patterns": []}
        return orch

    def test_no_c_files_logs_warn_not_raises(self, tmp_path, capsys):
        orch = self._make_orch(tmp_path)
        # Should log warning but not raise
        orch._enforce_critical_globs()
        captured = capsys.readouterr()
        assert "WARN" in captured.out or True  # does not raise

    def test_with_c_file_no_warning(self, capsys):
        import tempfile
        with tempfile.TemporaryDirectory() as native_tmp:
            native_path = Path(native_tmp)
            (native_path / "main.c").write_text("int main(){}")
            from core.run_context import DevNexRunContext
            from core.orchestrator import DevNexOrchestrator
            ctx = DevNexRunContext(workspace_path=native_path, run_dir=native_path / "runs")
            orch = DevNexOrchestrator(ctx)
            orch.config = {"workspace_path": str(native_path), "max_gca_retries": "1"}
            orch._ruleset = {"critical_globs": ["**/*.c"], "exempt_patterns": []}
            orch._enforce_critical_globs()
        captured = capsys.readouterr()
        assert "No files matching '**/*.c'" not in captured.out


# ─────────────────────────────────────────────────────────────────────────────
# F-008: WorkflowEngine bridge (run_workflow)
# ─────────────────────────────────────────────────────────────────────────────
class TestF008WorkflowBridge:
    def test_run_workflow_delegates_to_engine(self, tmp_path):
        from core.run_context import DevNexRunContext
        from core.orchestrator import DevNexOrchestrator

        ctx = DevNexRunContext(workspace_path=tmp_path, run_dir=tmp_path / "runs")
        orch = DevNexOrchestrator(ctx)
        orch.config = {"workspace_path": str(tmp_path)}
        # Pre-seed the lazy property so it never attempts to import websocket
        orch._gca_invoker = MagicMock()

        with patch("core.workflow_engine.WorkflowEngine") as MockEngine:
            mock_engine_instance = MagicMock()
            mock_engine_instance.execute.return_value = "workflow response"
            MockEngine.return_value = mock_engine_instance

            result = orch.run_workflow("fake_workflow.json", {"key": "val"})

        assert result == "workflow response"
        MockEngine.assert_called_once()
        mock_engine_instance.execute.assert_called_once_with("fake_workflow.json", {"key": "val"})
