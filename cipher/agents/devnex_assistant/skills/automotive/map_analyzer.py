"""
map_analyzer.py — UC 4.4 Milestone M1
=======================================
Parse an arm-none-eabi-ld linker map file and emit a structured
``section_layout.json`` describing every memory section: name,
start address, size, end address, and whether it falls in the
MCU RAM address space.

ASPICE SWE.2 artifact: this module produces the primary input data
for ram_overlap_detector.py (M2).

MISRA-C context: this is a Python analysis tool, not embedded C.
The *output* JSON is consumed by MISRA-C auditing logic.

Usage
-----
    from skills.automotive.map_analyzer import MapAnalyzer, SectionEntry

    analyzer = MapAnalyzer(ram_base=0x20000000, ram_top=0x2FFFFFFF)
    layout   = analyzer.parse(Path("build/firmware.map"))
    analyzer.write_json(layout, Path("artifacts/section_layout.json"))
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

# ── Constants ─────────────────────────────────────────────────────────────────

# Default STM32 Cortex-M SRAM window — caller may override via MapAnalyzer().
_DEFAULT_RAM_BASE: Final[int] = 0x20000000
_DEFAULT_RAM_TOP:  Final[int] = 0x2FFFFFFF

# Regex: top-level section header line from arm-none-eabi-ld .map output.
# Examples that must match:
#   .bss            0x0000000020010200    0x00000400
#   .stack          0x0000000020010600    0x00000800
#   DMA_Buffer      0x0000000020010000    0x00000400
#   ISR_Stack       0x0000000020010000    0x00000800   (overlap scenario)
_SECTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<name>[\.\w]+)\s+"
    r"(?P<addr>0x[0-9a-fA-F]{8,16})\s+"
    r"(?P<size>0x[0-9a-fA-F]+)"
    r"(?:\s+load address\s+(?P<lma>0x[0-9a-fA-F]+))?"
    r"\s*$",
    re.IGNORECASE,
)

# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class SectionEntry:
    """One parsed section from the linker map."""

    name:    str
    start:   int    # VMA — virtual memory address
    size:    int    # bytes
    end:     int    # exclusive upper bound: start + size
    lma:     int    # LMA — load memory address (0 when absent)
    in_ram:  bool   # True when VMA falls inside the configured RAM window


@dataclass
class SectionLayout:
    """Full parse result for one .map file."""

    source_file:   str
    ram_base:      int
    ram_top:       int
    sections:      list[SectionEntry] = field(default_factory=list)
    ram_sections:  list[SectionEntry] = field(default_factory=list)

    # Convenience computed during serialisation
    total_sections: int = 0
    total_ram_sections: int = 0

    def _refresh_counts(self) -> None:
        self.total_sections = len(self.sections)
        self.total_ram_sections = len(self.ram_sections)


# ── Analyzer ──────────────────────────────────────────────────────────────────


class MapAnalyzer:
    """
    Parse arm-none-eabi-ld linker map → :class:`SectionLayout`.

    Parameters
    ----------
    ram_base : int
        Inclusive lower bound of the MCU SRAM window (default 0x20000000).
    ram_top : int
        Inclusive upper bound of the MCU SRAM window (default 0x2FFFFFFF).
    """

    def __init__(
        self,
        ram_base: int = _DEFAULT_RAM_BASE,
        ram_top:  int = _DEFAULT_RAM_TOP,
    ) -> None:
        self._ram_base = ram_base
        self._ram_top  = ram_top

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self, map_path: Path) -> SectionLayout:
        """
        Parse *map_path* and return a :class:`SectionLayout`.

        Parameters
        ----------
        map_path : Path
            Absolute or relative path to the .map file produced by the
            arm-none-eabi-ld linker.

        Returns
        -------
        SectionLayout
            All sections found; ``ram_sections`` pre-filtered to SRAM window.

        Raises
        ------
        FileNotFoundError
            When *map_path* does not exist.
        """
        if not map_path.exists():
            raise FileNotFoundError(f"Map file not found: {map_path}")

        raw = map_path.read_text(encoding="utf-8", errors="replace")
        layout = SectionLayout(
            source_file=str(map_path.resolve()),
            ram_base=self._ram_base,
            ram_top=self._ram_top,
        )

        in_linker_map_block = False
        for line in raw.splitlines():
            stripped = line.strip()

            # The linker map body begins after this header line.
            if "Linker script and memory map" in stripped:
                in_linker_map_block = True
                continue

            if not in_linker_map_block:
                continue

            m = _SECTION_RE.match(stripped)
            if m is None:
                continue

            name = m.group("name")
            addr = int(m.group("addr"), 16)
            size = int(m.group("size"), 16)
            lma_raw = m.group("lma")
            lma  = int(lma_raw, 16) if lma_raw else 0

            if size == 0:
                continue  # empty NOLOAD section — skip

            in_ram = self._ram_base <= addr <= self._ram_top
            entry = SectionEntry(
                name=name,
                start=addr,
                size=size,
                end=addr + size,
                lma=lma,
                in_ram=in_ram,
            )
            layout.sections.append(entry)
            if in_ram:
                layout.ram_sections.append(entry)

        layout._refresh_counts()
        return layout

    def write_json(self, layout: SectionLayout, out_path: Path) -> None:
        """
        Serialise *layout* to *out_path* as UTF-8 JSON.

        Parameters
        ----------
        layout : SectionLayout
            Result from :meth:`parse`.
        out_path : Path
            Destination file path; parent directories must exist.
        """
        layout._refresh_counts()

        def _ser(obj: object) -> object:
            if isinstance(obj, SectionEntry):
                d = asdict(obj)
                # Add hex representations for readability
                d["start_hex"] = f"0x{obj.start:08X}"
                d["end_hex"]   = f"0x{obj.end:08X}"
                d["size_hex"]  = f"0x{obj.size:08X}"
                return d
            raise TypeError(f"Unserializable type: {type(obj)!r}")

        payload = {
            "source_file":        layout.source_file,
            "ram_base_hex":       f"0x{layout.ram_base:08X}",
            "ram_top_hex":        f"0x{layout.ram_top:08X}",
            "total_sections":     layout.total_sections,
            "total_ram_sections": layout.total_ram_sections,
            "sections":           [_ser(s) for s in layout.sections],
            "ram_sections":       [_ser(s) for s in layout.ram_sections],
        }
        out_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
