"""Sprint 4-5 smoke tests — prompt contract, skill loader stages, memory/research, packs."""

from __future__ import annotations

from pathlib import Path

import yaml

from cipher.are.prompt_contract import assemble_contract
from cipher.are.skill_loader.loader import SkillLoader, SkillDescriptor
from cipher.agents.memory_agent.agent import MemoryAgent, InMemoryMkf
from cipher.agents.research.agent import ResearchAgent


# ── E-013 PromptContract ──────────────────────────────────────────────────────

def test_prompt_contract_assembles_and_hashes():
    c = assemble_contract(
        skill_id="vcycle_s1n1",
        node_id="S1N1",
        user_intent="Generate LLD for SWC Dio",
        skill_card_md="## Purpose\nGenerate LLD CSV.",
        evidence_uris=["mkf://DLT.c", "mkf://DLT.h"],
        target_asil="ASIL-B",
        domain_pack="iso26262_asil_b",
    )
    assert c.contract_id
    assert "TASK INTENT" in c.prompt_text
    assert "EVIDENCE" in c.prompt_text
    assert c.target_asil == "ASIL-B"
    key = c.cache_key()
    assert "vcycle_s1n1" in key and "S1N1" in key


# ── E-012 SkillLoader 3-stage ────────────────────────────────────────────────

class _DummySkill:
    skill_id = "dummy_v1"
    async def execute(self, task):  # pragma: no cover - shape only
        return None


def test_skill_loader_discover_activate_resolve(tmp_path: Path):
    loader = SkillLoader(card_root=tmp_path)
    desc = SkillDescriptor(skill_id="dummy_v1", name="Dummy", asil="ASIL-B", phases=["SWE.3"])
    loader.register(_DummySkill(), desc)

    found = loader.discover(asil="ASIL-B", phase="SWE.3")
    assert any(d.skill_id == "dummy_v1" for d in found)

    # No card on disk → empty markdown, but bundle still produced.
    bundle = loader.activate("dummy_v1")
    assert bundle is not None
    assert bundle.descriptor.skill_id == "dummy_v1"
    assert bundle.card_markdown == ""

    # Add a card and re-activate (cached, so reset).
    loader._activations.clear()
    (tmp_path / "dummy_v1.SKILL.md").write_text(
        "# Dummy\n\n## Evidence\n- mkf://foo.c\n- mkf://foo.h\n",
        encoding="utf-8",
    )
    bundle = loader.activate("dummy_v1")
    assert bundle is not None
    assert "mkf://foo.c" in bundle.evidence_requirements

    assert loader.resolve("dummy_v1") is not None


# ── E-014 Memory + Research agents ───────────────────────────────────────────

def test_memory_agent_detects_gaps():
    mkf = InMemoryMkf({"mkf://known.c"})
    agent = MemoryAgent(mkf=mkf)
    report = agent.check("S1N1", ["mkf://known.c", "mkf://missing.h"])
    assert "mkf://known.c" in report.resolved
    assert "mkf://missing.h" in report.gaps
    assert report.has_gaps is True


def test_research_agent_proposes_from_workspace(tmp_path: Path):
    (tmp_path / "missing.h").write_text("/* stub */", encoding="utf-8")
    mkf = InMemoryMkf()
    mem = MemoryAgent(mkf=mkf)
    report = mem.check("S1N1", ["mkf://missing.h"])
    research = ResearchAgent(workspace_path=tmp_path)
    proposals = research.propose(report)
    assert len(proposals) == 1
    assert proposals[0].candidates, "Expected workspace match for missing.h"
    assert proposals[0].confidence > 0


# ── Domain packs ─────────────────────────────────────────────────────────────

DOMAIN_PACK_ROOT = Path(__file__).resolve().parents[2] / "cipher" / "gcl" / "domain_packs"


def test_new_domain_packs_load():
    for pack in ("iso26262_asil_c", "iso26262_asil_d", "aspice_l3", "misra_c_2012"):
        meta = yaml.safe_load((DOMAIN_PACK_ROOT / pack / "pack.yaml").read_text(encoding="utf-8"))
        assert meta["name"]
        assert (DOMAIN_PACK_ROOT / pack / "schemas" / "permitted_types.json").exists()
        assert (DOMAIN_PACK_ROOT / pack / "schemas" / "phase_kinds.json").exists()
