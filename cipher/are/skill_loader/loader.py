"""SkillLoader — 3-stage progressive disclosure (E-012).

Stages, per HLD R3.0 §6:

  Stage 1 — Discovery
    `discover()` returns lightweight `SkillDescriptor` rows (id, name, asil,
    phases, summary). Cheap. Used for catalog UIs and routing.

  Stage 2 — Activation
    `activate(skill_id)` loads the SKILL.md card (full prompt, evidence
    requirements, validator hints). Returns the descriptor + activation
    bundle. Cached per process.

  Stage 3 — Execution
    `resolve(skill_id)` returns the executable `Skill` instance, ready for
    `await skill.execute(task)`. Falls back to direct registry lookup when no
    activation context exists (preserves Sprint 1 behavior).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cipher.core.schemas.task_contract import TaskContract, TaskResult

log = logging.getLogger(__name__)


class Skill(Protocol):
    @property
    def skill_id(self) -> str: ...
    async def execute(self, task: TaskContract) -> TaskResult: ...


@dataclass
class SkillDescriptor:
    """Lightweight metadata for Stage 1 — Discovery."""
    skill_id: str
    name: str = ""
    asil: str = "QM"
    phases: list[str] = field(default_factory=list)
    summary: str = ""
    card_path: str | None = None


@dataclass
class ActivationBundle:
    """Stage 2 — Activation result."""
    descriptor: SkillDescriptor
    card_markdown: str = ""
    evidence_requirements: list[str] = field(default_factory=list)


class SkillLoader:
    """Registry + 3-stage progressive disclosure."""

    def __init__(self, card_root: Path | None = None) -> None:
        self._registry: dict[str, Skill] = {}
        self._descriptors: dict[str, SkillDescriptor] = {}
        self._activations: dict[str, ActivationBundle] = {}
        self._card_root = card_root or (
            Path(__file__).resolve().parents[3] / "agents" / "devnex_assistant"
            / "skills" / "definitions"
        )

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, skill: Skill, descriptor: SkillDescriptor | None = None) -> None:
        self._registry[skill.skill_id] = skill
        if descriptor is None:
            descriptor = SkillDescriptor(skill_id=skill.skill_id, name=skill.skill_id)
        self._descriptors[skill.skill_id] = descriptor

    # ── Stage 1: Discovery ────────────────────────────────────────────────

    def discover(self, asil: str | None = None, phase: str | None = None) -> list[SkillDescriptor]:
        results = list(self._descriptors.values())
        if asil:
            results = [d for d in results if d.asil == asil or d.asil == "QM"]
        if phase:
            results = [d for d in results if phase in d.phases or not d.phases]
        return results

    # ── Stage 2: Activation ───────────────────────────────────────────────

    def activate(self, skill_id: str) -> ActivationBundle | None:
        if skill_id in self._activations:
            return self._activations[skill_id]
        desc = self._descriptors.get(skill_id)
        if desc is None:
            return None
        card_md = ""
        card_path: Path | None = None
        if desc.card_path:
            card_path = Path(desc.card_path)
        else:
            candidate = self._card_root / f"{skill_id.lower()}.SKILL.md"
            if candidate.exists():
                card_path = candidate
        if card_path and card_path.exists():
            try:
                card_md = card_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                log.warning("Failed to read SKILL.md for %s: %s", skill_id, e)
        bundle = ActivationBundle(
            descriptor=desc,
            card_markdown=card_md,
            evidence_requirements=_parse_evidence_section(card_md),
        )
        self._activations[skill_id] = bundle
        return bundle

    # ── Stage 3: Execution ────────────────────────────────────────────────

    def resolve(self, skill_id: str) -> Skill | None:
        return self._registry.get(skill_id)

    def list_skills(self) -> list[str]:
        return list(self._registry.keys())


def _parse_evidence_section(card_md: str) -> list[str]:
    """Pull bullet lines from a `## Evidence` (or `## Inputs`) section."""
    if not card_md:
        return []
    lines = card_md.splitlines()
    out: list[str] = []
    in_section = False
    for line in lines:
        s = line.strip()
        if s.lower().startswith("## evidence") or s.lower().startswith("## inputs"):
            in_section = True
            continue
        if in_section:
            if s.startswith("## "):
                break
            if s.startswith(("- ", "* ")):
                out.append(s[2:].strip())
    return out


_loader_instance: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SkillLoader()
    return _loader_instance
