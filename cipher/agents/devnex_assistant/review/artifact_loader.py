"""Artifact discovery and validation for the Technical Review pipeline.

Expected inputs for a full SWC review
--------------------------------------
  lld_doc        — LLD document for the SWC  (.md / .csv / .xlsx / .docx / .pdf)
  hld_reqs       — HLD requirements relevant to this SWC  (.md / .csv / .xlsx)
  ut_env         — UT environment description  (.md / .py / .cfg / .yaml / .json)
  ut_doc         — UT test specification / design  (.md / .csv / .xlsx)
  ut_report      — UT execution report  (.xml / .html / .md / .json)
  kw_report      — Klocwork static analysis report  (.xml / .html / .csv / .json)
  trace_hld_lld  — HLD → LLD traceability matrix  (.csv / .xlsx / .md)
  trace_lld_code — LLD → Source code traceability matrix  (.csv / .xlsx / .md)
  trace_lld_ut   — LLD → UT document traceability matrix  (.csv / .xlsx / .md)

All paths are optional at construction time — the loader reports which ones are
missing so R1N1 (completeness check) can emit CRITICAL findings for blockers.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Artifact slots ────────────────────────────────────────────────────────────

ARTIFACT_SLOTS: dict[str, str] = {
    "lld_doc":        "LLD Document",
    "hld_reqs":       "HLD Requirements",
    "ut_env":         "UT Environment",
    "ut_doc":         "UT Document (Test Specification)",
    "ut_report":      "UT Execution Report",
    "kw_report":      "Klocwork Analysis Report",
    "trace_hld_lld":  "Traceability: HLD → LLD",
    "trace_lld_code": "Traceability: LLD → Code",
    "trace_lld_ut":   "Traceability: LLD → UT",
}

# Slots that block the review if absent (CRITICAL) vs. warning (MAJOR)
_CRITICAL_SLOTS = {"lld_doc", "hld_reqs", "kw_report", "ut_report"}
_MAJOR_SLOTS    = {"ut_env", "ut_doc", "trace_hld_lld", "trace_lld_code", "trace_lld_ut"}

# Accepted extensions per slot
_SLOT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "lld_doc":        (".md", ".csv", ".xlsx", ".docx", ".pdf"),
    "hld_reqs":       (".md", ".csv", ".xlsx", ".docx", ".pdf"),
    "ut_env":         (".md", ".py", ".cfg", ".yaml", ".yml", ".json", ".txt"),
    "ut_doc":         (".md", ".csv", ".xlsx", ".docx", ".pdf"),
    "ut_report":      (".xml", ".html", ".md", ".json", ".csv", ".txt"),
    "kw_report":      (".xml", ".html", ".csv", ".json", ".txt"),
    "trace_hld_lld":  (".csv", ".xlsx", ".md", ".json"),
    "trace_lld_code": (".csv", ".xlsx", ".md", ".json"),
    "trace_lld_ut":   (".csv", ".xlsx", ".md", ".json"),
}


# ── ReviewArtifacts dataclass ─────────────────────────────────────────────────

@dataclass
class ReviewArtifacts:
    """Container for all input artifact paths for one SWC review session."""
    lld_doc:        Path | None = None
    hld_reqs:       Path | None = None
    ut_env:         Path | None = None
    ut_doc:         Path | None = None
    ut_report:      Path | None = None
    kw_report:      Path | None = None
    trace_hld_lld:  Path | None = None
    trace_lld_code: Path | None = None
    trace_lld_ut:   Path | None = None

    # ── Path access ──────────────────────────────────────────────────────────

    def get(self, slot: str) -> Path | None:
        return getattr(self, slot, None)

    def as_path_list(self) -> list[str]:
        """Absolute path strings for every present artifact (GCA context injection)."""
        return [str(p) for p in self._present_paths()]

    def as_slot_map(self) -> dict[str, str | None]:
        return {slot: (str(getattr(self, slot)) if getattr(self, slot) else None)
                for slot in ARTIFACT_SLOTS}

    # ── Completeness ─────────────────────────────────────────────────────────

    def missing_critical(self) -> list[str]:
        return [s for s in _CRITICAL_SLOTS if getattr(self, s) is None]

    def missing_major(self) -> list[str]:
        return [s for s in _MAJOR_SLOTS if getattr(self, s) is None]

    def is_complete(self) -> bool:
        return len(self.missing_critical()) == 0 and len(self.missing_major()) == 0

    # ── Content helpers ───────────────────────────────────────────────────────

    def read_text(self, slot: str, max_chars: int = 32_000) -> str:
        """Return text content of the artifact for a given slot (truncated)."""
        path = getattr(self, slot, None)
        if path is None or not path.exists():
            return ""
        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                raw = path.read_text(encoding="utf-8")
                return raw[:max_chars]
            if suffix == ".csv":
                return _read_csv_as_text(path, max_chars)
            if suffix in (".xml", ".html"):
                raw = path.read_text(encoding="utf-8", errors="replace")
                # Strip tags for readability inside prompts
                clean = re.sub(r"<[^>]+>", " ", raw)
                clean = re.sub(r"\s+", " ", clean)
                return clean[:max_chars]
            # .md / .txt / .py / etc.
            return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except Exception:
            return ""

    def _present_paths(self) -> list[Path]:
        return [p for p in (
            self.lld_doc, self.hld_reqs, self.ut_env,
            self.ut_doc, self.ut_report, self.kw_report,
            self.trace_hld_lld, self.trace_lld_code, self.trace_lld_ut,
        ) if p is not None]


# ── Loader ────────────────────────────────────────────────────────────────────

@dataclass
class ArtifactValidationIssue:
    slot:       str
    severity:   str   # "CRITICAL" | "MAJOR" | "MINOR"
    message:    str


def load_artifacts(paths: dict[str, str | Path]) -> tuple[ReviewArtifacts, list[ArtifactValidationIssue]]:
    """
    Construct ReviewArtifacts from a dict of slot → path.
    Also auto-discovers artifacts in an 'artifacts_dir' key if provided.

    Returns (artifacts, issues) where issues contains all validation problems.
    """
    issues: list[ArtifactValidationIssue] = []
    resolved: dict[str, Path | None] = {slot: None for slot in ARTIFACT_SLOTS}

    # Optional auto-discovery from a directory
    artifacts_dir: Path | None = None
    if "artifacts_dir" in paths:
        artifacts_dir = Path(paths["artifacts_dir"])

    for slot in ARTIFACT_SLOTS:
        if slot in paths and paths[slot]:
            p = Path(paths[slot])
            if p.exists() and p.is_file():
                resolved[slot] = p
            else:
                resolved[slot] = None

        if resolved[slot] is None and artifacts_dir:
            resolved[slot] = _auto_discover(slot, artifacts_dir)

    # Validate presence
    for slot in ARTIFACT_SLOTS:
        if resolved[slot] is None:
            sev = "CRITICAL" if slot in _CRITICAL_SLOTS else "MAJOR"
            issues.append(ArtifactValidationIssue(
                slot=slot,
                severity=sev,
                message=f"{ARTIFACT_SLOTS[slot]} not found — provide path or place in artifacts_dir.",
            ))
            continue

        # Validate extension
        ext = resolved[slot].suffix.lower()  # type: ignore[union-attr]
        if ext not in _SLOT_EXTENSIONS.get(slot, ("",)):
            issues.append(ArtifactValidationIssue(
                slot=slot,
                severity="MINOR",
                message=(
                    f"{ARTIFACT_SLOTS[slot]}: unexpected extension '{ext}'. "
                    f"Expected one of {_SLOT_EXTENSIONS[slot]}."
                ),
            ))

        # Validate non-empty
        try:
            size = resolved[slot].stat().st_size  # type: ignore[union-attr]
            if size == 0:
                issues.append(ArtifactValidationIssue(
                    slot=slot,
                    severity="CRITICAL" if slot in _CRITICAL_SLOTS else "MAJOR",
                    message=f"{ARTIFACT_SLOTS[slot]} is empty (0 bytes).",
                ))
        except OSError:
            pass

    artifacts = ReviewArtifacts(
        lld_doc        = resolved["lld_doc"],
        hld_reqs       = resolved["hld_reqs"],
        ut_env         = resolved["ut_env"],
        ut_doc         = resolved["ut_doc"],
        ut_report      = resolved["ut_report"],
        kw_report      = resolved["kw_report"],
        trace_hld_lld  = resolved["trace_hld_lld"],
        trace_lld_code = resolved["trace_lld_code"],
        trace_lld_ut   = resolved["trace_lld_ut"],
    )
    return artifacts, issues


# ── Auto-discovery helpers ────────────────────────────────────────────────────

_DISCOVERY_PATTERNS: dict[str, list[str]] = {
    "lld_doc":        ["*LLD*", "*lld*", "*Low_Level*"],
    "hld_reqs":       ["*HLD*", "*hld*", "*High_Level*", "*SWE.1*"],
    "ut_env":         ["*ut_env*", "*test_env*", "*pytest*", "*conftest*"],
    "ut_doc":         ["*UT_doc*", "*test_spec*", "*UTD*", "*Test_Design*"],
    "ut_report":      ["*UT_report*", "*test_report*", "*junit*", "*coverage*"],
    "kw_report":      ["*kw_*", "*klocwork*", "*KW_*", "*static_analysis*"],
    "trace_hld_lld":  ["*HLD_LLD*", "*hld_lld*", "*HLD*LLD*Trace*"],
    "trace_lld_code": ["*LLD_Code*", "*lld_code*", "*LLD*Code*Trace*"],
    "trace_lld_ut":   ["*LLD_UT*", "*lld_ut*", "*LLD*UT*Trace*", "*LLD*Test*Trace*"],
}


def _auto_discover(slot: str, directory: Path) -> Path | None:
    """Search directory for a file matching slot discovery patterns."""
    if not directory.is_dir():
        return None
    for pattern in _DISCOVERY_PATTERNS.get(slot, []):
        matches = list(directory.glob(pattern))
        if matches:
            # Prefer files over directories; pick most recently modified
            files = [m for m in matches if m.is_file()]
            if files:
                return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return None


def _read_csv_as_text(path: Path, max_chars: int) -> str:
    """Convert CSV to a readable table string."""
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
        lines = [" | ".join(row) for row in rows]
        return "\n".join(lines)[:max_chars]
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
