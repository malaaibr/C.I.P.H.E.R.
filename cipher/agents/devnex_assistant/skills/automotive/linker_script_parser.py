"""linker_script_parser.py  —  UC 4.2 / UC 4.4 shared module."""
from __future__ import annotations
import json, re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final


_REGION_RE = re.compile(
    r"^\s*(?P<name>\w+)\s*"
    r"(?:\((?P<attrs>[rwx!]+)\))?\s*:\s*"
    r"ORIGIN\s*=\s*(?P<origin>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"LENGTH\s*=\s*(?P<length>0x[0-9a-fA-F]+|\d+[KkMm]?)",
    re.IGNORECASE,
)
_PLACEMENT_RE = re.compile(r">\s*(?P<region>\w+)", re.IGNORECASE)


def _parse_size(raw):
    raw = raw.strip()
    mul = {"K": 1024, "k": 1024, "M": 1048576, "m": 1048576}
    if raw and raw[-1] in mul:
        return int(raw[:-1]) * mul[raw[-1]]
    if raw.lower().startswith("0x"):
        return int(raw, 16)
    return int(raw)


def _strip_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _parse_memory_block(text):
    regions = []
    found_kw = False
    found_open = False
    depth = 0
    for line in text.splitlines():
        s = line.strip()
        if not found_kw:
            if re.match(r"^MEMORY(\s*\{.*)?$", s, re.IGNORECASE):
                found_kw = True
                if "{" in s:
                    found_open = True
                    depth = s.count("{") - s.count("}")
            continue
        if not found_open:
            if "{" in s:
                found_open = True
                depth = s.count("{") - s.count("}")
            continue
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            break
        m = _REGION_RE.match(line)
        if m is None:
            continue
        raw_or = m.group("origin")
        origin = int(raw_or, 16) if "0x" in raw_or.lower() else int(raw_or)
        length = _parse_size(m.group("length"))
        attrs = (m.group("attrs") or "").lower()
        regions.append(MemoryRegion(
            name=m.group("name"),
            origin=origin,
            length=length,
            end=origin + length,
            attrs=attrs,
            is_ram="w" in attrs,
        ))
    return regions


def _parse_sections_block(text):
    placements = []
    in_sec = False
    cur_sec = None
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^\s*SECTIONS\s*\{?", s, re.IGNORECASE) and not in_sec:
            in_sec = True
            continue
        if not in_sec:
            continue
        sec_start = re.match(r"^\s*([\.\w]+)\s*[:(]", s)
        if sec_start and not s.startswith(">"):
            cur_sec = sec_start.group(1)
        pm = _PLACEMENT_RE.search(s)
        if pm and cur_sec:
            placements.append(SectionPlacement(
                section_name=cur_sec,
                region_name=pm.group("region"),
            ))
    return placements


@dataclass
class MemoryRegion:
    name:   str
    origin: int
    length: int
    end:    int
    attrs:  str
    is_ram: bool


@dataclass
class SectionPlacement:
    section_name: str
    region_name:  str


@dataclass
class LinkerLayout:
    source_file: str
    regions:     list = field(default_factory=list)
    placements:  list = field(default_factory=list)

    @property
    def ram_regions(self):
        return [r for r in self.regions if r.is_ram]


class LinkerScriptParser:
    """Parse GNU LD linker script. Handles MEMORY on separate line from {."""

    def parse(self, ld_path):
        if not ld_path.exists():
            raise FileNotFoundError(f"Linker script not found: {ld_path}")
        raw = _strip_comments(ld_path.read_text(encoding="utf-8", errors="replace"))
        layout = LinkerLayout(source_file=str(ld_path.resolve()))
        layout.regions = _parse_memory_block(raw)
        layout.placements = _parse_sections_block(raw)
        return layout

    def write_json(self, layout, out_path):
        def _ser(r):
            d = asdict(r)
            d["origin_hex"] = f"0x{r.origin:08X}"
            d["end_hex"] = f"0x{r.end:08X}"
            return d
        payload = {
            "source_file": layout.source_file,
            "regions": [_ser(r) for r in layout.regions],
            "ram_regions": [_ser(r) for r in layout.ram_regions],
            "placements": [asdict(p) for p in layout.placements],
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
