"""Tests for enhanced AgentCard with trust tiers."""

from cipher.core.schemas.agent_card import AgentCard, SkillDescriptor, TrustTier


class TestTrustTier:
    def test_tier_values(self):
        assert TrustTier.T0 == "T0"
        assert TrustTier.T1 == "T1"
        assert TrustTier.T2 == "T2"


class TestAgentCard:
    def test_default_trust_tier(self):
        card = AgentCard(
            agent_id="AGT-001",
            name="DevNex",
            description="V-cycle SDLC automation",
            url="http://localhost:7001",
        )
        assert card.trust_tier == TrustTier.T1

    def test_explicit_trust_tier(self):
        card = AgentCard(
            agent_id="AGT-000",
            name="Orchestrator",
            description="Runtime prompt contract assembly",
            url="http://localhost:8000",
            trust_tier=TrustTier.T0,
        )
        assert card.trust_tier == TrustTier.T0


class TestSkillDescriptorEnhancements:
    def test_asil_levels(self):
        skill = SkillDescriptor(
            skill_id="vcycle_s1n1",
            name="LLD Generation",
            description="Generate LLD from source",
            asil_levels=["A", "B", "C", "D"],
            aspice_process="SWE.3",
        )
        assert skill.asil_levels == ["A", "B", "C", "D"]
        assert skill.aspice_process == "SWE.3"

    def test_defaults_empty(self):
        skill = SkillDescriptor(
            skill_id="test",
            name="Test",
            description="Test skill",
        )
        assert skill.asil_levels == []
        assert skill.aspice_process == ""
