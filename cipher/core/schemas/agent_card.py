"""AgentCard — A2A agent identity and capability advertisement."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDescriptor(BaseModel):
    """A single skill an agent can perform."""

    skill_id: str
    name: str
    description: str
    supported_task_classes: list[str] = Field(default_factory=list)
    v_cycle_stages: list[str] = Field(default_factory=list)


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
    skills: list[SkillDescriptor] = Field(default_factory=lambda: [])
    supported_protocols: list[str] = Field(default_factory=lambda: ["a2a/v1"])
    metadata: dict[str, str] = Field(default_factory=dict)
