"""
Apply DOC_VERSIONING.md frontmatter + Revision History footer to a curated
set of Markdown docs. Idempotent: re-running only adds the blocks to files
that don't already have them.

Run from repo root:  python scripts/version_docs.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

TODAY = "2026-05-18"
DEFAULT_OWNER = "CIPHER team"


@dataclass
class DocSpec:
    path: str
    version: str = "1.0.0"
    status: str = "current"
    supersedes: str | None = None
    superseded_by: str | None = None
    initial_change: str = "Versioning frontmatter added (see docs/DOC_VERSIONING.md)."


# Full-treatment docs (frontmatter + Revision History footer)
FULL_TREATMENT: list[DocSpec] = [
    # Root
    DocSpec("README.md"),
    DocSpec("CLAUDE.md", initial_change="Synced with Sprint 8 state."),
    # Top-level docs (already current)
    DocSpec("docs/SPRINT_PLAN.md", version="1.2.0",
            initial_change="Tracks Sprints 1–8 (VSIX + MVP wiring). Supersedes SESSION_HANDOFF §14."),
    DocSpec("docs/VSIX_DESIGN.md"),
    DocSpec("docs/BUILD.md", version="1.1.0",
            initial_change="GitHub Actions section removed — CI out of scope for this phase."),
    DocSpec("docs/USER_GUIDE.md", version="1.1.0",
            initial_change="Added DVF opt-in + voice install notes under 'What to try next'."),
    DocSpec("docs/USER_MANUAL.md"),
    DocSpec("docs/DVF_OPTIN_GUIDE.md"),
    DocSpec("docs/ASDLC.md"),
    DocSpec("docs/CODE_CHANGES_GUIDE.md"),
    DocSpec("docs/COURSE_PROMPT.md"),
    DocSpec("docs/DEMO_RUNBOOK_DIO.md"),
    # Superseded
    DocSpec("docs/SESSION_HANDOFF.md", status="superseded",
            superseded_by="docs/SPRINT_PLAN.md",
            initial_change="Marked superseded — see SPRINT_PLAN.md for current backlog."),
    DocSpec("docs/agents/devnex.md", status="superseded",
            superseded_by="docs/agents/devnex_assistant.md",
            initial_change="Marked superseded — merged into devnex_assistant agent."),
    # Deprecated legacy
    DocSpec("docs/car/CAR-001-maancipher-shell.md", status="deprecated",
            initial_change="Marked deprecated — predates CIPHER; kept for archeology."),
    DocSpec("docs/wbs/wrap-rewrite-001-maancipher-shell.md", status="deprecated",
            initial_change="Marked deprecated — predates CIPHER; kept for archeology."),
    # Authoritative references (frontmatter only — body left untouched, but a footer row noted)
    DocSpec("docs/CIPHER_archi.md", version="3.0.0",
            initial_change="Versioning frontmatter added; body unchanged."),
    DocSpec("docs/CIPHER_HLD.md", version="3.0.0",
            initial_change="Versioning frontmatter added; body unchanged."),
    DocSpec("docs/CIPHER_LLD.md", version="1.0.0",
            initial_change="Versioning frontmatter added; body unchanged."),
    # Per-agent docs
    DocSpec("docs/agents/devnex_assistant.md"),
    DocSpec("docs/agents/memory_agent.md"),
    DocSpec("docs/agents/asil_reviewer.md"),
    DocSpec("docs/agents/compliance.md"),
    DocSpec("docs/agents/planner.md"),
    DocSpec("docs/agents/research.md"),
    DocSpec("docs/agents/test_agent.md"),
    DocSpec("docs/agents/tool_agent.md"),
    DocSpec("docs/agents/traceability.md"),
    # Extension
    DocSpec("extension/README.md"),
]

# Frontmatter-only sweep (no footer)
FRONTMATTER_ONLY: list[DocSpec] = [
    # ADRs
    DocSpec("docs/adr/ADR-0001-llm-gateway.md"),
    DocSpec("docs/adr/ADR-0002-gca-websocket-bridge.md"),
    DocSpec("docs/adr/ADR-0003-poc-scope-lock.md"),
    DocSpec("docs/adr/ADR-0004-memory-agent-rag.md"),
    DocSpec("docs/adr/ADR-0005-shell-panel-docking.md"),
    # CAR
    DocSpec("docs/car/CAR-002-devnex-assistant.md"),
    DocSpec("docs/car/CAR-003-raglab-main.md"),
    DocSpec("docs/car/CAR-004-autosar-dio-sws.md"),
    DocSpec("docs/car/CAR-005-autosar-port-sws.md"),
    DocSpec("docs/car/CAR-006-autosar-det-sws.md"),
    DocSpec("docs/car/CAR-007-autosar-iohwab-reference.md"),
    DocSpec("docs/car/CAR-008-autosar-swc-template-reference.md"),
    # Layer HLDs/LLDs
    DocSpec("docs/layers/Core_HLD.md"),
    DocSpec("docs/layers/DRS_HLD.md"),
    DocSpec("docs/layers/GCL_HLD.md"),
    DocSpec("docs/layers/MKF_HLD.md"),
    DocSpec("docs/layers/PKL_HLD.md"),
    DocSpec("docs/layers/TRF_HLD.md"),
    DocSpec("docs/layers/AAL_HLD.md"),
    DocSpec("docs/layers/GUI_HLD.md"),
    DocSpec("docs/layers/Core_LLD.md"),
    DocSpec("docs/layers/DRS_LLD.md"),
    DocSpec("docs/layers/GCL_LLD.md"),
    DocSpec("docs/layers/PKL_LLD.md"),
    DocSpec("docs/layers/TRF_LLD.md"),
    DocSpec("docs/layers/AAL_LLD.md"),
    DocSpec("docs/layers/GUI_LLD.md"),
    # WBS
    DocSpec("docs/wbs/WBS-0001-poc-spine.md"),
    DocSpec("docs/wbs/WBS-0002-dio-demo-trial.md"),
    DocSpec("docs/wbs/WBS-0003-full-demo-trial.md"),
    DocSpec("docs/wbs/WBS-0004-cap-architecture-enhancements.md"),
    DocSpec("docs/wbs/wrap-rewrite-002-devnex-assistant.md"),
    DocSpec("docs/wbs/wrap-rewrite-003-raglab-main.md"),
    # DevNex internal
    DocSpec("cipher/agents/devnex_assistant/README.md"),
    DocSpec("cipher/agents/devnex_assistant/README_TRACE_PANEL.md"),
    DocSpec("cipher/agents/devnex_assistant/docs/CIPHER_Platform_HLD.md"),
    DocSpec("cipher/agents/devnex_assistant/docs/HLD.md"),
    DocSpec("cipher/agents/devnex_assistant/docs/LLD.md"),
    DocSpec("cipher/agents/devnex_assistant/docs/architecture_mvp_manual.md"),
    DocSpec("cipher/agents/devnex_assistant/docs/CHANGELOG_SPRINT0.md"),
    # Module READMEs (active)
    DocSpec("cipher/README.md"),
    DocSpec("cipher/agents/README.md"),
]

FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def build_frontmatter(spec: DocSpec) -> str:
    lines = [
        "---",
        f"doc_version: {spec.version}",
        f"last_updated: {TODAY}",
        f"owner: {DEFAULT_OWNER}",
        f"status: {spec.status}",
    ]
    if spec.supersedes:
        lines.append(f"supersedes: {spec.supersedes}")
    if spec.superseded_by:
        lines.append(f"superseded_by: {spec.superseded_by}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def build_footer(spec: DocSpec) -> str:
    return (
        "\n\n## Revision History\n\n"
        "| Version | Date | Author | Change |\n"
        "|---------|------|--------|--------|\n"
        f"| {spec.version} | {TODAY} | {DEFAULT_OWNER} | {spec.initial_change} |\n"
    )


def superseded_banner(spec: DocSpec) -> str:
    if spec.status == "superseded" and spec.superseded_by:
        return (
            f"> **Superseded by [{spec.superseded_by}]({Path(spec.superseded_by).name}) "
            f"as of {TODAY}.** Kept for archeology.\n\n"
        )
    if spec.status == "deprecated":
        return (
            f"> **Deprecated as of {TODAY} — historical reference only.**\n\n"
        )
    return ""


def has_frontmatter(text: str) -> bool:
    return bool(FRONTMATTER_RE.match(text))


def apply(spec: DocSpec, root: Path, with_footer: bool) -> str:
    p = root / spec.path
    if not p.exists():
        return f"SKIP (missing): {spec.path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    changed = False
    if not has_frontmatter(text):
        fm = build_frontmatter(spec)
        banner = superseded_banner(spec)
        text = fm + banner + text
        changed = True
    if with_footer and "## Revision History" not in text:
        text = text.rstrip() + build_footer(spec)
        changed = True
    if changed:
        p.write_text(text, encoding="utf-8")
        return f"OK : {spec.path}"
    return f"-- : {spec.path} (already versioned)"


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    print(f"Repo root: {root}\n--- FULL TREATMENT ---")
    for spec in FULL_TREATMENT:
        print(apply(spec, root, with_footer=True))
    print("--- FRONTMATTER-ONLY ---")
    for spec in FRONTMATTER_ONLY:
        print(apply(spec, root, with_footer=False))
    print("--- done ---")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
