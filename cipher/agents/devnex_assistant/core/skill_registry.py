"""Maps skill_id strings to ISkill instances.

F-004 fix: 'explain' and 'free_form' skills are now registered in build_default()
so any IntentClassifier result can be dispatched without a WARN.
"""

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
        """Build registry pre-wired with all DevNex skills (V-cycle + UC skills)."""
        from skills.lld_gen_skill      import LLDGenSkill
        from skills.code_link_skill    import CodeLinkSkill
        from skills.trace_report_skill import TraceReportSkill
        from skills.test_gen_skill     import TestGenSkill
        from skills.full_trace_skill   import FullTraceSkill
        # F-004 additions
        from skills.explain_skill      import ExplainSkill
        from skills.free_form_skill    import FreeFormSkill
        # UC 3.1 / UC 4.1 Sprint 1
        from skills.automotive.asil_review_skill   import AsilReviewSkill
        from skills.automotive.standards_qa_skill  import StandardsQASkill

        reg = cls()
        reg.register("lld_gen",      LLDGenSkill(orchestrator))
        reg.register("code_link",    CodeLinkSkill(orchestrator))
        reg.register("trace_report", TraceReportSkill(orchestrator))
        reg.register("test_gen",     TestGenSkill(orchestrator))
        reg.register("full_trace",   FullTraceSkill(orchestrator))
        # F-004
        reg.register("explain",      ExplainSkill(orchestrator))
        reg.register("free_form",    FreeFormSkill(orchestrator))
        # Sprint 1 UCs
        reg.register("asil_review",  AsilReviewSkill(orchestrator))
        reg.register("standards_qa", StandardsQASkill(orchestrator))
        return reg
