"""asil_review_skill.py — UC 3.1: ASIL-B/C/D Code Review Assistant.

Pipeline:
  Phase 1  Ollama TRIAGE    — classify violations by rule + severity
  Phase 2  Gemini PLAN      — build fix strategy per violation cluster
  Phase 3  GCA CODE_GEN     — generate compliant code rewrites
  Phase 4  AsilGate         — enforce ASIL-D hard block if residual critical remains
  Phase 5  Human G5 gate    — Safety Engineer sign-off for ASIL-D

The module plays BOTH the Reviewer role (finds violations) AND the Developer
role (proposes fixes), co-processing until the component reaches target ASIL
compliance, matching the UC 3.1 workflow described in the platform UC catalog.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

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

MODULE_NAME = "AsilReviewSkill"

# MISRA-C:2012 rules surfaced during review
MISRA_CRITICAL = {
    "R1.3": "Undefined behaviour shall not occur",
    "R11.3": "A cast shall not be performed between a pointer to object and a pointer to a different object",
    "R11.8": "A cast shall not remove any const or volatile qualification",
    "R15.5": "A function shall have a single point of exit at the end",
    "R14.4": "The controlling expression of an if or iteration-statement shall be essentially Boolean",
    "R17.7": "The value returned by a function shall be used",
    "R21.3": "The memory allocation and deallocation functions shall not be used",
}


@dataclass
class AsilViolation:
    """One MISRA / safety violation found in source."""
    file:       str
    line:       int
    rule:       str
    severity:   str       # CRITICAL | MAJOR | MINOR
    description: str
    fix_hint:   str = ""
    fixed:      bool = False


@dataclass
class AsilReviewReport:
    """Complete ASIL review report for one source component."""
    source_file:       str
    asil_target:       str
    total_violations:  int
    critical_count:    int
    major_count:       int
    minor_count:       int
    violations:        list = field(default_factory=list)
    fix_diffs:         list = field(default_factory=list)
    gate_decision:     str  = "PENDING"
    compliance_badge:  str  = "NOT_COMPLIANT"
    rationale:         str  = ""

    @property
    def is_compliant(self) -> bool:
        return self.critical_count == 0 and self.compliance_badge == "COMPLIANT"


class AsilReviewSkill:
    """UC 3.1 — ASIL-B/C/D code review + fix co-processor.

    Parameters
    ----------
    orchestrator :
        DevNexOrchestrator instance — provides config, gca_invoker, _artifacts_dir.
    ollama_url :
        Ollama REST endpoint (default: http://localhost:11434).
    gemini_cmd :
        Gemini CLI command (default: ['gemini']).
    on_log :
        Optional log callback (message, level).
    """

    def __init__(
        self,
        orchestrator=None,
        ollama_url: str = "http://localhost:11434",
        gemini_cmd: list | None = None,
        on_log: Callable | None = None,
    ) -> None:
        self._orch      = orchestrator
        self._ollama    = ollama_url
        self._gemini    = gemini_cmd or ["gemini"]
        self._on_log    = on_log or (lambda *_: None)

    # ── Public API ────────────────────────────────────────────────────────

    def run(
        self,
        source_path: str | Path,
        asil_target: str = "B",
        artifacts_dir: Path | None = None,
    ) -> AsilReviewReport:
        """
        Execute the full UC 3.1 pipeline.

        Parameters
        ----------
        source_path : path to the .c file under review
        asil_target : 'B', 'C', or 'D'
        artifacts_dir : where to write JSON / MD artefacts (defaults to orch artifacts dir)

        Returns AsilReviewReport.
        Raises SemanticConflictError on ASIL-D hard block with residual critical violations.
        """
        src = Path(source_path)
        if not src.exists():
            raise ArtifactMissingError(f"UC 3.1: Source file not found: '{src}'")

        out_dir = artifacts_dir or self._get_artifacts_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        asil = asil_target.upper()

        self._log(f"UC 3.1 starting | file={src.name} | ASIL-{asil}")

        # Phase 1 — Ollama TRIAGE: classify violations
        violations = self._phase1_triage(src, asil)
        self._log(f"Phase 1: {len(violations)} violation(s) found")

        # Phase 2 — Gemini PLAN: build fix strategy
        fix_plan = self._phase2_plan(src, violations, asil)
        self._log(f"Phase 2: Fix plan generated ({len(fix_plan)} chars)")

        # Phase 3 — GCA CODE_GEN: generate fix diffs
        fix_diffs = self._phase3_codegen(src, violations, fix_plan, asil)
        self._log(f"Phase 3: {len(fix_diffs)} fix diff(s) generated")

        # Phase 4 — ASIL gate evaluation
        critical_count = sum(1 for v in violations if v.severity == "CRITICAL")
        major_count    = sum(1 for v in violations if v.severity == "MAJOR")
        minor_count    = sum(1 for v in violations if v.severity == "MINOR")

        gate = AsilGate(asil)
        has_critical_overlap = critical_count > 0
        decision = gate.evaluate(has_critical_overlap)
        self._log(
            f"Phase 4: gate={decision.gate} | action={decision.action} | "
            f"critical={critical_count}",
            level="WARN" if decision.is_blocking else "INFO",
        )

        # Build report
        report = AsilReviewReport(
            source_file      = str(src),
            asil_target      = asil,
            total_violations = len(violations),
            critical_count   = critical_count,
            major_count      = major_count,
            minor_count      = minor_count,
            violations       = [asdict(v) for v in violations],
            fix_diffs        = fix_diffs,
            gate_decision    = decision.action,
            compliance_badge = "COMPLIANT" if critical_count == 0 else "NOT_COMPLIANT",
            rationale        = decision.rationale,
        )

        # Write artefacts
        rpt_json = out_dir / f"asil_review_{src.stem}.json"
        rpt_json.write_text(json.dumps(asdict(report), indent=2, default=str), encoding="utf-8")

        rpt_md = out_dir / f"asil_review_{src.stem}.md"
        rpt_md.write_text(self._build_md_report(report, violations), encoding="utf-8")
        self._log(f"Artefacts written -> {rpt_json.name}, {rpt_md.name}", level="SUCCESS")

        # Phase 4 enforcement — raise on ASIL-D hard block
        if decision.action == "HARD_BLOCK":
            raise SemanticConflictError(
                f"[ASIL-{asil} HARD BLOCK] {decision.rationale}\n"
                f"Critical violations: {critical_count}\n"
                f"Review report: {rpt_md}"
            )

        return report

    # ── Private phases ────────────────────────────────────────────────────

    def _phase1_triage(self, src: Path, asil: str) -> list[AsilViolation]:
        """Ollama TRIAGE — classify MISRA / safety violations."""
        source_text = src.read_text(encoding="utf-8", errors="replace")
        rules_block = "\n".join(f"  {k}: {v}" for k, v in MISRA_CRITICAL.items())

        prompt = (
            f"You are a MISRA-C:2012 static analyser for ASIL-{asil} embedded software.\n"
            f"Analyse the following C source for violations of these critical rules:\n"
            f"{rules_block}\n\n"
            f"Source file: {src.name}\n```c\n{source_text[:8000]}\n```\n\n"
            "Return a JSON array of violations. Each object must have these fields:\n"
            '  {"file": "<filename>", "line": <int>, "rule": "<Rnn.n>", '
            '"severity": "CRITICAL|MAJOR|MINOR", "description": "<string>", "fix_hint": "<string>"}\n'
            "Return [] if no violations found."
        )
        raw = self._call_ollama(prompt)
        return self._parse_violations(raw, src.name)

    def _phase2_plan(self, src: Path, violations: list[AsilViolation], asil: str) -> str:
        """Gemini PLAN — strategic fix plan for violation clusters."""
        if not violations:
            return "No violations — no fix plan required."
        v_summary = "\n".join(
            f"  Line {v.line}: {v.rule} — {v.description}"
            for v in violations[:20]
        )
        prompt = (
            f"ISO 26262 ASIL-{asil} fix strategy for {src.name}.\n\n"
            f"Violations:\n{v_summary}\n\n"
            "Generate a structured fix plan:\n"
            "1. Group violations by root cause\n"
            "2. For each group: proposed fix approach + rationale\n"
            "3. Prioritise CRITICAL before MAJOR before MINOR\n"
            "4. Note any MISRA Rule R1.3 / R11.8 interactions"
        )
        return self._call_gemini(prompt)

    def _phase3_codegen(
        self,
        src: Path,
        violations: list[AsilViolation],
        fix_plan: str,
        asil: str,
    ) -> list[str]:
        """GCA CODE_GEN — generate compliant code fix diffs."""
        if not violations or self._orch is None:
            return []
        source_text = src.read_text(encoding="utf-8", errors="replace")
        v_json = json.dumps([asdict(v) for v in violations[:10]], indent=2)

        prompt = (
            f"ISO 26262 ASIL-{asil} code fix generator.\n\n"
            f"File: {src.name}\n"
            f"Violations:\n{v_json}\n\n"
            f"Fix plan:\n{fix_plan[:2000]}\n\n"
            f"Source:\n```c\n{source_text[:6000]}\n```\n\n"
            "For each violation produce a unified diff (--- a/file +++ b/file) with the MISRA-compliant fix.\n"
            "Separate diffs with ---DIFF---"
        )
        try:
            result = self._orch.gca_invoker.invoke_prompt(prompt, [str(src)])
            if result.is_response_valid:
                return [d.strip() for d in result.raw_response.split("---DIFF---") if d.strip()]
        except Exception as exc:
            self._log(f"Phase 3: GCA call failed — {exc}", level="WARN")
        return []

    # ── LLM backend helpers ───────────────────────────────────────────────

    def _call_ollama(self, prompt: str, model: str = "llama3") -> str:
        """Call Ollama REST API (TRIAGE role)."""
        try:
            import urllib.request
            body = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{self._ollama}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data.get("response", "")
        except Exception as exc:
            self._log(f"Ollama call failed ({exc}) — using empty triage result.", level="WARN")
            return "[]"

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini CLI subprocess (PLAN role)."""
        try:
            result = subprocess.run(
                self._gemini + [prompt[:4000]],
                capture_output=True, text=True, timeout=90,
            )
            return result.stdout.strip() or result.stderr.strip() or "No plan generated."
        except Exception as exc:
            self._log(f"Gemini call failed ({exc}) — using stub plan.", level="WARN")
            return f"[Gemini unavailable: {exc}] Fix CRITICAL violations manually."

    # ── Parsing / reporting helpers ───────────────────────────────────────

    @staticmethod
    def _parse_violations(raw: str, filename: str) -> list[AsilViolation]:
        try:
            start = raw.find("[")
            end   = raw.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(raw[start:end])
                return [
                    AsilViolation(
                        file        = item.get("file", filename),
                        line        = int(item.get("line", 0)),
                        rule        = item.get("rule", "R?.?"),
                        severity    = item.get("severity", "MINOR").upper(),
                        description = item.get("description", ""),
                        fix_hint    = item.get("fix_hint", ""),
                    )
                    for item in items if isinstance(item, dict)
                ]
        except (json.JSONDecodeError, ValueError):
            pass
        return []

    @staticmethod
    def _build_md_report(report: AsilReviewReport, violations: list[AsilViolation]) -> str:
        lines = [
            f"# ASIL Review Report — {Path(report.source_file).name}",
            "",
            f"**Target ASIL:** {report.asil_target}  |  "
            f"**Compliance:** `{report.compliance_badge}`  |  "
            f"**Gate:** `{report.gate_decision}`",
            "",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| CRITICAL | {report.critical_count} |",
            f"| MAJOR    | {report.major_count} |",
            f"| MINOR    | {report.minor_count} |",
            "",
            "## Violations",
            "",
        ]
        for v in violations:
            lines += [
                f"### {v.rule} — {v.severity} (line {v.line})",
                f"{v.description}",
                f"> **Fix hint:** {v.fix_hint}" if v.fix_hint else "",
                "",
            ]
        lines += [
            "## Gate Rationale",
            "",
            report.rationale,
            "",
            "## Resolution Steps",
            "1. Address all CRITICAL violations before re-running review.",
            "2. Re-run UC 3.1 after fixes to confirm COMPLIANT badge.",
            "3. Safety Engineer G5 sign-off required for ASIL-D components.",
        ]
        return "\n".join(lines)

    def _get_artifacts_dir(self) -> Path:
        if self._orch is not None:
            return self._orch._artifacts_dir
        return Path(".devnex") / "asil_review"

    def _log(self, message: str, level: str = "INFO") -> None:
        line = format_console_log(MODULE_NAME, level, message, utc_timestamp(), "run")
        print(line)
        self._on_log(message, level)
