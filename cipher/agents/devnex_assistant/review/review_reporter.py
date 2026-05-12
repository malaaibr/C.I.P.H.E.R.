"""ReviewReporter — serialise a ReviewReport to JSON and Markdown artifacts.

Outputs
-------
  <swc_name>_review_report.json   — machine-readable full report
  <swc_name>_review_report.md     — human-readable Markdown summary
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from review.review_models import (
    FindingSeverity,
    ReviewNodeStatus,
    ReviewReport,
    ReviewVerdict,
    StageResult,
)


# ── Verdict rendering ─────────────────────────────────────────────────────────

_VERDICT_BADGE = {
    ReviewVerdict.APPROVED:    "✅ APPROVED",
    ReviewVerdict.CONDITIONAL: "⚠️  CONDITIONAL",
    ReviewVerdict.REJECTED:    "❌ REJECTED",
    ReviewVerdict.INCOMPLETE:  "🔄 INCOMPLETE",
}

_SEV_ICON = {
    FindingSeverity.CRITICAL: "🔴",
    FindingSeverity.MAJOR:    "🟠",
    FindingSeverity.MINOR:    "🟡",
    FindingSeverity.INFO:     "🔵",
}

_NODE_STATUS_ICON = {
    ReviewNodeStatus.PASSED:  "✅",
    ReviewNodeStatus.FAILED:  "❌",
    ReviewNodeStatus.SKIPPED: "⏭️",
    ReviewNodeStatus.RUNNING: "🔄",
    ReviewNodeStatus.PENDING: "⏳",
}


# ── Reporter ──────────────────────────────────────────────────────────────────

class ReviewReporter:
    """Generates JSON and Markdown review report artifacts."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: ReviewReport) -> tuple[Path, Path]:
        """
        Write JSON + Markdown reports.
        Returns (json_path, md_path).
        Uses atomic write (tempfile + os.replace) to avoid partial reads.
        """
        safe_name = report.swc_name.replace(" ", "_").replace("/", "_")
        json_path = self._output_dir / f"{safe_name}_review_report.json"
        md_path   = self._output_dir / f"{safe_name}_review_report.md"

        self._atomic_write(json_path, report.to_json())
        self._atomic_write(md_path,   self._render_markdown(report))
        return json_path, md_path

    # ── Markdown renderer ─────────────────────────────────────────────────────

    def _render_markdown(self, report: ReviewReport) -> str:
        parts: list[str] = []

        # Header
        parts.append(f"# Technical Review Report — {report.swc_name}")
        parts.append("")
        parts.append(f"| Field | Value |")
        parts.append(f"|-------|-------|")
        parts.append(f"| Component | `{report.swc_name}` |")
        parts.append(f"| Reviewer  | {report.reviewer} |")
        parts.append(f"| Date/Time | {report.timestamp} |")
        parts.append(f"| Verdict   | **{_VERDICT_BADGE.get(report.verdict, report.verdict.value)}** |")
        parts.append(f"| Critical  | {report.critical_count} |")
        parts.append(f"| Major     | {report.major_count} |")
        parts.append(f"| Minor     | {report.minor_count} |")
        parts.append("")

        # Executive summary
        if report.summary:
            parts.append("## Executive Summary")
            parts.append("")
            parts.append(report.summary)
            parts.append("")

        # Coverage table (from R9N1 metrics if available)
        r9 = next((s for s in report.stage_results if s.node_id == "R9N1"), None)
        if r9 and r9.metrics.get("coverage_table"):
            parts.append("## Coverage Metrics")
            parts.append("")
            ct = r9.metrics["coverage_table"]
            parts.append("| Metric | Value |")
            parts.append("|--------|-------|")
            metric_labels = {
                "hld_req_quality_pct":   "HLD Req Quality",
                "hld_lld_coverage_pct":  "HLD→LLD Coverage",
                "lld_code_coverage_pct": "LLD→Code Coverage",
                "lld_ut_coverage_pct":   "LLD→UT Coverage",
                "ut_pass_rate_pct":      "UT Pass Rate",
                "statement_coverage_pct":"Statement Coverage",
                "branch_coverage_pct":   "Branch Coverage",
                "mc_dc_coverage_pct":    "MC/DC Coverage",
                "kw_errors":             "KW Errors",
            }
            for key, label in metric_labels.items():
                val = ct.get(key, "—")
                if isinstance(val, (int, float)) and "pct" in key:
                    cell = f"{val:.1f}%"
                else:
                    cell = str(val)
                parts.append(f"| {label} | {cell} |")
            parts.append("")

        # Gate summary
        if r9 and r9.metrics.get("gate_summary"):
            gs = r9.metrics["gate_summary"]
            parts.append("## Gate Summary")
            parts.append("")
            gate_labels = {
                "R1N1_completeness": "R1N1 — Artifact Completeness",
                "R6N1_kw_analysis":  "R6N1 — KW Static Analysis",
                "R8N1_ut_execution": "R8N1 — UT Execution",
            }
            for key, label in gate_labels.items():
                result = gs.get(key, "—")
                icon   = "✅" if result == "PASS" else "❌" if result == "FAIL" else "—"
                parts.append(f"- {icon} **{label}**: {result}")
            parts.append("")

        # Stage-by-stage results
        parts.append("## Stage Results")
        parts.append("")
        for stage in report.stage_results:
            icon = _NODE_STATUS_ICON.get(stage.status, "")
            parts.append(f"### {icon} {stage.node_id} — {stage.label}")
            parts.append("")
            parts.append(f"**Status:** {stage.status.value.upper()}")
            if stage.metrics:
                m_items = []
                for k, v in stage.metrics.items():
                    if isinstance(v, dict):
                        continue
                    if isinstance(v, float):
                        m_items.append(f"{k}={v:.1f}")
                    else:
                        m_items.append(f"{k}={v}")
                if m_items:
                    parts.append(f"**Metrics:** {' · '.join(m_items)}")
            parts.append("")

            if stage.findings:
                parts.append("| # | Sev | Category | Description | Ref |")
                parts.append("|---|-----|----------|-------------|-----|")
                for i, f in enumerate(stage.findings, 1):
                    icon_sev = _SEV_ICON.get(f.severity, "")
                    ref = f.item_ref or f.artifact_ref or ""
                    desc = f.description[:120] + ("…" if len(f.description) > 120 else "")
                    parts.append(
                        f"| {i} | {icon_sev} {f.severity.value} "
                        f"| {f.category} | {desc} | {ref} |"
                    )
                parts.append("")
            else:
                parts.append("_No findings._")
                parts.append("")

            if stage.errors:
                for err in stage.errors:
                    parts.append(f"> ⚠️ Error: {err}")
                parts.append("")

        # Recommendation
        if r9 and r9.metrics.get("recommendation"):
            parts.append("## Recommendation")
            parts.append("")
            parts.append(r9.metrics["recommendation"])
            parts.append("")

        # Footer
        parts.append("---")
        parts.append("*Generated by DevNex Technical Review Pipeline*")

        return "\n".join(parts)

    # ── Atomic write ──────────────────────────────────────────────────────────

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        fd, tmp = tempfile.mkstemp(
            dir=str(target.parent),
            prefix=f".{target.stem}_",
            suffix=target.suffix,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp, str(target))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
