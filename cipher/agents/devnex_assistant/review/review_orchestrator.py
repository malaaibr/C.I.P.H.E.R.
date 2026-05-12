"""TechReviewOrchestrator — drives the 9-node SWC Technical Review pipeline.

Node execution order
--------------------
  R1N1  Artifact Completeness Check      (gate — FAIL blocks R2–R9 if critical)
  R2N1  HLD Requirement Quality Review
  R3N1  LLD Design Review
  R4N1  HLD → LLD Traceability Review
  R5N1  LLD → Code Traceability Review
  R6N1  Klocwork Static Analysis Gate    (hard gate — 0 errors required)
  R7N1  UT Document Review
  R8N1  UT Environment & Report Review   (soft gate — 100% pass + coverage)
  R9N1  Review Consolidation & Verdict   (always runs; derives final verdict)
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from core.console_logging import format_console_log, utc_timestamp
from gca.vscode_invoker import DevNexGCAInvoker
from review.artifact_loader import (
    ReviewArtifacts,
    ArtifactValidationIssue,
    ARTIFACT_SLOTS,
    load_artifacts,
)
from review.review_models import (
    FindingSeverity,
    ReviewFinding,
    ReviewNodeStatus,
    ReviewReport,
    ReviewVerdict,
    StageResult,
)

MODULE_NAME = "TechReviewOrchestrator"

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_NODE_LABELS: dict[str, str] = {
    "R1N1": "Artifact Completeness Check",
    "R2N1": "HLD Requirement Review",
    "R3N1": "LLD Design Review",
    "R4N1": "HLD → LLD Traceability",
    "R5N1": "LLD → Code Traceability",
    "R6N1": "KW Static Analysis Gate",
    "R7N1": "UT Document Review",
    "R8N1": "UT Environment & Report",
    "R9N1": "Review Consolidation & Verdict",
}

_NODE_SEQUENCE = list(_NODE_LABELS.keys())


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class ReviewConfig:
    """Inputs required to start a review session."""
    swc_name:      str
    reviewer:      str
    artifact_paths: dict[str, str]   # slot → absolute file path (may be partial)
    artifacts_dir:  str = ""         # optional: auto-discover from directory

    def to_artifact_paths_dict(self) -> dict[str, str]:
        d = dict(self.artifact_paths)
        if self.artifacts_dir:
            d["artifacts_dir"] = self.artifacts_dir
        return d


# ── Orchestrator ──────────────────────────────────────────────────────────────

class TechReviewOrchestrator:
    """
    @brief Coordinates the SWC Technical Review pipeline (R1N1–R9N1).

    @details
    Mirrors DevNexOrchestrator patterns:
    - progress_callback(pct, node_id, label) for GUI updates
    - on_node_started(node_id) / on_node_complete(StageResult) callbacks
    - on_log(message, level) for structured console output
    - Single shared GCA invoker across all 9 nodes
    """

    def __init__(
        self,
        config:             ReviewConfig,
        gca_invoker:        DevNexGCAInvoker,
        on_log:             Callable[[str, str], None] | None = None,
        on_node_started:    Callable[[str], None] | None = None,
        on_node_complete:   Callable[[StageResult], None] | None = None,
        progress_callback:  Callable[[int, str, str], None] | None = None,
    ) -> None:
        self._config          = config
        self._gca             = gca_invoker
        self._on_log          = on_log or (lambda m, l: None)
        self._on_node_started = on_node_started or (lambda n: None)
        self._on_node_complete= on_node_complete or (lambda r: None)
        self._progress        = progress_callback or (lambda p, n, l: None)

        # Loaded once at run start
        self._artifacts: ReviewArtifacts | None = None
        self._artifact_issues: list[ArtifactValidationIssue] = []
        self._stage_results: list[StageResult] = []

        # Report built incrementally
        self._report = ReviewReport(
            swc_name=config.swc_name,
            reviewer=config.reviewer,
        )

    # ── Logging ───────────────────────────────────────────────────────────────

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame  = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        log_line = format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller)
        print(log_line)
        self._on_log(message, level)

    # ── Public API ────────────────────────────────────────────────────────────

    def run_node(self, node_id: str) -> StageResult:
        """Execute a single review node by ID. Thread-safe (no shared mutation)."""
        if node_id not in _NODE_LABELS:
            return StageResult(
                node_id=node_id,
                label="Unknown",
                status=ReviewNodeStatus.FAILED,
                errors=[f"Unknown review node: {node_id}"],
            )
        self._ensure_artifacts_loaded()
        handler = getattr(self, f"_run_{node_id.lower()}", None)
        if handler is None:
            return StageResult(
                node_id=node_id,
                label=_NODE_LABELS[node_id],
                status=ReviewNodeStatus.FAILED,
                errors=[f"No handler for {node_id}."],
            )
        self._trace(f"Starting {node_id}: {_NODE_LABELS[node_id]}")
        self._on_node_started(node_id)
        result: StageResult = handler()
        self._on_node_complete(result)
        return result

    def run_all(self) -> ReviewReport:
        """
        Execute R1N1 → R9N1 sequentially.
        If R1N1 gate fails (missing critical artifacts) remaining nodes are skipped.
        R9N1 always runs for consolidation.
        """
        self._stage_results.clear()
        self._report.stage_results.clear()
        total = len(_NODE_SEQUENCE)

        r1_failed = False
        for idx, node_id in enumerate(_NODE_SEQUENCE):
            pct = int((idx / total) * 100)
            self._progress(pct, node_id, _NODE_LABELS[node_id])

            # Skip R2–R8 if R1N1 hard failed (no point reviewing missing artifacts)
            if r1_failed and node_id not in ("R9N1",):
                result = StageResult(
                    node_id=node_id,
                    label=_NODE_LABELS[node_id],
                    status=ReviewNodeStatus.SKIPPED,
                    errors=["Skipped: R1N1 completeness gate failed."],
                )
            else:
                result = self.run_node(node_id)

            self._stage_results.append(result)
            self._report.stage_results.append(result)

            if node_id == "R1N1" and result.critical_count > 0:
                r1_failed = True
                self._trace(
                    "R1N1 gate FAILED — critical artifacts missing. Skipping R2–R8.",
                    level="WARN",
                )

        self._report.verdict = self._report.compute_verdict()
        self._progress(100, "R9N1", "Review Complete")
        self._trace(
            f"Review complete — verdict: {self._report.verdict.value}",
            level="SUCCESS",
        )
        return self._report

    # ── Artifact management ───────────────────────────────────────────────────

    def _ensure_artifacts_loaded(self) -> None:
        if self._artifacts is not None:
            return
        self._artifacts, self._artifact_issues = load_artifacts(
            self._config.to_artifact_paths_dict()
        )
        self._trace(
            f"Artifacts loaded: "
            f"{sum(1 for s in ARTIFACT_SLOTS if self._artifacts.get(s))} / {len(ARTIFACT_SLOTS)} present, "
            f"{len(self._artifact_issues)} issue(s)."
        )

    def _art(self) -> ReviewArtifacts:
        self._ensure_artifacts_loaded()
        return self._artifacts  # type: ignore[return-value]

    # ── Prompt helpers ────────────────────────────────────────────────────────

    def _load_prompt(self, filename: str) -> str:
        path = _PROMPTS_DIR / filename
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"# Review prompt not found: {filename}"

    def _render(self, template: str, **kwargs: str) -> str:
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", value)
        return template

    def _invoke(self, prompt: str, node_id: str, attached_files: list[str] | None = None) -> str:
        """Send prompt to GCA and return raw response text."""
        self._trace(f"Sending prompt to GCA for {node_id} ({len(prompt)} chars).")
        result = self._gca.invoke_prompt(prompt, attached_files or [])
        if not result.is_response_valid:
            raise RuntimeError(f"GCA returned empty response for {node_id}.")
        self._trace(
            f"GCA response received for {node_id} ({len(result.raw_response)} chars).",
            level="SUCCESS",
        )
        return result.raw_response

    def _parse_json_response(self, raw: str, node_id: str) -> dict[str, Any]:
        """Extract JSON object from GCA response (strips markdown fences if present)."""
        # Strip ```json ... ``` or ``` ... ```
        stripped = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        stripped = re.sub(r"\n?```$", "", stripped.strip(), flags=re.MULTILINE)
        stripped = stripped.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            # Try to extract first {...} block
            match = re.search(r"\{[\s\S]+\}", stripped)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        self._trace(f"Failed to parse JSON response for {node_id}.", level="WARN")
        return {}

    def _findings_from_list(
        self, items: list[dict], node_id: str
    ) -> list[ReviewFinding]:
        out: list[ReviewFinding] = []
        for item in items:
            try:
                sev_raw = str(item.get("severity", "INFO")).upper()
                sev = FindingSeverity(sev_raw) if sev_raw in FindingSeverity._value2member_map_ else FindingSeverity.INFO
                out.append(ReviewFinding(
                    stage_id     = node_id,
                    severity     = sev,
                    category     = item.get("category", ""),
                    description  = item.get("description", ""),
                    artifact_ref = item.get("artifact_ref", ""),
                    item_ref     = item.get("item_ref", ""),
                    line_ref     = int(item.get("line_ref", 0)),
                    standard_ref = item.get("standard_ref", ""),
                ))
            except Exception:
                continue
        return out

    # ── Node handlers ─────────────────────────────────────────────────────────

    def _run_r1n1(self) -> StageResult:
        """Artifact Completeness Check."""
        art = self._art()

        # Build manifest text
        manifest_lines = []
        for slot, label in ARTIFACT_SLOTS.items():
            p = art.get(slot)
            status_str = f"PRESENT ({p.name})" if p else "MISSING"
            manifest_lines.append(f"- {label}: {status_str}")
        manifest = "\n".join(manifest_lines)

        issues_text = "\n".join(
            f"- [{i.severity}] {ARTIFACT_SLOTS.get(i.slot, i.slot)}: {i.message}"
            for i in self._artifact_issues
        ) or "None detected by pre-check."

        template = self._load_prompt("r1_artifact_check.md")
        prompt   = self._render(
            template,
            SWC_NAME          = self._config.swc_name,
            REVIEWER          = self._config.reviewer,
            TIMESTAMP         = utc_timestamp(),
            ARTIFACT_MANIFEST = manifest,
            VALIDATION_ISSUES = issues_text,
        )

        try:
            raw = self._invoke(prompt, "R1N1")
            data = self._parse_json_response(raw, "R1N1")
        except Exception as exc:
            return self._error_stage("R1N1", str(exc))

        # Augment findings with pre-detected validation issues
        findings = self._findings_from_list(data.get("findings", []), "R1N1")
        for issue in self._artifact_issues:
            findings.append(ReviewFinding(
                stage_id     = "R1N1",
                severity     = FindingSeverity(issue.severity),
                category     = "COMPLETENESS",
                description  = issue.message,
                artifact_ref = ARTIFACT_SLOTS.get(issue.slot, issue.slot),
            ))

        gate_pass = data.get("gate_decision", "").upper() == "PASS" and not art.missing_critical()
        status = ReviewNodeStatus.PASSED if gate_pass else ReviewNodeStatus.FAILED

        return StageResult(
            node_id      = "R1N1",
            label        = _NODE_LABELS["R1N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "present": len(data.get("present_artifacts", [])),
                "missing_critical": len(art.missing_critical()),
                "missing_major":    len(art.missing_major()),
                "gate":             data.get("gate_decision", "FAIL"),
            },
        )

    def _run_r2n1(self) -> StageResult:
        """HLD Requirement Quality Review."""
        art = self._art()
        template = self._load_prompt("r2_hld_review.md")
        prompt   = self._render(
            template,
            SWC_NAME         = self._config.swc_name,
            HLD_REQS_CONTENT = art.read_text("hld_reqs") or "(HLD requirements not provided)",
        )
        files = [str(art.hld_reqs)] if art.hld_reqs else []
        try:
            raw  = self._invoke(prompt, "R2N1", files)
            data = self._parse_json_response(raw, "R2N1")
        except Exception as exc:
            return self._error_stage("R2N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R2N1")
        status   = ReviewNodeStatus.FAILED if any(
            f.severity == FindingSeverity.CRITICAL for f in findings
        ) else ReviewNodeStatus.PASSED

        return StageResult(
            node_id      = "R2N1",
            label        = _NODE_LABELS["R2N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "req_count":        data.get("req_count", 0),
                "asil_distribution":data.get("asil_distribution", {}),
                "quality_metrics":  data.get("quality_metrics", {}),
            },
        )

    def _run_r3n1(self) -> StageResult:
        """LLD Design Review."""
        art = self._art()
        template = self._load_prompt("r3_lld_review.md")
        prompt   = self._render(
            template,
            SWC_NAME         = self._config.swc_name,
            LLD_DOC_CONTENT  = art.read_text("lld_doc")  or "(LLD not provided)",
            HLD_REQS_CONTENT = art.read_text("hld_reqs") or "(HLD not provided)",
        )
        files = [p for p in [art.lld_doc, art.hld_reqs] if p]
        try:
            raw  = self._invoke(prompt, "R3N1", [str(f) for f in files])
            data = self._parse_json_response(raw, "R3N1")
        except Exception as exc:
            return self._error_stage("R3N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R3N1")
        status   = ReviewNodeStatus.FAILED if any(
            f.severity == FindingSeverity.CRITICAL for f in findings
        ) else ReviewNodeStatus.PASSED

        return StageResult(
            node_id      = "R3N1",
            label        = _NODE_LABELS["R3N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "design_element_count": data.get("design_element_count", 0),
                "interface_count":      data.get("interface_count", 0),
                "state_machine_count":  data.get("state_machine_count", 0),
            },
        )

    def _run_r4n1(self) -> StageResult:
        """HLD → LLD Traceability Review."""
        art = self._art()
        template = self._load_prompt("r4_hld_lld_trace.md")
        prompt   = self._render(
            template,
            SWC_NAME              = self._config.swc_name,
            TRACE_HLD_LLD_CONTENT = art.read_text("trace_hld_lld") or "(matrix not provided)",
            HLD_REQS_CONTENT      = art.read_text("hld_reqs")      or "(HLD not provided)",
            LLD_DOC_CONTENT       = art.read_text("lld_doc")        or "(LLD not provided)",
        )
        files = [p for p in [art.trace_hld_lld, art.hld_reqs, art.lld_doc] if p]
        try:
            raw  = self._invoke(prompt, "R4N1", [str(f) for f in files])
            data = self._parse_json_response(raw, "R4N1")
        except Exception as exc:
            return self._error_stage("R4N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R4N1")
        status   = ReviewNodeStatus.FAILED if any(
            f.severity == FindingSeverity.CRITICAL for f in findings
        ) else ReviewNodeStatus.PASSED

        return StageResult(
            node_id      = "R4N1",
            label        = _NODE_LABELS["R4N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "hld_coverage_pct": data.get("hld_coverage_pct", 0),
                "lld_orphan_pct":   data.get("lld_orphan_pct", 0),
                "trace_links":      data.get("trace_link_count", 0),
            },
        )

    def _run_r5n1(self) -> StageResult:
        """LLD → Code Traceability Review."""
        art = self._art()
        template = self._load_prompt("r5_lld_code_trace.md")
        prompt   = self._render(
            template,
            SWC_NAME               = self._config.swc_name,
            TRACE_LLD_CODE_CONTENT = art.read_text("trace_lld_code") or "(matrix not provided)",
            LLD_DOC_CONTENT        = art.read_text("lld_doc")         or "(LLD not provided)",
        )
        files = [p for p in [art.trace_lld_code, art.lld_doc] if p]
        try:
            raw  = self._invoke(prompt, "R5N1", [str(f) for f in files])
            data = self._parse_json_response(raw, "R5N1")
        except Exception as exc:
            return self._error_stage("R5N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R5N1")
        status   = ReviewNodeStatus.FAILED if any(
            f.severity == FindingSeverity.CRITICAL for f in findings
        ) else ReviewNodeStatus.PASSED

        return StageResult(
            node_id      = "R5N1",
            label        = _NODE_LABELS["R5N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "lld_coverage_pct":   data.get("lld_coverage_pct", 0),
                "code_annotation_pct":data.get("code_annotation_pct", 0),
            },
        )

    def _run_r6n1(self) -> StageResult:
        """Klocwork Static Analysis Gate (hard gate — 0 errors required)."""
        art = self._art()
        template = self._load_prompt("r6_kw_analysis.md")
        prompt   = self._render(
            template,
            SWC_NAME         = self._config.swc_name,
            KW_REPORT_CONTENT= art.read_text("kw_report") or "(KW report not provided)",
        )
        files = [str(art.kw_report)] if art.kw_report else []
        try:
            raw  = self._invoke(prompt, "R6N1", files)
            data = self._parse_json_response(raw, "R6N1")
        except Exception as exc:
            return self._error_stage("R6N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R6N1")
        errors   = int(data.get("errors", 0))

        # Hard gate: any KW error → CRITICAL finding guaranteed
        if errors > 0 and not any(f.severity == FindingSeverity.CRITICAL for f in findings):
            findings.append(ReviewFinding(
                stage_id     = "R6N1",
                severity     = FindingSeverity.CRITICAL,
                category     = "KW_ERROR",
                description  = f"Klocwork reports {errors} error(s). Gate: FAIL.",
                artifact_ref = "KW Analysis Report",
                standard_ref = "ISO 26262-6 §9",
            ))

        gate_pass = data.get("gate_result", "FAIL").upper() == "PASS" and errors == 0
        status = ReviewNodeStatus.PASSED if gate_pass else ReviewNodeStatus.FAILED

        return StageResult(
            node_id      = "R6N1",
            label        = _NODE_LABELS["R6N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "kw_errors":      errors,
                "kw_warnings":    data.get("warnings", 0),
                "suppressions":   data.get("suppressions", 0),
                "gate":           data.get("gate_result", "FAIL"),
            },
        )

    def _run_r7n1(self) -> StageResult:
        """UT Document Review."""
        art = self._art()
        template = self._load_prompt("r7_ut_doc_review.md")
        prompt   = self._render(
            template,
            SWC_NAME           = self._config.swc_name,
            UT_DOC_CONTENT     = art.read_text("ut_doc")       or "(UT document not provided)",
            LLD_DOC_CONTENT    = art.read_text("lld_doc")      or "(LLD not provided)",
            TRACE_LLD_UT_CONTENT = art.read_text("trace_lld_ut") or "(trace matrix not provided)",
        )
        files = [p for p in [art.ut_doc, art.lld_doc, art.trace_lld_ut] if p]
        try:
            raw  = self._invoke(prompt, "R7N1", [str(f) for f in files])
            data = self._parse_json_response(raw, "R7N1")
        except Exception as exc:
            return self._error_stage("R7N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R7N1")
        status   = ReviewNodeStatus.FAILED if any(
            f.severity == FindingSeverity.CRITICAL for f in findings
        ) else ReviewNodeStatus.PASSED

        return StageResult(
            node_id      = "R7N1",
            label        = _NODE_LABELS["R7N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "test_case_count":      data.get("test_case_count", 0),
                "lld_test_coverage_pct":data.get("lld_test_coverage_pct", 0),
                "mc_dc_designed":       data.get("mc_dc_designed", False),
            },
        )

    def _run_r8n1(self) -> StageResult:
        """UT Environment & Execution Report Review."""
        art = self._art()
        template = self._load_prompt("r8_ut_report_review.md")
        prompt   = self._render(
            template,
            SWC_NAME         = self._config.swc_name,
            UT_ENV_CONTENT   = art.read_text("ut_env")    or "(UT environment not provided)",
            UT_REPORT_CONTENT= art.read_text("ut_report") or "(UT report not provided)",
        )
        files = [p for p in [art.ut_env, art.ut_report] if p]
        try:
            raw  = self._invoke(prompt, "R8N1", [str(f) for f in files])
            data = self._parse_json_response(raw, "R8N1")
        except Exception as exc:
            return self._error_stage("R8N1", str(exc))

        findings = self._findings_from_list(data.get("findings", []), "R8N1")
        failed   = int(data.get("failed_tests", 0))
        open_def = int(data.get("open_defects", 0))

        # Hard gate: failing tests or open defects → CRITICAL
        if (failed > 0 or open_def > 0) and not any(
            f.severity == FindingSeverity.CRITICAL for f in findings
        ):
            msg = []
            if failed:
                msg.append(f"{failed} failing test(s)")
            if open_def:
                msg.append(f"{open_def} open defect(s)")
            findings.append(ReviewFinding(
                stage_id     = "R8N1",
                severity     = FindingSeverity.CRITICAL,
                category     = "PASS_RATE",
                description  = f"UT gate FAIL: {', '.join(msg)}.",
                artifact_ref = "UT Report",
                standard_ref = "ASPICE SWE.5 BP3 / ISO 26262-6 §9",
            ))

        gate_pass = data.get("gate_result", "FAIL").upper() == "PASS"
        status = ReviewNodeStatus.PASSED if gate_pass else ReviewNodeStatus.FAILED

        return StageResult(
            node_id      = "R8N1",
            label        = _NODE_LABELS["R8N1"],
            status       = status,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "pass_rate_pct":        data.get("pass_rate_pct", 0),
                "statement_coverage_pct":data.get("statement_coverage_pct", 0),
                "branch_coverage_pct":  data.get("branch_coverage_pct", 0),
                "mc_dc_coverage_pct":   data.get("mc_dc_coverage_pct", 0),
                "failed_tests":         failed,
                "open_defects":         open_def,
                "gate":                 data.get("gate_result", "FAIL"),
            },
        )

    def _run_r9n1(self) -> StageResult:
        """Review Consolidation & Verdict — always runs last."""
        stages_json = json.dumps(
            [s.to_dict() for s in self._stage_results], indent=2
        )
        template = self._load_prompt("r9_consolidation.md")
        prompt   = self._render(
            template,
            SWC_NAME           = self._config.swc_name,
            REVIEWER           = self._config.reviewer,
            TIMESTAMP          = utc_timestamp(),
            STAGE_RESULTS_JSON = stages_json,
        )
        try:
            raw  = self._invoke(prompt, "R9N1")
            data = self._parse_json_response(raw, "R9N1")
        except Exception as exc:
            return self._error_stage("R9N1", str(exc))

        # Build consolidation findings from critical/major lists in response
        findings: list[ReviewFinding] = []
        for item in data.get("critical_findings", []):
            findings.append(ReviewFinding(
                stage_id    = item.get("stage_id", "R9N1"),
                severity    = FindingSeverity.CRITICAL,
                category    = item.get("category", "CONSOLIDATED"),
                description = item.get("description", "") + " | Action: " + item.get("action", ""),
                item_ref    = item.get("item_ref", ""),
            ))
        for item in data.get("major_findings", []):
            findings.append(ReviewFinding(
                stage_id    = item.get("stage_id", "R9N1"),
                severity    = FindingSeverity.MAJOR,
                category    = item.get("category", "CONSOLIDATED"),
                description = item.get("description", "") + " | Action: " + item.get("action", ""),
                item_ref    = item.get("item_ref", ""),
            ))

        # Update report verdict from R9N1 response (authoritative)
        verdict_str = data.get("verdict", self._report.compute_verdict().value).upper()
        try:
            self._report.verdict = ReviewVerdict(verdict_str)
        except ValueError:
            self._report.verdict = self._report.compute_verdict()

        self._report.summary = data.get("executive_summary", "")

        return StageResult(
            node_id      = "R9N1",
            label        = _NODE_LABELS["R9N1"],
            status       = ReviewNodeStatus.PASSED,
            findings     = findings,
            raw_response = raw,
            metrics      = {
                "verdict":          self._report.verdict.value,
                "coverage_table":   data.get("coverage_table", {}),
                "gate_summary":     data.get("gate_summary", {}),
                "recommendation":   data.get("recommendation", ""),
            },
        )

    # ── Error helper ──────────────────────────────────────────────────────────

    def _error_stage(self, node_id: str, error: str) -> StageResult:
        self._trace(f"{node_id} error: {error}", level="ERROR")
        return StageResult(
            node_id  = node_id,
            label    = _NODE_LABELS.get(node_id, node_id),
            status   = ReviewNodeStatus.FAILED,
            errors   = [error],
            findings = [
                ReviewFinding(
                    stage_id    = node_id,
                    severity    = FindingSeverity.CRITICAL,
                    category    = "EXECUTION_ERROR",
                    description = f"Review node execution failed: {error}",
                )
            ],
        )
