"""
test_uc4_4.py — UC 4.4 Test Suite
===================================
Tests for the semantic memory-map overlap detection pipeline.

Canonical UC 4.4 scenario
--------------------------
Two independent branches are merged:

  Branch A (dma-feature):   adds DMA_Buffer at 0x20010000, size 0x400 (1 KB)
  Branch B (isr-stack):     adds ISR_Stack  at 0x20010000, size 0x800 (2 KB)

Git reports zero conflicts (different files were modified), but the merged
linker map shows both sections starting at the same address.

Result:
  DMA_Buffer  [0x20010000 – 0x200103FF]
  ISR_Stack   [0x20010000 – 0x200107FF]
  Overlap:    [0x20010000 – 0x200103FF]  (1024 bytes, ASIL-D HARD BLOCK)

Test structure
--------------
TestMapAnalyzer        — M1: .map parsing
TestRamOverlapDetector — M2: sweep algorithm (canonical + edge cases)
TestLinkerScriptParser — M1b: .ld MEMORY block extraction
TestAsilGate           — M3: ASIL decision table
TestUC44Integration    — end-to-end with temp files
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from skills.automotive.map_analyzer import MapAnalyzer, SectionEntry, SectionLayout
from skills.automotive.ram_overlap_detector import RamOverlapDetector, OverlapReport
from skills.automotive.linker_script_parser import LinkerScriptParser, MemoryRegion
from gcl.asil_gate import AsilGate, AsilDecision, SemanticConflictError


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

# Canonical UC 4.4 .map file content — two sections at the same address.
CANONICAL_MAP = textwrap.dedent("""\
    Archive member included to satisfy reference by file (symbol)
    ...

    Linker script and memory map

    .text           0x0000000008000000    0x00012345
    .data           0x0000000020000000    0x00000080
    .bss            0x0000000020000100    0x00000200
    DMA_Buffer      0x0000000020010000    0x00000400
    ISR_Stack       0x0000000020010000    0x00000800
    .heap           0x0000000020020000    0x00001000
""")

# Map with no overlaps
CLEAN_MAP = textwrap.dedent("""\
    Linker script and memory map

    .text           0x0000000008000000    0x00012345
    .data           0x0000000020000000    0x00000080
    .bss            0x0000000020000100    0x00000200
    DMA_Buffer      0x0000000020010000    0x00000400
    ISR_Stack       0x0000000020010400    0x00000800
""")

# Canonical STM32H7 linker script fragment
CANONICAL_LDS = textwrap.dedent("""\
    /* STM32H7 linker script — UC 4.4 test fixture */
    MEMORY
    {
      FLASH (rx)   : ORIGIN = 0x08000000, LENGTH = 2048K
      RAM   (xrw)  : ORIGIN = 0x20000000, LENGTH = 512K
      DTCM  (xrw)  : ORIGIN = 0x20000000, LENGTH = 128K
    }
    SECTIONS
    {
      .text : {
        *(.text)
      } >FLASH AT>FLASH

      .data : {
        *(.data)
      } >RAM AT>FLASH

      .bss (NOLOAD) : {
        *(.bss)
      } >RAM

      .dma_buffer (NOLOAD) : {
        DMA_Buffer = .;
        *(.dma_buffer)
        . = ALIGN(4);
      } >RAM
    }
