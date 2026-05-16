"""explain_skill.py — F-004 gap fix.

Handles EXPLAIN intents: looks up a concept or entity from config / artifacts
and returns a plain-language description via GCA.
"""
from __future__ import annotations

from pathlib import Path


class ExplainSkill:
    """Skill for EXPLAIN intents — 'explain <term>'."""

    def __init__(self, orchestrator) -> None:
        self._orch = orchestrator

    def run(self, target: str) -> str:
        """
        Invoke GCA to explain *target* in the context of the current SWC project.

        Returns the explanation string.
        """
        swc = self._orch.config.get("SWC_name", "the current SWC")
        prompt = (
            f"You are a senior embedded-software engineer.\n"
            f"Explain the following concept or entity in the context of "
            f"automotive embedded development and the SWC '{swc}':\n\n"
            f"  {target}\n\n"
            "Provide a concise (2-4 paragraph) technical explanation suitable for "
            "a developer familiar with AUTOSAR and ISO 26262."
        )
        result = self._orch.gca_invoker.invoke_prompt(prompt, [])
        if not result.is_response_valid:
            return f"[ExplainSkill] GCA returned no valid response for '{target}'."
        return result.raw_response
