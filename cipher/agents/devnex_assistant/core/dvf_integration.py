"""
DVF integration helper — opt-in wiring for orchestrator nodes.

Existing DevNex node methods (S1N1.execute etc.) call the LLM Gateway directly.
This helper wraps that call in the Draft-Verify-Finalize loop so each
LLM-touching node can become citation-aware with a single line change:

    from cipher.agents.devnex_assistant.core.dvf_integration import run_with_dvf

    crc, reports = run_with_dvf(
        invoke_fn=self._invoke_llm,
        prompt=prompt,
        attached_files=files,
        config=self._config,
        resolved_paths=self._resolved_paths,
        node_id="S1N1",
    )

Nodes that aren't ready for CAP yet keep calling the LLM directly — the
loop is purely additive.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from cipher.agents.devnex_assistant.core.dvf_loop import (
    DVFLoop,
    build_context_manifest,
)
from cipher.core.schemas.crc import CRCChain
from cipher.core.schemas.issue_report import IssueReport

logger = logging.getLogger(__name__)


def run_with_dvf(
    invoke_fn: Callable[[str, list[str], str], Any],
    prompt: str,
    attached_files: list[str],
    config: dict[str, str],
    resolved_paths: dict[str, Path],
    node_id: str,
    max_revisions: int | None = None,
    domain_pack: str | None = None,
) -> tuple[CRCChain, list[IssueReport]]:
    """Run an LLM call through the full DVF loop.

    Returns the validated CRC plus the chain of IssueReports produced during
    REVISE iterations. If R_max is exceeded the loop escalates to HITL and
    returns the last (still-invalid) CRC alongside the reports — callers
    should inspect `reports[-1].is_pass` before persisting.
    """
    pack = domain_pack or config.get("domain_pack") or "iso26262_asil_b"
    revisions = max_revisions if max_revisions is not None else 3

    manifest = build_context_manifest(config=config, resolved_paths=resolved_paths, task_id=node_id)

    loop = DVFLoop(
        invoke_fn=invoke_fn,
        manifest=manifest,
        max_revisions=revisions,
        domain_pack=pack,
    )
    crc, reports = loop.run(prompt=prompt, attached_files=attached_files, node_id=node_id)
    logger.info(
        "DVF[%s] state=%s revisions=%d violations_last=%d",
        node_id, loop.state, loop.revision_count,
        reports[-1].violation_count if reports else 0,
    )
    return crc, reports