""")


@pytest.fixture
def tmp_map_overlap(tmp_path: Path) -> Path:
    """Write canonical UC 4.4 overlap scenario to a temp .map file."""
    p = tmp_path / "firmware.map"
    p.write_text(CANONICAL_MAP, encoding="utf-8")
    return p


@pytest.fixture
def tmp_map_clean(tmp_path: Path) -> Path:
    """Write a clean (no-overlap) .map file."""
    p = tmp_path / "firmware_clean.map"
    p.write_text(CLEAN_MAP, encoding="utf-8")
    return p


@pytest.fixture
def tmp_lds(tmp_path: Path) -> Path:
    """Write canonical linker script to temp file."""
    p = tmp_path / "stm32h7xx_flash.ld"
    p.write_text(CANONICAL_LDS, encoding="utf-8")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# TestMapAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestMapAnalyzer:
    """Unit tests for map_analyzer.MapAnalyzer (M1)."""

    def test_parse_returns_section_layout(self, tmp_map_overlap: Path) -> None:
        layout = MapAnalyzer().parse(tmp_map_overlap)
        assert isinstance(layout, SectionLayout)

    def test_total_sections_count(self, tmp_map_overlap: Path) -> None:
        layout = MapAnalyzer().parse(tmp_map_overlap)
        # .text, .data, .bss, DMA_Buffer, ISR_Stack, .heap = 6
        assert layout.total_sections == 6

    def test_ram_sections_filtered_correctly(self, tmp_map_overlap: Path) -> None:
        layout = MapAnalyzer().parse(tmp_map_overlap)
        # .data .bss DMA_Buffer ISR_Stack .heap are in RAM; .text is FLASH
        assert layout.total_ram_sections == 5
        names = {s.name for s in layout.ram_sections}
        assert "DMA_Buffer" in names
        assert "ISR_Stack"  in names
        assert ".text"      not in names

    def test_dma_buffer_address(self, tmp_map_overlap: Path) -> None:
        layout = MapAnalyzer().parse(tmp_map_overlap)
        dma = next(s for s in layout.ram_sections if s.name == "DMA_Buffer")
        assert dma.start == 0x20010000
        assert dma.size  == 0x400
        assert dma.end   == 0x20010400

    def test_isr_stack_address(self, tmp_map_overlap: Path) -> None:
        layout = MapAnalyzer().parse(tmp_map_overlap)
        isr = next(s for s in layout.ram_sections if s.name == "ISR_Stack")
        assert isr.start == 0x20010000
        assert isr.size  == 0x800
        assert isr.end   == 0x20010800

    def test_write_json_produces_valid_json(
        self, tmp_map_overlap: Path, tmp_path: Path
    ) -> None:
        analyzer  = MapAnalyzer()
        layout    = analyzer.parse(tmp_map_overlap)
        out       = tmp_path / "section_layout.json"
        analyzer.write_json(layout, out)
        data = json.loads(out.read_text())
        assert data["total_ram_sections"] == 5
        assert "ram_base_hex" in data

    def test_section_hex_fields_in_json(
        self, tmp_map_overlap: Path, tmp_path: Path
    ) -> None:
        analyzer = MapAnalyzer()
        layout   = analyzer.parse(tmp_map_overlap)
        out      = tmp_path / "sl.json"
        analyzer.write_json(layout, out)
        data  = json.loads(out.read_text())
        first = data["ram_sections"][0]
        assert "start_hex" in first
        assert first["start_hex"].startswith("0x")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            MapAnalyzer().parse(tmp_path / "nonexistent.map")

    def test_empty_sections_skipped(self, tmp_path: Path) -> None:
        """Sections with size 0x0 must be ignored."""
        content = textwrap.dedent("""\
            Linker script and memory map
            .empty          0x0000000020000000    0x00000000
            .real_section   0x0000000020000100    0x00000100
        """)
        p = tmp_path / "fw.map"
        p.write_text(content)
        layout = MapAnalyzer().parse(p)
        assert layout.total_sections == 1
        assert layout.sections[0].name == ".real_section"


# ─────────────────────────────────────────────────────────────────────────────
# TestRamOverlapDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestRamOverlapDetector:
    """Unit tests for ram_overlap_detector.RamOverlapDetector (M2)."""

    # ── in-memory helpers ─────────────────────────────────────────────────────

    def _sections(self, *args: tuple[str, int, int]) -> list[dict]:
        """Build section dicts from (name, start, size) tuples."""
        return [
            {"name": n, "start": s, "end": s + sz, "size": sz, "in_ram": True}
            for n, s, sz in args
        ]

    # ── Canonical UC 4.4 scenario ─────────────────────────────────────────────

    def test_canonical_overlap_detected(self) -> None:
        sections = self._sections(
            ("DMA_Buffer", 0x20010000, 0x400),
            ("ISR_Stack",  0x20010000, 0x800),
        )
        rpt = RamOverlapDetector(asil_level="D").run_from_layout(sections)
        assert rpt.has_overlap is True
        assert len(rpt.overlaps) == 1

    def test_canonical_overlap_range(self) -> None:
        sections = self._sections(
            ("DMA_Buffer", 0x20010000, 0x400),
            ("ISR_Stack",  0x20010000, 0x800),
        )
        rpt = RamOverlapDetector(asil_level="D").run_from_layout(sections)
        ov  = rpt.overlaps[0]
        assert ov.overlap_start == 0x20010000
        assert ov.overlap_end   == 0x20010400   # min(end_A, end_B) = min(0x400,0x800) end
        assert ov.overlap_size  == 0x400  # 1024 bytes

    def test_canonical_asil_d_action(self) -> None:
        sections = self._sections(
            ("DMA_Buffer", 0x20010000, 0x400),
            ("ISR_Stack",  0x20010000, 0x800),
        )
        rpt = RamOverlapDetector(asil_level="D").run_from_layout(sections)
        assert "HARD_BLOCK" in rpt.recommended_action
        assert rpt.require_safety_engineer is True

    # ── Clean scenario ────────────────────────────────────────────────────────

    def test_no_overlap_clean(self) -> None:
        sections = self._sections(
            ("DMA_Buffer", 0x20010000, 0x400),
            ("ISR_Stack",  0x20010400, 0x800),  # immediately after DMA_Buffer
        )
        rpt = RamOverlapDetector(asil_level="D").run_from_layout(sections)
        assert rpt.has_overlap is False
        assert rpt.overlaps == []

    def test_adjacent_boundary_not_overlap(self) -> None:
        """End of section A == start of section B is NOT an overlap."""
        sections = self._sections(
            ("sec_a", 0x20000000, 0x100),
            ("sec_b", 0x20000100, 0x100),  # start == end of sec_a
        )
        rpt = RamOverlapDetector(asil_level="QM").run_from_layout(sections)
        assert rpt.has_overlap is False

    def test_single_byte_overlap(self) -> None:
        """sec_b starts 1 byte before the end of sec_a."""
        sections = self._sections(
            ("sec_a", 0x20000000, 0x100),
            ("sec_b", 0x200000FF, 0x100),  # overlaps by 1 byte
        )
        rpt = RamOverlapDetector(asil_level="B").run_from_layout(sections)
        assert rpt.has_overlap is True
        assert rpt.overlaps[0].overlap_size == 1

    def test_three_way_overlap_detected(self) -> None:
        """Three sections all starting at the same address."""
        sections = self._sections(
            ("sec_a", 0x20010000, 0x100),
            ("sec_b", 0x20010000, 0x200),
            ("sec_c", 0x20010000, 0x300),
        )
        rpt = RamOverlapDetector(asil_level="D").run_from_layout(sections)
        assert rpt.has_overlap is True
        assert len(rpt.overlaps) >= 2

    # ── ASIL level actions ────────────────────────────────────────────────────

    @pytest.mark.parametrize("asil,expected_action", [
        ("D",  "HARD_BLOCK"),
        ("C",  "HOLD"),
        ("B",  "HOLD"),
        ("A",  "WARN"),
        ("QM", "WARN"),
    ])
    def test_asil_action_strings(self, asil: str, expected_action: str) -> None:
        sections = self._sections(("x", 0x20000000, 0x100), ("y", 0x20000000, 0x200))
        rpt = RamOverlapDetector(asil_level=asil).run_from_layout(sections)
        assert expected_action in rpt.recommended_action

    def test_invalid_asil_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown ASIL level"):
            RamOverlapDetector(asil_level="X")

    # ── JSON output ───────────────────────────────────────────────────────────

    def test_write_json_no_overlap(self, tmp_path: Path, tmp_map_clean: Path) -> None:
        analyzer = MapAnalyzer()
        layout   = analyzer.parse(tmp_map_clean)
        layout_json = tmp_path / "sl.json"
        analyzer.write_json(layout, layout_json)

        detector = RamOverlapDetector(asil_level="D")
        rpt      = detector.run(layout_json)
        out      = tmp_path / "overlap_report.json"
        detector.write_json(rpt, out)

        data = json.loads(out.read_text())
        assert data["has_overlap"] is False
        assert data["overlaps"] == []

    def test_write_json_overlap(self, tmp_path: Path, tmp_map_overlap: Path) -> None:
        analyzer = MapAnalyzer()
        layout   = analyzer.parse(tmp_map_overlap)
        layout_json = tmp_path / "sl.json"
        analyzer.write_json(layout, layout_json)

        detector = RamOverlapDetector(asil_level="D")
        rpt      = detector.run(layout_json)
        out      = tmp_path / "overlap_report.json"
        detector.write_json(rpt, out)

        data = json.loads(out.read_text())
        assert data["has_overlap"] is True
        assert len(data["overlaps"]) >= 1
        assert data["overlaps"][0]["overlap_start_hex"] == "0x20010000"

    def test_missing_layout_json_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            RamOverlapDetector().run(tmp_path / "nonexistent.json")


# ─────────────────────────────────────────────────────────────────────────────
# TestLinkerScriptParser
# ─────────────────────────────────────────────────────────────────────────────

class TestLinkerScriptParser:
    """Unit tests for linker_script_parser.LinkerScriptParser (M1b)."""

    def test_parse_memory_regions(self, tmp_lds: Path) -> None:
        layout = LinkerScriptParser().parse(tmp_lds)
        names  = {r.name for r in layout.regions}
        assert "FLASH" in names
        assert "RAM"   in names
        assert "DTCM"  in names

    def test_flash_origin(self, tmp_lds: Path) -> None:
        layout = LinkerScriptParser().parse(tmp_lds)
        flash  = next(r for r in layout.regions if r.name == "FLASH")
        assert flash.origin == 0x08000000

    def test_ram_is_writable(self, tmp_lds: Path) -> None:
        layout = LinkerScriptParser().parse(tmp_lds)
        ram    = next(r for r in layout.regions if r.name == "RAM")
        assert ram.is_ram is True

    def test_flash_not_ram(self, tmp_lds: Path) -> None:
        layout = LinkerScriptParser().parse(tmp_lds)
        flash  = next(r for r in layout.regions if r.name == "FLASH")
        assert flash.is_ram is False

    def test_ram_length(self, tmp_lds: Path) -> None:
        layout = LinkerScriptParser().parse(tmp_lds)
        ram    = next(r for r in layout.regions if r.name == "RAM")
        assert ram.length == 512 * 1024

    def test_write_json(self, tmp_lds: Path, tmp_path: Path) -> None:
        parser = LinkerScriptParser()
        layout = parser.parse(tmp_lds)
        out    = tmp_path / "declared_regions.json"
        parser.write_json(layout, out)
        data   = json.loads(out.read_text())
        assert len(data["regions"]) == 3
        assert len(data["ram_regions"]) >= 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            LinkerScriptParser().parse(tmp_path / "ghost.ld")


# ─────────────────────────────────────────────────────────────────────────────
# TestAsilGate
# ─────────────────────────────────────────────────────────────────────────────

class TestAsilGate:
    """Unit tests for gcl.asil_gate.AsilGate (M3)."""

    # ── Decision table ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("asil,has_overlap,expected_action", [
        ("D",  True,  "HARD_BLOCK"),
        ("C",  True,  "HOLD"),
        ("B",  True,  "HOLD"),
        ("A",  True,  "WARN"),
        ("QM", True,  "WARN"),
        ("D",  False, "PASS"),
        ("C",  False, "PASS"),
        ("B",  False, "PASS"),
        ("A",  False, "PASS"),
        ("QM", False, "PASS"),
    ])
    def test_decision_table(
        self, asil: str, has_overlap: bool, expected_action: str
    ) -> None:
        gate     = AsilGate(asil)
        decision = gate.evaluate(has_overlap)
        assert decision.action == expected_action

    def test_asil_d_overlap_is_blocking(self) -> None:
        decision = AsilGate("D").evaluate(has_overlap=True)
        assert decision.is_blocking is True

    def test_asil_d_no_overlap_not_blocking(self) -> None:
        decision = AsilGate("D").evaluate(has_overlap=False)
        assert decision.is_blocking is False

    def test_asil_qm_overlap_not_blocking(self) -> None:
        decision = AsilGate("QM").evaluate(has_overlap=True)
        assert decision.is_blocking is False

    def test_asil_d_requires_safety_engineer(self) -> None:
        decision = AsilGate("D").evaluate(has_overlap=True)
        assert decision.require_safety_engineer is True

    def test_asil_b_no_safety_engineer(self) -> None:
        decision = AsilGate("B").evaluate(has_overlap=True)
        assert decision.require_safety_engineer is False

    def test_asil_d_gate_is_g5(self) -> None:
        decision = AsilGate("D").evaluate(has_overlap=True)
        assert decision.gate == "G5"

    def test_pass_decision_gate(self) -> None:
        decision = AsilGate("D").evaluate(has_overlap=False)
        assert decision.gate == "PASS"

    # ── enforce() raises on HARD_BLOCK ────────────────────────────────────────

    def test_enforce_asil_d_raises(self) -> None:
        with pytest.raises(SemanticConflictError, match="HARD BLOCK"):
            AsilGate("D").enforce(has_overlap=True)

    def test_enforce_asil_c_does_not_raise(self) -> None:
        # HOLD is blocking but does NOT raise — returns the decision
        decision = AsilGate("C").enforce(has_overlap=True)
        assert decision.action == "HOLD"

    def test_enforce_no_overlap_returns_pass(self) -> None:
        decision = AsilGate("D").enforce(has_overlap=False)
        assert decision.action == "PASS"

    def test_invalid_asil_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown ASIL level"):
            AsilGate("Z")


# ─────────────────────────────────────────────────────────────────────────────
# TestUC44Integration
# ─────────────────────────────────────────────────────────────────────────────

class TestUC44Integration:
    """
    End-to-end integration: M1 → M2 → M3 pipeline with real files.

    These tests do NOT invoke GCA (gca_invoker=None) — they test the
    analysis pipeline only.
    """

    class _MockRunContext:
        """Minimal DevNexRunContext shim for testing."""

        def __init__(self, cfg: dict, artifacts: Path) -> None:
            self.config    = cfg
            self._artifacts = artifacts

        def get_artifacts_path(self) -> Path:
            return self._artifacts

    def test_full_pipeline_overlap_raises(
        self, tmp_path: Path, tmp_map_overlap: Path, tmp_lds: Path
    ) -> None:
        """Full pipeline with overlap must raise SemanticConflictError."""
        from skills.automotive.uc4_4_skill import UC44SemanticConflictSkill

        ctx = self._MockRunContext(
            cfg={
                "map_file":   str(tmp_map_overlap),
                "lds_file":   str(tmp_lds),
                "asil_level": "D",
            },
            artifacts=tmp_path / "artifacts",
        )
        (tmp_path / "artifacts").mkdir()
        skill = UC44SemanticConflictSkill(run_context=ctx, gca_invoker=None)

        with pytest.raises(SemanticConflictError):
            skill.run()

    def test_full_pipeline_overlap_artifacts_written(
        self, tmp_path: Path, tmp_map_overlap: Path, tmp_lds: Path
    ) -> None:
        """Even when hard-blocked, artifacts must be written for Safety Engineer."""
        from skills.automotive.uc4_4_skill import UC44SemanticConflictSkill

        arts = tmp_path / "artifacts"
        arts.mkdir()
        ctx  = self._MockRunContext(
            cfg={
                "map_file":   str(tmp_map_overlap),
                "lds_file":   str(tmp_lds),
                "asil_level": "D",
            },
            artifacts=arts,
        )
        skill = UC44SemanticConflictSkill(run_context=ctx, gca_invoker=None)

        with pytest.raises(SemanticConflictError):
            skill.run()

        # All four key artifacts must exist regardless of hard block
        assert (arts / "section_layout.json").exists()
        assert (arts / "overlap_report.json").exists()
        assert (arts / "asil_gate_decision.json").exists()
        assert (arts / "semantic_conflict_report.md").exists()

    def test_full_pipeline_no_overlap_passes(
        self, tmp_path: Path, tmp_map_clean: Path, tmp_lds: Path
    ) -> None:
        """Clean map must pass without raising and return status='pass'."""
        from skills.automotive.uc4_4_skill import UC44SemanticConflictSkill

        arts = tmp_path / "artifacts"
        arts.mkdir()
        ctx  = self._MockRunContext(
            cfg={
                "map_file":   str(tmp_map_clean),
                "lds_file":   str(tmp_lds),
                "asil_level": "D",
            },
            artifacts=arts,
        )
        skill  = UC44SemanticConflictSkill(run_context=ctx, gca_invoker=None)
        result = skill.run()
        assert result["status"] == "pass"
        assert result["has_overlap"] is False

    def test_gate_decision_json_content(
        self, tmp_path: Path, tmp_map_overlap: Path, tmp_lds: Path
    ) -> None:
        """asil_gate_decision.json must record HARD_BLOCK for ASIL-D overlap."""
        from skills.automotive.uc4_4_skill import UC44SemanticConflictSkill

        arts = tmp_path / "artifacts"
        arts.mkdir()
        ctx  = self._MockRunContext(
            cfg={
                "map_file":   str(tmp_map_overlap),
                "lds_file":   str(tmp_lds),
                "asil_level": "D",
            },
            artifacts=arts,
        )
        with pytest.raises(SemanticConflictError):
            UC44SemanticConflictSkill(run_context=ctx, gca_invoker=None).run()

        data = json.loads((arts / "asil_gate_decision.json").read_text())
        assert data["action"] == "HARD_BLOCK"
        assert data["gate"]   == "G5"
        assert data["require_safety_engineer"] is True
