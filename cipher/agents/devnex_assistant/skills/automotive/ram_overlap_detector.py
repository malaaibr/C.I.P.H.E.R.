"""
ram_overlap_detector.py — UC 4.4 Milestone M2
==============================================
Consume a ``section_layout.json`` (from map_analyzer.py M1) and detect
address-range overlaps between RAM sections.

This is the *semantic* conflict detector that git cannot provide: after a clean
merge, the linker may place DMA_Buffer and ISR_Stack at the same physical RAM
address because their allocations came from independent branches that each
modified different files (linker script vs. DMA init code).

ASIL-D relevance
----------------
A DMA buffer overlapping the ISR stack is a safety-critical undefined
behaviour per MISRA-C:2012 Rule 1.3 (``undefined behaviour shall not occur``)
and Rule 11.8 (``cast not remove const/volatile``).  The detector hard-stops
the pipeline and mandates a Safety Engineer G5 gate review.

Algorithm
---------
1. Sort RAM sections by start address (ascending).
2. Sweep with a "high-water mark" (``hwm``):
   - For each section i:  if ``section[i].start < hwm``, overlap detected.
   - ``hwm`` = max(hwm, section[i].end) after every step.
3. Emit each overlap as an :class:`OverlapRecord` with:
   - The two conflicting section names
   - Exact overlap byte range [overlap_start, overlap_end)
   - Overlap size in bytes
   - ASIL classification and recommended action

Usage
-----
    from skills.automotive.ram_overlap_detector import RamOverlapDetector

    detector = RamOverlapDetector(asil_level="D")
    report   = detector.run(section_layout_json=Path("artifacts/section_layout.json"))
    detector.write_json(report, Path("artifacts/overlap_report.json"))
    if report.has_overlap:
        raise SemanticConflictError(report.summary)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

# ── ASIL action table ─────────────────────────────────────────────────────────

_ASIL_ACTION: Final[dict[str, str]] = {
    "D":  "HARD_BLOCK — Safety Engineer G5 gate MANDATORY",
    "C":  "HOLD — Safety Engineer review required before merge",
    "B":  "HOLD — BSW / Tech Lead review required",
    "A":  "WARN — Tech Lead review recommended",
    "QM": "WARN — Developer review recommended",
}

_ASIL_REQUIRE_SAFETY_ENGINEER: Final[dict[str, bool]] = {
    "D": True, "C": True, "B": False, "A": False, "QM": False,
}


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class OverlapRecord:
    """One detected address-range collision between two RAM sections."""

    section_a:        str   # name of first overlapping section
    section_b:        str   # name of second overlapping section
    a_start:          int
    a_end:            int
    b_start:          int
    b_end:            int
    overlap_start:    int   # first overlapping byte address
    overlap_end:      int   # exclusive upper bound of overlap
    overlap_size:     int   # bytes
    asil_action:      str
    require_safety_engineer: bool

    @property
    def summary(self) -> str:
        return (
            f"OVERLAP: {self.section_a}[0x{self.a_start:08X}–0x{self.a_end-1:08X}] "
            f"∩ {self.section_b}[0x{self.b_start:08X}–0x{self.b_end-1:08X}] "
            f"= 0x{self.overlap_start:08X}–0x{self.overlap_end-1:08X} "
            f"({self.overlap_size} bytes) | {self.asil_action}"
        )


@dataclass
class OverlapReport:
    """Full result from one detector run."""

    source_layout:            str
    asil_level:               str
    has_overlap:              bool
    overlaps:                 list[OverlapRecord] = field(default_factory=list)
    total_overlapping_bytes:  int = 0
    recommended_action:       str = "PASS"
    require_safety_engineer:  bool = False

    @property
    def summary(self) -> str:
        if not self.has_overlap:
            return "No RAM overlaps detected."
        lines = [f"SEMANTIC CONFLICT DETECTED ({len(self.overlaps)} overlap(s)):"]
        for ov in self.overlaps:
            lines.append(f"  • {ov.summary}")
        lines.append(f"  Recommended action: {self.recommended_action}")
        return "\n".join(lines)


# ── Detector ──────────────────────────────────────────────────────────────────


class RamOverlapDetector:
    """
    Detect address-range overlaps among RAM sections.

    Parameters
    ----------
    asil_level : str
        ASIL level for this merge context (``"D"``, ``"C"``, ``"B"``,
        ``"A"``, or ``"QM"``).  Determines the recommended action in the
        overlap report.
    """

    def __init__(self, asil_level: str = "D") -> None:
        if asil_level not in _ASIL_ACTION:
            raise ValueError(
                f"Unknown ASIL level '{asil_level}'. "
                f"Valid values: {list(_ASIL_ACTION)}"
            )
        self._asil_level = asil_level

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, section_layout_json: Path) -> OverlapReport:
        """
        Load *section_layout_json* and return an :class:`OverlapReport`.

        Parameters
        ----------
        section_layout_json : Path
            Output of ``MapAnalyzer.write_json()`` — the ``section_layout.json``
            artifact from M1.

        Returns
        -------
        OverlapReport
            ``has_overlap=True`` when any two RAM sections share addresses.

        Raises
        ------
        FileNotFoundError
            When *section_layout_json* does not exist.
        """
        if not section_layout_json.exists():
            raise FileNotFoundError(
                f"section_layout.json not found: {section_layout_json}"
            )

        raw = json.loads(section_layout_json.read_text(encoding="utf-8"))
        sections = self._load_sections(raw.get("ram_sections", []))

        report = OverlapReport(
            source_layout=str(section_layout_json.resolve()),
            asil_level=self._asil_level,
            has_overlap=False,
        )

        overlaps = self._sweep(sections)
        if overlaps:
            report.has_overlap = True
            report.overlaps = overlaps
            report.total_overlapping_bytes = sum(ov.overlap_size for ov in overlaps)
            report.recommended_action = _ASIL_ACTION[self._asil_level]
            report.require_safety_engineer = _ASIL_REQUIRE_SAFETY_ENGINEER[
                self._asil_level
            ]

        return report

    def run_from_layout(self, ram_sections: list[dict]) -> OverlapReport:
        """
        Detect overlaps from an in-memory list of section dicts (test helper).

        Parameters
        ----------
        ram_sections : list[dict]
            Each dict must have ``name``, ``start``, ``end`` integer keys.
        """
        sections = self._load_sections(ram_sections)
        report = OverlapReport(
            source_layout="<in-memory>",
            asil_level=self._asil_level,
            has_overlap=False,
        )
        overlaps = self._sweep(sections)
        if overlaps:
            report.has_overlap = True
            report.overlaps = overlaps
            report.total_overlapping_bytes = sum(ov.overlap_size for ov in overlaps)
            report.recommended_action = _ASIL_ACTION[self._asil_level]
            report.require_safety_engineer = _ASIL_REQUIRE_SAFETY_ENGINEER[
                self._asil_level
            ]
        return report

    def write_json(self, report: OverlapReport, out_path: Path) -> None:
        """
        Serialise *report* to *out_path* as UTF-8 JSON.
        """
        def _ser_overlap(ov: OverlapRecord) -> dict:
            d = asdict(ov)
            d["overlap_start_hex"] = f"0x{ov.overlap_start:08X}"
            d["overlap_end_hex"]   = f"0x{ov.overlap_end-1:08X}"  # inclusive
            d["a_start_hex"]       = f"0x{ov.a_start:08X}"
            d["b_start_hex"]       = f"0x{ov.b_start:08X}"
            d["summary"]           = ov.summary
            return d

        payload = {
            "source_layout":           report.source_layout,
            "asil_level":              report.asil_level,
            "has_overlap":             report.has_overlap,
            "total_overlapping_bytes": report.total_overlapping_bytes,
            "recommended_action":      report.recommended_action,
            "require_safety_engineer": report.require_safety_engineer,
            "summary":                 report.summary,
            "overlaps":                [_ser_overlap(ov) for ov in report.overlaps],
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_sections(raw: list[dict]) -> list[tuple[str, int, int]]:
        """Parse raw JSON section dicts to (name, start, end) tuples."""
        sections = []
        for s in raw:
            name  = s["name"]
            start = s["start"]
            end   = s["end"]
            sections.append((name, start, end))
        # Sort ascending by start address for the sweep
        sections.sort(key=lambda t: t[1])
        return sections

    def _sweep(
        self, sections: list[tuple[str, int, int]]
    ) -> list[OverlapRecord]:
        """
        High-water-mark sweep.  O(n log n) — dominated by sort in _load_sections.

        Returns a list of :class:`OverlapRecord` for every detected collision.
        """
        overlaps: list[OverlapRecord] = []
        hwm_end   = 0
        hwm_name  = ""
        hwm_start = 0

        for name, start, end in sections:
            if start < hwm_end:
                # Overlap detected: [start, min(end, hwm_end))
                ov_start = start
                ov_end   = min(end, hwm_end)
                overlaps.append(
                    OverlapRecord(
                        section_a=hwm_name,
                        section_b=name,
                        a_start=hwm_start,
                        a_end=hwm_end,
                        b_start=start,
                        b_end=end,
                        overlap_start=ov_start,
                        overlap_end=ov_end,
                        overlap_size=ov_end - ov_start,
                        asil_action=_ASIL_ACTION[self._asil_level],
                        require_safety_engineer=_ASIL_REQUIRE_SAFETY_ENGINEER[
                            self._asil_level
                        ],
                    )
                )
            # Advance high-water mark
            if end > hwm_end:
                hwm_end   = end
                hwm_name  = name
                hwm_start = start

        return overlaps
