"""free_form_skill.py — F-004 gap fix.

Handles FREE_FORM intents: passes the raw user prompt directly to GCA
with project context injected, and returns the response.
"""
from __future__ import annotations


class FreeFormSkill:
    """Skill for FREE_FORM intents — arbitrary developer Q&A."""

    def __init__(self, orchestrator) -> None:
        self._orch = orchestrator

    def run(self, prompt: str) -> str:
        """
        Forward *prompt* to GCA with SWC project context prepended.

        Returns the raw GCA response string.
        """
        swc = self._orch.config.get("SWC_name", "")
        workspace = self._orch.config.get("workspace_path", ".")
        context_header = (
            f"You are CIPHER DevNex, an AI assistant for automotive embedded "
            f"software development (ISO 26262 / ASPICE / MISRA-C).\n"
            f"Current project: SWC='{swc}', workspace='{workspace}'.\n\n"
        )
        full_prompt = context_header + prompt
        result = self._orch.gca_invoker.invoke_prompt(full_prompt, [])
        if not result.is_response_valid:
            return "[FreeFormSkill] GCA returned no valid response."
        return result.raw_response
