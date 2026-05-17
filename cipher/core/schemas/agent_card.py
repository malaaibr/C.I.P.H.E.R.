"""AgentCard — A2A agent identity and capability advertisement."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TrustTier(StrEnum):
    """Agent trust classification per CIPHER HLD §9."""

    T0 = "T0"  # Always-on, elevated scoped permissions
    T1 = "T1"  # Advisory, read-only outputs until promoted
    T2 = "T2"  # Can mutate artifacts, requires policy check + HITL for irreversible


class SkillDescriptor(BaseModel):
    """A single skill an agent can perform."""

    skill_id: str
    name: str
    description: str
    supported_task_classes: list[str] = Field(default_factory=list)
    v_cycle_stages: list[str] = Field(default_factory=list)
    asil_levels: list[str] = Field(
        default_factory=list,
        description="Supported ASIL levels, e.g. ['A', 'B', 'C', 'D']",
    )
    aspice_process: str = Field(
        default="", description="ASPICE process reference, e.g. SWE.3"
    )


class AgentCard(BaseModel):
    """
    Agent identity card registered with the ARE A2A server.

    Based on the Google A2A AgentCard spec, adapted for CIPHER.
    """

    agent_id: str
    name: str
    description: str
    version: str = "0.1.0"
    url: str
    trust_tier: TrustTier = Field(
        default=TrustTier.T1, description="Agent trust classification"
    )
    skills: list[SkillDescriptor] = Field(default_factory=lambda: [])
    supported_protocols: list[str] = Field(default_factory=lambda: ["a2a/v1"])
    metadata: dict[str, str] = Field(default_factory=dict)
