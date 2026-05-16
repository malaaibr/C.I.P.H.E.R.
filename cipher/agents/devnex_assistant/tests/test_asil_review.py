"""test_asil_review.py — UC 3.1: ASIL Code Review Skill test suite.

Classes:
  TestAsilViolationParsing   — JSON violation parsing from Ollama TRIAGE output
  TestAsilReviewPhases       — Phase 1/2/3/4 with mocked LLM backends
  TestAsilGateIntegration    — Gate enforcement per ASIL level
  TestAsilReportGeneration   — Artefact writing + MD report structure
  TestAsilReviewIntegration  — End-to-end with real temp .c file
"""
from __future__ import annotations

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from skills.automotive.asil_review_skill import (
    AsilReviewSkill, AsilViolation, AsilReviewReport,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_C = """\
#include <stdint.h>
// Bad: casts away volatile
void write_reg(volatile uint32_t *reg, uint32_t val) {
    *((uint32_t *)reg) = val;   // R11.8 violation
    if (1) {                    // R14.4 — non-Boolean controlling expr
        malloc(64);             // R21.3 — dynamic memory
    }
}
"""

SAMPLE_OLLAMA_JSON = json.dumps([
    {"file": "test.c", "line": 4, "rule": "R11.8", "severity": "CRITICAL",
     "description": "Cast removes volatile qualifier", "fix_hint": "Remove cast"},
    {"file": "test.c", "line": 5, "rule": "R14.4", "severity": "MAJOR",
     "description": "Controlling expression is not Boolean", "fix_hint": "Use explicit comparison"},
    {"file": "test.c", "line": 6, "rule": "R21.3", "severity": "CRITICAL",
     "description": "Dynamic memory allocation forbidden", "fix_hint": "Use static allocation"},
])


# ─────────────────────────────────────────────────────────────────────────────
# TestAsilViolationParsing
# ─────────────────────────────────────────────────────────────────────────────
class TestAsilViolationParsing:
    def test_parse_valid_json_array(self):
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        assert len(violations) == 3

    def test_parse_critical_count(self):
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        criticals = [v for v in violations if v.severity == "CRITICAL"]
        assert len(criticals) == 2

    def test_parse_rule_ids(self):
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        rules = {v.rule for v in violations}
        assert "R11.8" in rules
        assert "R21.3" in rules

    def test_parse_empty_array(self):
        violations = AsilReviewSkill._parse_violations("[]", "test.c")
        assert violations == []

    def test_parse_malformed_json_returns_empty(self):
        violations = AsilReviewSkill._parse_violations("not json at all", "test.c")
        assert violations == []

    def test_parse_partial_json_with_text(self):
        raw = f"Here are the violations:\n{SAMPLE_OLLAMA_JSON}\nEnd."
        violations = AsilReviewSkill._parse_violations(raw, "test.c")
        assert len(violations) == 3

    def test_violation_line_is_int(self):
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        for v in violations:
            assert isinstance(v.line, int)


# ─────────────────────────────────────────────────────────────────────────────
# TestAsilReviewPhases
# ─────────────────────────────────────────────────────────────────────────────
class TestAsilReviewPhases:
    def _make_skill(self):
        mock_orch = MagicMock()
        mock_orch.config = {"SWC_name": "TestSWC"}
        return AsilReviewSkill(orchestrator=mock_orch)

    def test_phase1_triage_calls_ollama(self, tmp_path):
        skill = self._make_skill()
        src = tmp_path / "test.c"
        src.write_text(SAMPLE_C)
        with patch.object(skill, "_call_ollama", return_value=SAMPLE_OLLAMA_JSON) as mock_ollama:
            violations = skill._phase1_triage(src, "B")
        mock_ollama.assert_called_once()
        assert len(violations) == 3

    def test_phase2_plan_calls_gemini(self, tmp_path):
        skill = self._make_skill()
        src = tmp_path / "test.c"
        src.write_text(SAMPLE_C)
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        with patch.object(skill, "_call_gemini", return_value="Fix plan: step 1...") as mock_gem:
            plan = skill._phase2_plan(src, violations, "D")
        mock_gem.assert_called_once()
        assert "Fix" in plan

    def test_phase2_returns_no_plan_when_no_violations(self, tmp_path):
        skill = self._make_skill()
        src = tmp_path / "clean.c"
        src.write_text("void f(){}")
        plan = skill._phase2_plan(src, [], "B")
        assert "No violations" in plan

    def test_phase3_codegen_calls_gca(self, tmp_path):
        skill = self._make_skill()
        src = tmp_path / "test.c"
        src.write_text(SAMPLE_C)
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")

        mock_result = MagicMock()
        mock_result.is_response_valid = True
        mock_result.raw_response = "--- a/test.c\n+++ b/test.c\n@@ fix1 @@\n---DIFF---\n--- a/test.c\n+++ b/test.c\n@@ fix2 @@"
        skill._orch.gca_invoker.invoke_prompt.return_value = mock_result

        diffs = skill._phase3_codegen(src, violations, "fix plan", "D")
        assert len(diffs) == 2
        skill._orch.gca_invoker.invoke_prompt.assert_called_once()

    def test_phase3_returns_empty_when_no_orchestrator(self, tmp_path):
        skill = AsilReviewSkill(orchestrator=None)
        src = tmp_path / "test.c"
        src.write_text(SAMPLE_C)
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        diffs = skill._phase3_codegen(src, violations, "plan", "B")
        assert diffs == []


# ─────────────────────────────────────────────────────────────────────────────
# TestAsilGateIntegration
# ─────────────────────────────────────────────────────────────────────────────
class TestAsilGateIntegration:
    def _run_review(self, tmp_path, asil, ollama_json):
        skill = AsilReviewSkill(orchestrator=None)
        src = tmp_path / "comp.c"
        src.write_text(SAMPLE_C)
        with patch.object(skill, "_call_ollama", return_value=ollama_json):
            with patch.object(skill, "_call_gemini", return_value="plan"):
                return skill.run(src, asil_target=asil, artifacts_dir=tmp_path)

    def test_asil_d_hard_block_on_critical(self, tmp_path):
        from gcl.asil_gate import SemanticConflictError
        with pytest.raises(SemanticConflictError):
            self._run_review(tmp_path, "D", SAMPLE_OLLAMA_JSON)

    def test_asil_c_no_raise_returns_report(self, tmp_path):
        report = self._run_review(tmp_path, "C", SAMPLE_OLLAMA_JSON)
        assert report.asil_target == "C"
        assert report.gate_decision in ("HOLD", "HARD_BLOCK", "WARN")

    def test_asil_b_no_raise_on_clean_source(self, tmp_path):
        clean_json = "[]"
        report = self._run_review(tmp_path, "B", clean_json)
        assert report.critical_count == 0
        assert report.compliance_badge == "COMPLIANT"
        assert report.gate_decision == "PASS"

    def test_asil_d_passes_when_no_violations(self, tmp_path):
        clean_json = "[]"
        report = self._run_review(tmp_path, "D", clean_json)
        assert report.gate_decision == "PASS"
        assert report.compliance_badge == "COMPLIANT"


# ─────────────────────────────────────────────────────────────────────────────
# TestAsilReportGeneration
# ─────────────────────────────────────────────────────────────────────────────
class TestAsilReportGeneration:
    def test_json_artifact_written(self, tmp_path):
        skill = AsilReviewSkill(orchestrator=None)
        src = tmp_path / "comp.c"
        src.write_text("void f(){}")
        with patch.object(skill, "_call_ollama", return_value="[]"):
            with patch.object(skill, "_call_gemini", return_value=""):
                skill.run(src, asil_target="B", artifacts_dir=tmp_path)
        assert (tmp_path / "asil_review_comp.json").exists()

    def test_md_artifact_written(self, tmp_path):
        skill = AsilReviewSkill(orchestrator=None)
        src = tmp_path / "comp.c"
        src.write_text("void f(){}")
        with patch.object(skill, "_call_ollama", return_value="[]"):
            with patch.object(skill, "_call_gemini", return_value=""):
                skill.run(src, asil_target="B", artifacts_dir=tmp_path)
        md = tmp_path / "asil_review_comp.md"
        assert md.exists()
        content = md.read_text()
        assert "ASIL Review Report" in content

    def test_md_report_contains_all_sections(self, tmp_path):
        skill = AsilReviewSkill(orchestrator=None)
        violations = AsilReviewSkill._parse_violations(SAMPLE_OLLAMA_JSON, "test.c")
        report = AsilReviewReport(
            source_file="test.c", asil_target="D",
            total_violations=3, critical_count=2, major_count=1, minor_count=0,
            gate_decision="HARD_BLOCK", compliance_badge="NOT_COMPLIANT",
            rationale="critical violations present",
        )
        md = skill._build_md_report(report, violations)
        assert "## Violations" in md
        assert "## Gate Rationale" in md
        assert "## Resolution Steps" in md
        assert "R11.8" in md

    def test_json_artifact_parseable(self, tmp_path):
        skill = AsilReviewSkill(orchestrator=None)
        src = tmp_path / "comp.c"
        src.write_text("void f(){}")
        with patch.object(skill, "_call_ollama", return_value="[]"):
            with patch.object(skill, "_call_gemini", return_value=""):
                skill.run(src, asil_target="A", artifacts_dir=tmp_path)
        data = json.loads((tmp_path / "asil_review_comp.json").read_text())
        assert "asil_target" in data
        assert "violations" in data
