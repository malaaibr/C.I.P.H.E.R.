"""uc4_4_skill.py — UC 4.4 Skill Orchestrator

Implements the full UC 4.4 pipeline: Semantic Conflict — Memory Map Overlap
Undetected by Git.

Pipeline (M1 -> M5):
  M1   map_analyzer         -> section_layout.json
  M1b  linker_script_parser -> declared_regions.json
  M2   ram_overlap_detector -> overlap_report.json
  M3   asil_gate.enforce()  -> ASIL-D hard block
  M4   gca_invoker          -> semantic_conflict_report.md
  M5   Safety Engineer G5 gate (human review)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

# Python 3.10/3.11 compat — console_logging uses datetime.UTC (3.11+)
try:
    from core.console_logging import format_console_log, utc_timestamp
    _USE_CONSOLE_LOG = True
except (ImportError, AttributeError):
    _USE_CONSOLE_LOG = False

    def format_console_log(module, level, msg, ts="", caller=""):
        return f"[{level}] {module}: {msg}"

    def utc_timestamp():
        from datetime import datetime, timezone
        return datetime.now(tz=timezone.utc).isoformat()


from core.errors import NodeExecutionError, ArtifactMissingError
from gcl.asil_gate import AsilDecision, AsilGate, SemanticConflictError
from skills.automotive.map_analyzer import MapAnalyzer
from skills.automotive.ram_overlap_detector import OverlapReport, RamOverlapDetector
from skills.automotive.linker_script_parser import LinkerScriptParser

MODULE_NAME = "UC4_4_Skill"


class UC44SemanticConflictSkill:
    """UC 4.4 — Semantic Memory Map Overlap Detector.

    Parameters
    ----------
    run_context :
        Provides `config` dict and `get_artifacts_path()` method.
    gca_invoker :
        Optional GCA invoker. When None, M4 uses built-in fallback report.
    on_log :
        Optional logging callback (message, level).
    """

    def __init__(self, run_context, gca_invoker=None, on_log=None):
        self._ctx       = run_context
        self._gca       = gca_invoker
        self._on_log    = on_log or (lambda *_: None)
        self._artifacts = run_context.get_artifacts_path()
        self._artifacts.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self):
        """Execute full UC 4.4 pipeline.

        Returns dict with status, artifact paths, gca_report.
        Raises SemanticConflictError on ASIL-D hard block.
        Raises ArtifactMissingError when .map or .ld file not found.
        """
        cfg      = getattr(self._ctx, "config", {})
        map_path = self._resolve("map_file", cfg)
        lds_path = self._resolve("lds_file", cfg)
        asil     = cfg.get("asil_level", "D").upper()

        self._log(f"UC 4.4 starting | map={map_path.name} | lds={lds_path.name} | ASIL={asil}")

        # M1 — parse .map
        self._log("M1: Parsing linker map file...")
        analyzer    = MapAnalyzer()
        layout      = analyzer.parse(map_path)
        layout_path = self._artifacts / "section_layout.json"
        analyzer.write_json(layout, layout_path)
        self._log(f"M1: {layout.total_sections} sections, {layout.total_ram_sections} in RAM")

        # M1b — parse .ld
        self._log("M1b: Parsing linker script...")
        ld_parser    = LinkerScriptParser()
        ld_layout    = ld_parser.parse(lds_path)
        regions_path = self._artifacts / "declared_regions.json"
        ld_parser.write_json(ld_layout, regions_path)
        self._log(f"M1b: {len(ld_layout.regions)} memory regions declared")

        # M2 — detect overlaps
        self._log("M2: Running RAM overlap detector...")
        detector    = RamOverlapDetector(asil_level=asil)
        overlap_rpt = detector.run(layout_path)
        overlap_path = self._artifacts / "overlap_report.json"
        detector.write_json(overlap_rpt, overlap_path)

        if overlap_rpt.has_overlap:
            self._log(
                f"M2 OVERLAP: {len(overlap_rpt.overlaps)} collision(s), "
                f"{overlap_rpt.total_overlapping_bytes} bytes",
                level="ERROR",
            )
        else:
            self._log("M2: No RAM overlaps detected.")

        # M3 — ASIL gate evaluation
        self._log(f"M3: Evaluating ASIL-{asil} gate...")
        gate     = AsilGate(asil)
        decision = gate.evaluate(overlap_rpt.has_overlap)
        self._log(
            f"M3: {decision.action} | gate={decision.gate} | safety_eng={decision.require_safety_engineer}",
            level="WARN" if decision.is_blocking else "INFO",
        )

        gate_path = self._artifacts / "asil_gate_decision.json"
        gate_path.write_text(json.dumps({
            "asil_level":              decision.asil_level,
            "has_overlap":             decision.has_overlap,
            "action":                  decision.action,
            "gate":                    decision.gate,
            "require_safety_engineer": decision.require_safety_engineer,
            "rationale":               decision.rationale,
        }, indent=2), encoding="utf-8")

        # M4 — GCA report (generated BEFORE hard block so artifact exists)
        gca_report = ""
        if overlap_rpt.has_overlap:
            gca_report = self._run_m4_gca(overlap_rpt, decision, asil)

        # M3 enforcement — hard block after artifact write
        if decision.action == "HARD_BLOCK":
            raise SemanticConflictError(
                f"[ASIL-{asil} HARD BLOCK] {decision.rationale}\n"
                f"Overlap report: {overlap_path}\n"
                f"GCA report: {self._artifacts / 'semantic_conflict_report.md'}"
            )

        return {
            "status":              "blocked" if decision.is_blocking else "pass",
            "has_overlap":         overlap_rpt.has_overlap,
            "section_layout_path": str(layout_path),
            "overlap_report_path": str(overlap_path),
            "gate_decision_path":  str(gate_path),
            "asil_decision":       decision.action,
            "gca_report":          gca_report,
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _resolve(self, key, cfg):
        raw = cfg.get(key, "")
        if not raw:
            raise ArtifactMissingError(
                f"UC 4.4: Required config key '{key}' is missing."
            )
        p = Path(raw)
        if not p.is_absolute():
            p = Path(cfg.get("workspace_path", ".")) / p
        if not p.exists():
            raise ArtifactMissingError(
                f"UC 4.4: '{key}' file not found at '{p}'."
            )
        return p

    def _run_m4_gca(self, overlap_rpt, decision, asil):
        self._log("M4: Generating semantic conflict report...")
        prompt     = self._build_gca_prompt(overlap_rpt, decision, asil)
        report_md  = ""

        if self._gca is not None:
            try:
                result = self._gca.invoke_prompt(prompt, [])
                if result.is_response_valid:
                    report_md = result.raw_response
                else:
                    report_md = self._built_in_report(overlap_rpt, decision)
            except Exception as exc:
                self._log(f"M4: GCA failed ({exc}), using fallback.", level="WARN")
                report_md = self._built_in_report(overlap_rpt, decision)
        else:
            self._log("M4: No GCA — using built-in report.", level="WARN")
            report_md = self._built_in_report(overlap_rpt, decision)

        rpt_path = self._artifacts / "semantic_conflict_report.md"
        rpt_path.write_text(report_md, encoding="utf-8")
        self._log(f"M4: Report written -> {rpt_path}")
        return report_md

    @staticmethod
    def _build_gca_prompt(overlap_rpt, decision, asil):
        lines = "\n".join(f"  - {ov.summary}" for ov in overlap_rpt.overlaps)
        return (
            f"ISO 26262 ASIL-{asil} safety review for CIPHER AI Integrator.\n\n"
            f"Gate Decision: {decision.action}\n"
            f"Rationale: {decision.rationale}\n\n"
            f"Detected RAM Overlaps:\n{lines}\n\n"
            "Generate a formal SEMANTIC CONFLICT REPORT in Markdown with:\n"
            "1. Executive Summary\n"
            "2. Conflict Details table (Section A | Section B | Overlap Range | Bytes)\n"
            "3. MISRA-C Violations (R1.3, R11.8)\n"
            "4. Impact Assessment\n"
            "5. Resolution Steps\n"
            "6. Safety Engineer G5 Checklist"
        )

    @staticmethod
    def _built_in_report(overlap_rpt, decision):
        lines = [
            "# SEMANTIC CONFLICT REPORT — UC 4.4",
            "",
            f"**ASIL Level:** {overlap_rpt.asil_level}",
            f"**Decision:** {decision.action}  |  **Gate:** {decision.gate}",
            f"**Safety Engineer Required:** {decision.require_safety_engineer}",
            "",
            "## Detected Overlaps",
            "",
        ]
        for ov in overlap_rpt.overlaps:
            lines += [
                f"| Field | Value |",
                f"|-------|-------|",
                f"| Section A | `{ov.section_a}` [0x{ov.a_start:08X}–0x{ov.a_end-1:08X}] |",
                f"| Section B | `{ov.section_b}` [0x{ov.b_start:08X}–0x{ov.b_end-1:08X}] |",
                f"| Overlap | 0x{ov.overlap_start:08X}–0x{ov.overlap_end-1:08X} ({ov.overlap_size} bytes) |",
                f"| Action | {ov.asil_action} |",
                "",
            ]
        lines += [
            "## Rationale", "", decision.rationale, "",
            "## Resolution",
            "1. Adjust linker script so DMA_Buffer and ISR_Stack have non-overlapping ranges.",
            "2. Re-run UC 4.4 post-merge check to confirm clean.",
            "3. Safety Engineer G5 sign-off required before merge.",
        ]
        return "\n".join(lines)

    def _log(self, message, level="INFO"):
        line = format_console_log(MODULE_NAME, level, message, utc_timestamp(), "run")
        print(line)
        self._on_log(message, level)
