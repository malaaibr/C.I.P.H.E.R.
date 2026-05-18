"""
Runtime Prompt Contract Assembly (E-013, HLD R3.0 §7).

The orchestrator no longer pastes a static prompt — it assembles a Contract
from four sources at call-time:

  1. SKILL.md card                   (from SkillLoader.activate)
  2. ContextManifest evidence rows   (from MKF / config-resolved paths)
  3. Domain pack policy fragments    (allowed kinds, ASIL, phase)
  4. Trust-tier + budget envelope    (from AgentCard + BudgetEnforcer)

The result is a `PromptContract` that the LLM Gateway can hash for cache
keys and that the validator can pin to a specific CRC.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptContract:
    """One assembled prompt with provenance baked in."""
    contract_id: str
    skill_id: str
    node_id: str
    target_asil: str
    domain_pack: str
    prompt_text: str
    evidence_uris: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)

    def cache_key(self) -> str:
        h = hashlib.sha256(self.prompt_text.encode("utf-8")).hexdigest()[:16]
        return f"{self.skill_id}:{self.node_id}:{self.target_asil}:{h}"


def assemble_contract(
    skill_id: str,
    node_id: str,
    user_intent: str,
    *,
    skill_card_md: str = "",
    evidence_uris: list[str] | None = None,
    target_asil: str = "QM",
    domain_pack: str = "iso26262_asil_b",
    max_revisions: int = 3,
    budget_tokens: int | None = None,
) -> PromptContract:
    """Assemble a `PromptContract` from its sources.

    `user_intent` is the human-supplied task description; everything else is
    runtime context that should not leak into the SKILL.md card itself.
    """
    parts: list[str] = []
    if skill_card_md.strip():
        parts.append("## SKILL CARD\n" + skill_card_md.strip())
    parts.append("## TASK INTENT\n" + user_intent.strip())

    evidence_uris = evidence_uris or []
    if evidence_uris:
        parts.append("## EVIDENCE (allowed citation URIs)\n" + "\n".join(f"- {u}" for u in evidence_uris))

    parts.append(
        "## CONSTRAINTS\n"
        f"- target_asil: {target_asil}\n"
        f"- domain_pack: {domain_pack}\n"
        f"- max_revisions: {max_revisions}\n"
        f"- output_format: CRC JSON (cipher.cap.crc.v1) — every step must cite ≥1 URI from EVIDENCE.\n"
    )

    prompt_text = "\n\n".join(parts) + "\n"
    contract = PromptContract(
        contract_id=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:24],
        skill_id=skill_id,
        node_id=node_id,
        target_asil=target_asil,
        domain_pack=domain_pack,
        prompt_text=prompt_text,
        evidence_uris=evidence_uris,
        constraints={
            "max_revisions": max_revisions,
            "budget_tokens": budget_tokens,
        },
    )
    return contract
