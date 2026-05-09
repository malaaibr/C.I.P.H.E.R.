"""Maps skill_id strings to ISkill instances."""

from __future__ import annotations

import inspect
from typing import Optional

from core.console_logging import format_console_log, utc_timestamp

MODULE_NAME = "SkillRegistry"


class SkillRegistry:
    def __init__(self) -> None:
        self._registry: dict = {}

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def register(self, skill_id: str, skill) -> None:
        self._trace(f"Registering skill '{skill_id}'.")
        self._registry[skill_id] = skill

    def resolve(self, skill_id: str) -> Optional[object]:
        skill = self._registry.get(skill_id)
        if skill is None:
            self._trace(f"No skill found for id='{skill_id}'.", level="WARN")
        return skill

    @classmethod
    def build_default(cls, orchestrator) -> "SkillRegistry":
        """@brief Build registry pre-wired with all DevNex skills."""
        from skills.lld_gen_skill     import LLDGenSkill
        from skills.code_link_skill   import CodeLinkSkill
        from skills.trace_report_skill import TraceReportSkill
        from skills.test_gen_skill    import TestGenSkill
        from skills.full_trace_skill  import FullTraceSkill

        reg = cls()
        reg.register("lld_gen",    LLDGenSkill(orchestrator))
        reg.register("code_link",  CodeLinkSkill(orchestrator))
        reg.register("trace_report", TraceReportSkill(orchestrator))
        reg.register("test_gen",   TestGenSkill(orchestrator))
        reg.register("full_trace", FullTraceSkill(orchestrator))
        return reg
