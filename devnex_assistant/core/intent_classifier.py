"""Rule-based intent classifier: rawInput → ParsedIntent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Dict

from core.console_logging import format_console_log, utc_timestamp
import inspect

MODULE_NAME = "IntentClassifier"


@dataclass
class ParsedIntent:
    intent_type:  str
    vcycle_stage: Optional[str]
    skill_id:     str
    entities:     Dict[str, str] = field(default_factory=dict)
    confidence:   float = 1.0


_RULES = [
    (r"^S1N1$",                         "RUN_STAGE", "S1N1",  "lld_gen"),
    (r"^S1N[23]$",                       "RUN_STAGE", "S1N2",  "lld_gen"),
    (r"^S1N4$",                          "RUN_STAGE", "S1N4",  "lld_gen"),
    (r"^S2N1$",                          "RUN_STAGE", "S2N1",  "code_link"),
    (r"^S2N2$",                          "RUN_STAGE", "S2N2",  "code_link"),
    (r"^S2",                             "RUN_STAGE", "S2N1",  "code_link"),
    (r"^S3",                             "RUN_STAGE", "S3N1",  "trace_report"),
    (r"^S4",                             "RUN_STAGE", "S4N1",  "trace_report"),
    (r"^S5",                             "RUN_STAGE", "S5N1",  "trace_report"),
    (r"^S6",                             "RUN_STAGE", "S6N1",  "test_gen"),
    (r"^S7",                             "RUN_STAGE", "S7N1",  "test_gen"),
    (r"^S8",                             "RUN_STAGE", "S8N1",  "test_gen"),
    (r"^S9",                             "RUN_STAGE", "S9N1",  "full_trace"),
    (r"generate\s+lld|lld\s+gen",        "RUN_STAGE", "S1N1",  "lld_gen"),
    (r"explain\s+(\w+)",                 "EXPLAIN",   None,    "explain"),
    (r"write\s+test|gen(?:erate)?\s*test", "RUN_STAGE", "S6N1", "test_gen"),
    (r"trace|traceability\s+matrix",     "RUN_STAGE", "S9N1",  "full_trace"),
    (r"sync\s+code|code.*lld",           "RUN_STAGE", "S2N1",  "code_link"),
    (r"link\s+code",                     "RUN_STAGE", "S2N1",  "code_link"),
    (r"run\s+all|full\s+workflow",       "RUN_ALL",   None,    "full_workflow"),
    (r"status|where\s+am\s+i|progress",  "STATUS",    None,    "status"),
]


class IntentClassifier:
    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def classify(self, raw_input: str, context=None) -> ParsedIntent:
        self._trace(f"Classifying intent for input: '{raw_input[:60]}'.")
        text = raw_input.strip()
        for pattern, intent_type, stage, skill_id in _RULES:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities: Dict[str, str] = {}
                if intent_type == "EXPLAIN" and match.lastindex:
                    entities["target"] = match.group(1)
                if context and hasattr(context, "config"):
                    entities["swc_name"] = context.config.get("SWC_name", "")
                intent = ParsedIntent(
                    intent_type=intent_type,
                    vcycle_stage=stage,
                    skill_id=skill_id,
                    entities=entities,
                    confidence=1.0,
                )
                self._trace(f"Matched rule → intent_type='{intent_type}', skill='{skill_id}'.")
                return intent

        self._trace("No rule matched — falling back to FREE_FORM.", level="WARN")
        return ParsedIntent(
            intent_type="FREE_FORM",
            vcycle_stage=None,
            skill_id="free_form",
            entities={"prompt": text},
            confidence=0.5,
        )
