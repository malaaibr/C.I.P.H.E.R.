"""DevNexOrchestrator — coordinates V-cycle stage execution.

Sprint 0 gap fixes applied:
  F-001 Artifact filenames aligned with trace_loader CSV_MAP expectations
        S3N1 -> LLD_Code_Trace_Matrix.csv
        S4N1 -> HLD_LLD_Trace_Matrix.csv  (JSON kept as HLD_LLD_Links.json)
        S5N1 -> Full_Downstream_Trace.csv
  F-002 _invoke_with_retry() wraps every GCA call, reads max_gca_retries from config
  F-005 ArtifactMissingError raised in S1N1 / S1N4 when required files absent
  F-006 S1N4 now loads categorize_reqs_v1.md prompt template
  F-007 S3N1 / S4N1 now load lld_code_trace_v1.md / hld_lld_links_v1.md templates
  F-008 run_workflow() bridges WorkflowEngine so AF.json graphs can be executed
  F-009 _enforce_critical_globs() validates workspace files from ruleset.yaml
  F-010 run_context.validate_workspace() called before S1N1
"""

from __future__ import annotations

import inspect
import json
import time
import yaml
from pathlib import Path
from typing import Callable, Any
from dataclasses import dataclass, field

from core.console_logging import format_console_log, utc_timestamp
from core.errors import (
    WorkflowAbortedError, NodeExecutionError,
    ConfigValidationError, ArtifactMissingError,
)
from core.run_context import DevNexRunContext
from persistence.state_store import StateStore
from persistence.config_store import ConfigStore

MODULE_NAME = "DevNexOrchestrator"
LLD_INPUT_FILE_KEYS = [
    "SWC_name_C",
    "SWC_name_H",
    "G_SWDD_TEMP",
    "SWC_name_TEMP_LLD",
    "SWC_name_HLD",
    "lds_file",
    "map_file",
]
LLD_EMBEDDED_CONTEXT_KEYS = [
    "SWC_name_C",
    "SWC_name_H",
    "G_SWDD_TEMP",
    "SWC_name_TEMP_LLD",
    "SWC_name_HLD",
]
_RULESET_PATH = Path(__file__).parent.parent / "configs" / "ruleset.yaml"


@dataclass
class NodeResult:
    """
    @brief Result contract returned by each V-cycle node.
    """
    node_id:   str
    status:    str
    output:    str
    artifacts: list[str] = field(default_factory=list)
    errors:    list[str] = field(default_factory=list)


# ── Sprint 8: DVF helper module-level utilities ─────────────────────────────

def path_context_with_content(path_config: dict, content_sections: list[str]) -> dict:
    """
    Build a template render context that includes the file-content tail used
    by v2 (citation-aware) prompts. Keeps `_render_prompt` calls uniform across
    nodes that want to opt into DVF.
    """
    ctx = dict(path_config)
    ctx["__attached_content__"] = "\n\n## Attached Input Files\n" + "".join(content_sections)
    return ctx


def _render_crc_as_json(crc, swc: str) -> str:  # noqa: ARG001 — swc may be used by custom renderers
    """
    Default DVF artifact renderer — dumps the validated CRC as pretty JSON.
    Nodes whose artifact is structured (CSV, annotated source, etc.) should
    pass a tailored `render_artifact` callable into `_maybe_invoke_via_dvf`.
    """
    import json as _json
    try:
        return _json.dumps(crc.model_dump(mode="json"), indent=2)
    except Exception:
        return repr(crc)


class DevNexOrchestrator:
    """
    @brief Coordinates V-cycle node execution for DevNex Assistant.

    Stage/Node mapping:
      S1N1 -> lld_gen_skill.run_s1n1()
      S1N2 -> human review (upload to req mgmt)
      S1N3 -> human review (extract IDs)
      S1N4 -> lld_gen_skill.run_s1n4()
      S2N1 -> code_link_skill.run_s2n1()
      S2N2 -> human review (inspect annotated code)
      S3N1 -> trace_report_skill.run_s3()
      S4N1 -> trace_report_skill.run_s4()
      S5N1 -> trace_report_skill.run_s5()
      S6N1 -> test_gen_skill.run_s6() + human review (.TST wait)
      S7N1 -> test_gen_skill.run_s7()
      S8N1 -> test_gen_skill.run_s8()
      S9N1 -> full_trace_skill.run_s9()
    """

    def __init__(
        self,
        run_context: DevNexRunContext,
        on_log:             Callable[[str, str], None] | None = None,
        on_node_started:    Callable[[str], None] | None = None,
        on_node_complete:   Callable[[NodeResult], None] | None = None,
        on_human_review:    Callable[[str, str], bool] | None = None,
        progress_callback:  Callable[[int, str], None] | None = None,
    ) -> None:
        self.run_context       = run_context
        self.on_log            = on_log or (lambda *_: None)
        self.on_node_started   = on_node_started or (lambda _: None)
        self.on_node_complete  = on_node_complete or (lambda _: None)
        self.on_human_review   = on_human_review or self._default_human_review
        self.progress_callback = progress_callback or (lambda *_: None)

        self.state_store  = StateStore()
        self.config_store = ConfigStore()
        self.config       = self.config_store.load()

        self._gca_invoker = None
        self._ruleset: dict | None = None

        self._artifacts_dir = run_context.get_artifacts_path()
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    # ── Lazy GCA invoker ──────────────────────────────────────────────────

    @property
    def gca_invoker(self):
        if self._gca_invoker is None:
            from gca.vscode_invoker import DevNexGCAInvoker
            self._gca_invoker = DevNexGCAInvoker(Path(self.config.get("workspace_path", ".")))
        return self._gca_invoker

    # ── Logging ───────────────────────────────────────────────────────────

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        line = format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller)
        print(line)
        self.on_log(message, level)

    # ── F-002: GCA retry wrapper ──────────────────────────────────────────

    def _invoke_with_retry(self, prompt: str, files: list, node_id: str = ""):
        """
        @brief F-002 — Invoke GCA with automatic retry on invalid response.

        Reads max_gca_retries from config (default 3 per ruleset.yaml).
        Raises NodeExecutionError if all attempts fail.
        """
        max_retries = int(self.config.get("max_gca_retries", 3))
        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                result = self.gca_invoker.invoke_prompt(prompt, files)
                if result.is_response_valid:
                    return result
                self._trace(
                    f"{node_id}: GCA attempt {attempt}/{max_retries} returned invalid response.",
                    level="WARN",
                )
            except Exception as exc:
                last_exc = exc
                self._trace(
                    f"{node_id}: GCA attempt {attempt}/{max_retries} raised {exc}.",
                    level="WARN",
                )
            if attempt < max_retries:
                time.sleep(1)

        err = f"{node_id}: GCA failed after {max_retries} attempt(s)."
        if last_exc:
            err += f" Last error: {last_exc}"
        raise NodeExecutionError(err)

    # ── Sprint 8: Generic DVF opt-in helper ───────────────────────────────

    def _maybe_invoke_via_dvf(
        self,
        *,
        node_id: str,
        base_prompt: str,
        attached_files: list,
        swc: str,
        out_path: "Path",
        resolved_paths: dict | None = None,
        v2_prompt_basename: str | None = None,
        v2_template_context: dict | None = None,
        render_artifact: Callable | None = None,
    ) -> "NodeResult | None":
        """
        @brief Generic DVF opt-in for any LLM-touching node.

        Returns a NodeResult when DVF handled the work; returns None so the
        caller can fall through to its legacy direct-LLM path.

        Opt-in rules (all must hold):
          - config["enable_dvf"] is truthy
          - v2_prompt_basename is provided AND the prompt file exists
          - config["dvf_nodes"] is unset, OR node_id is in that list
          - DVF import + run succeeds without exception

        On any failure during the DVF path the helper logs WARN and returns
        None so the node falls back to its legacy path — opt-in must never
        regress the legacy behaviour.
        """
        if not self.config.get("enable_dvf"):
            return None
        if v2_prompt_basename is None:
            return None
        enabled_nodes = self.config.get("dvf_nodes")
        if enabled_nodes is not None and node_id not in enabled_nodes:
            return None

        try:
            from cipher.agents.devnex_assistant.core.dvf_integration import run_with_dvf
        except Exception as imp_err:
            self._trace(f"{node_id}: DVF import failed ({imp_err}); using legacy path.",
                        level="WARN")
            return None

        try:
            v2_template = self._load_prompt(v2_prompt_basename)
        except Exception as e:
            self._trace(f"{node_id}: v2 prompt '{v2_prompt_basename}' not loadable ({e}); legacy path.",
                        level="WARN")
            return None

        ctx = v2_template_context if v2_template_context is not None else dict(self.config)
        attached_tail = ctx.pop("__attached_content__", "")
        dvf_prompt = self._render_prompt(v2_template, ctx) + attached_tail

        try:
            self._trace(f"{node_id}: DVF enabled — running Draft-Verify-Finalize loop.")
            crc, reports = run_with_dvf(
                invoke_fn=self._invoke_with_retry,
                prompt=dvf_prompt,
                attached_files=attached_files,
                config=self.config,
                resolved_paths=resolved_paths or {},
                node_id=node_id,
                max_revisions=int(self.config.get("max_revisions", 3)),
                domain_pack=self.config.get("domain_pack", "iso26262_asil_b"),
            )
        except Exception as dvf_err:
            self._trace(f"{node_id}: DVF run failed ({dvf_err}); falling back to legacy path.",
                        level="WARN")
            return None

        renderer = render_artifact or _render_crc_as_json
        artifact_text = renderer(crc, swc)
        out_path.write_text(artifact_text, encoding="utf-8")

        last_pass = reports[-1].is_pass if reports else False
        self._trace(
            f"{node_id}: DVF complete — pass={last_pass} revisions={len(reports) - 1}",
            level="SUCCESS" if last_pass else "WARN",
        )
        return NodeResult(
            node_id=node_id,
            status="complete" if last_pass else "complete_with_warnings",
            output=artifact_text,
            artifacts=[str(out_path)],
            errors=[] if last_pass else
                [f"{v.violation_type}: {v.message}" for v in reports[-1].violations],
        )

    # ── F-009: critical_globs enforcement ────────────────────────────────

    def _load_ruleset(self) -> dict:
        if self._ruleset is None:
            if _RULESET_PATH.exists():
                try:
                    self._ruleset = yaml.safe_load(_RULESET_PATH.read_text(encoding="utf-8")) or {}
                except Exception as exc:
                    self._trace(f"ruleset.yaml load failed: {exc}", level="WARN")
                    self._ruleset = {}
            else:
                self._ruleset = {}
        return self._ruleset

    def _enforce_critical_globs(self) -> None:
        """
        @brief F-009 — Check that workspace contains files matching critical_globs.

        Only enforces when the workspace path is a real directory.
        Logs warnings (does not raise) for missing patterns so CI is not blocked
        on projects that legitimately omit certain file types.
        """
        ruleset = self._load_ruleset()
        globs = ruleset.get("critical_globs", [])
        if not globs:
            return
        workspace = Path(self.config.get("workspace_path", "."))
        if not workspace.is_dir():
            return
        exempt = ruleset.get("exempt_patterns", [])
        for pattern in globs:
            # removeprefix("**/") strips exactly the two-star-slash prefix as a
            # string; lstrip("**/") would mis-strip chars and turn "**/*.c" → ".c"
            glob_suffix = pattern.removeprefix("**/")
            matches = [
                p for p in workspace.rglob(glob_suffix)
                if not any(p.match(ex) for ex in exempt)
            ]
            if not matches:
                self._trace(
                    f"F-009: No files matching '{pattern}' found in workspace '{workspace}'.",
                    level="WARN",
                )

    # ── Node execution entry point ─────────────────────────────────────────

    def run_node(self, node_id: str) -> NodeResult:
        """@brief Execute a single V-cycle node by ID."""
        self._trace(f"Starting node execution: {node_id}.")
        self.on_node_started(node_id)

        node_map = {
            "S1N1": self._run_s1n1,
            "S1N2": self._run_s1n2_review,
            "S1N3": self._run_s1n3_review,
            "S1N4": self._run_s1n4,
            "S2N1": self._run_s2n1,
            "S2N2": self._run_s2n2_review,
            "S3N1": self._run_s3n1,
            "S4N1": self._run_s4n1,
            "S5N1": self._run_s5n1,
            "S6N1": self._run_s6n1,
            "S7N1": self._run_s7n1,
            "S8N1": self._run_s8n1,
            "S9N1": self._run_s9n1,
        }
        handler = node_map.get(node_id)
        if handler is None:
            raise NodeExecutionError(f"Unknown node ID: {node_id}")

        result = handler()
        self.state_store.set_node_status(node_id, result.status)
        self.on_node_complete(result)
        self._trace(f"Node {node_id} completed with status='{result.status}'.", level="SUCCESS")
        return result

    def run_all(self, progress_callback: Callable[[int, str], None] | None = None) -> list[NodeResult]:
        """@brief Execute all nodes S1N1 -> S9N1 sequentially."""
        all_nodes = [
            "S1N1", "S1N2", "S1N3", "S1N4",
            "S2N1", "S2N2",
            "S3N1", "S4N1", "S5N1",
            "S6N1", "S7N1", "S8N1", "S9N1",
        ]
        results = []
        cb = progress_callback or self.progress_callback
        for i, node_id in enumerate(all_nodes):
            pct = int((i / len(all_nodes)) * 100)
            cb(pct, f"Running {node_id}...")
            result = self.run_node(node_id)
            results.append(result)
            if result.status in ("aborted", "error"):
                self._trace(f"Full run halted at {node_id} (status={result.status}).", level="WARN")
                break
        cb(100, "V-cycle complete.")
        return results

    # ── F-008: WorkflowEngine bridge ──────────────────────────────────────

    def run_workflow(self, workflow_path: str, inputs: dict | None = None) -> str:
        """
        @brief F-008 — Execute an AF.json workflow graph via WorkflowEngine.

        Bridges the WorkflowEngine (AF.json graph executor) with the
        DevNexOrchestrator so both execution paths share the same GCA bridge
        and callbacks.

        @param workflow_path Path to an AF.json workflow definition.
        @param inputs        Template substitution variables for {{nodeId.output.port}}.
        @return Raw LLM response from the last sendPrompt node.
        """
        from core.workflow_engine import WorkflowEngine

        engine = WorkflowEngine(
            gca_bridge=self.gca_invoker,
            on_node_start=lambda nid, label: self.on_node_started(nid),
            on_node_complete=lambda nid, resp: self._trace(f"WF node '{nid}' complete."),
            on_human_review=lambda nid, data: self.on_human_review(nid, data.get("message", "")),
        )
        self._trace(f"F-008: Executing workflow '{workflow_path}'.")
        return engine.execute(workflow_path, inputs or {})

    # ── Stage implementations ──────────────────────────────────────────────

    def _run_s1n1(self) -> NodeResult:
        """@brief S1N1 — Collect inputs, build prompt, invoke GCA, write LLD CSV."""
        self._validate_config([
            "SWC_name", "G_SWDD_TEMP", "SWC_name_C", "SWC_name_H",
            "SWC_name_TEMP_LLD", "SWC_name_HLD", "lds_file", "map_file",
        ])
        # F-010: validate workspace path before any file resolution
        self.run_context.validate_workspace()
        # F-009: warn on missing critical file patterns
        self._enforce_critical_globs()

        swc = self.config["SWC_name"]
        self._trace(f"S1N1: Building LLD generation prompt for SWC '{swc}'.")

        workspace = Path(self.config.get("workspace_path", "."))
        resolved: dict[str, Path] = {
            key: self._resolve_workspace_path(self.config[key], workspace)
            for key in LLD_INPUT_FILE_KEYS
        }

        path_config = dict(self.config)
        for k, p in resolved.items():
            path_config[k] = str(p)

        prompt_template = self._load_prompt("lld_gen_v1.md")
        prompt = self._render_prompt(prompt_template, path_config)

        content_sections: list[str] = []
        for k in LLD_EMBEDDED_CONTEXT_KEYS:
            p = resolved[k]
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace")
                content_sections.append(
                    f"\n\n### FILE: {p.name}  ({p})\n```\n{text}\n```"
                )
                self._trace(f"S1N1: Embedded context file '{p.name}' ({len(text)} chars).")
            else:
                # F-005: raise instead of silently continuing with [FILE NOT FOUND]
                raise ArtifactMissingError(
                    f"S1N1: Required context file '{p}' (config key='{k}') not found. "
                    "Verify all file paths in the Config tab."
                )

        prompt += "\n\n## Attached Input Files\n" + "".join(content_sections)
        attached_files = [str(resolved[k]) for k in LLD_EMBEDDED_CONTEXT_KEYS]
        self._trace(f"S1N1: Invoking GCA (prompt={len(prompt)} chars).")

        out_path = self._artifacts_dir / f"{swc}_TEMP_LLD_updated.csv"

        # Sprint 8 — Opt-in DVF via generic helper. Returns a NodeResult when
        # DVF handled the work, None to fall through to the legacy path.
        from cipher.agents.devnex_assistant.core.dvf_loop import render_csv_from_crc
        dvf_result = self._maybe_invoke_via_dvf(
            node_id="S1N1",
            base_prompt=prompt,
            attached_files=attached_files,
            swc=swc,
            out_path=out_path,
            resolved_paths=resolved,
            v2_prompt_basename="lld_gen_v2.md",
            v2_template_context=path_context_with_content(path_config, content_sections),
            render_artifact=render_csv_from_crc,
        )
        if dvf_result is not None:
            return dvf_result

        # F-002: retry wrapper (legacy direct path)
        result = self._invoke_with_retry(prompt, attached_files, "S1N1")
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S1N1: Artifact written -> '{out_path}'.", level="SUCCESS")

        return NodeResult(
            node_id="S1N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s1n2_review(self) -> NodeResult:
        """@brief S1N2 — Human review gate: upload LLD to DOORS/ReqIF."""
        swc = self.config.get("SWC_name", "SWC")
        msg = (
            f"Upload '{swc}_TEMP_LLD_updated.csv' to your Requirements Management tool "
            f"(DOORS / ReqIF) to obtain unique IDs for each requirement.\n\n"
            f"Click Continue once unique IDs have been assigned."
        )
        self._trace("S1N2: Awaiting human review — upload to Req Mgmt tool.")
        approved = self.on_human_review("S1N2", msg)
        if not approved:
            raise WorkflowAbortedError("S1N2: User aborted at upload review gate.")
        return NodeResult(
            node_id="S1N2", status="complete",
            output="Human review approved — LLD uploaded to Req Mgmt tool.",
        )

    def _run_s1n3_review(self) -> NodeResult:
        """@brief S1N3 — Human review gate: extract updated LLD with unique IDs."""
        msg = (
            "Extract the updated LLD with new unique IDs from your Requirements Management tool.\n\n"
            "Save the file locally as '[SWC]_LLD_withIDs.csv', then click Continue."
        )
        self._trace("S1N3: Awaiting human review — extract IDs from Req Mgmt tool.")
        approved = self.on_human_review("S1N3", msg)
        if not approved:
            raise WorkflowAbortedError("S1N3: User aborted at ID extraction gate.")
        return NodeResult(
            node_id="S1N3", status="complete",
            output="Human review approved — LLD with unique IDs extracted.",
        )

    def _run_s1n4(self) -> NodeResult:
        """@brief S1N4 — Categorize LLD requirements: Functional vs Non-Functional."""
        self._validate_config(["SWC_name", "SWC_nameInspBaseLLD"])
        swc       = self.config["SWC_name"]
        insp_file = self.config["SWC_nameInspBaseLLD"]
        self._trace(f"S1N4: Categorizing requirements from '{insp_file}'.")

        # F-005: raise when input file missing (was: silently continue with empty content)
        insp_path = Path(insp_file)
        if not insp_path.exists():
            raise ArtifactMissingError(
                f"S1N4: LLD inspection file not found at '{insp_path}'. "
                "Complete S1N2/S1N3 first to produce the file."
            )
        insp_content = insp_path.read_text(encoding="utf-8")

        # F-006: load template instead of inline hardcoded prompt
        prompt_template = self._load_prompt("categorize_reqs_v1.md")
        prompt = self._render_prompt(prompt_template, {
            **self.config,
            "SWC_nameInspBaseLLD": insp_content,
        })

        # F-002: retry wrapper
        result = self._invoke_with_retry(prompt, [insp_file], "S1N4")

        out_path = self._artifacts_dir / f"{swc}_FUNC_req.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S1N4: Functional requirements written -> '{out_path}'.", level="SUCCESS")

        return NodeResult(
            node_id="S1N4", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s2n1(self) -> NodeResult:
        """@brief S2N1 — Embed LLD requirement references in source code."""
        self._validate_config(["SWC_name", "SWC_name_C"])
        swc        = self.config["SWC_name"]
        source_file = self.config["SWC_name_C"]
        func_req_file = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")

        self._trace(f"S2N1: Embedding LLD references into '{source_file}'.")
        prompt_template = self._load_prompt("code_link_v1.md")
        prompt = self._render_prompt(prompt_template, self.config)

        result = self._invoke_with_retry(prompt, [source_file, func_req_file], "S2N1")

        out_path = self._artifacts_dir / f"updated_{swc}.c"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S2N1: Annotated source written -> '{out_path}'.", level="SUCCESS")

        return NodeResult(
            node_id="S2N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s2n2_review(self) -> NodeResult:
        """@brief S2N2 — Human review: inspect LLD-annotated source code."""
        swc = self.config.get("SWC_name", "SWC")
        msg = (
            f"Review the LLD-annotated source file 'updated_{swc}.c'.\n\n"
            "Verify all requirement references are correctly placed before continuing."
        )
        self._trace("S2N2: Awaiting human review — inspect annotated source code.")
        approved = self.on_human_review("S2N2", msg)
        if not approved:
            raise WorkflowAbortedError("S2N2: User aborted at code review gate.")
        return NodeResult(
            node_id="S2N2", status="complete",
            output="Human review approved — annotated source code accepted.",
        )

    def _run_s3n1(self) -> NodeResult:
        """@brief S3N1 — Generate LLD->Code traceability report.

        F-001: Output renamed to LLD_Code_Trace_Matrix.csv to match trace_loader._CSV_MAP.
        F-007: Prompt loaded from lld_code_trace_v1.md template.
        """
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S3N1: Generating LLD -> Code traceability report.")
        source_file = str(self._artifacts_dir / f"updated_{swc}.c")
        func_req    = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")

        # F-007: template instead of inline prompt
        prompt_template = self._load_prompt("lld_code_trace_v1.md")
        prompt = self._render_prompt(prompt_template, {**self.config, "SWC_name": swc})

        result = self._invoke_with_retry(prompt, [source_file, func_req], "S3N1")

        # F-001: was LLD_Code_Trace_Report.csv — renamed to match trace_loader._CSV_MAP
        out_path = self._artifacts_dir / "LLD_Code_Trace_Matrix.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S3N1: Trace report written -> '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S3N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s4n1(self) -> NodeResult:
        """@brief S4N1 — Map LLD requirements to parent HLD items.

        F-001: JSON still written as HLD_LLD_Links.json; CSV HLD_LLD_Trace_Matrix.csv
               also written so trace_loader can consume it directly.
        F-007: Prompt loaded from hld_lld_links_v1.md template.
        """
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S4N1: Linking LLD requirements to HLD items.")
        hld_file = self.config.get("SWC_name_HLD", "")
        func_req = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")

        # F-007: template instead of inline prompt
        prompt_template = self._load_prompt("hld_lld_links_v1.md")
        prompt = self._render_prompt(prompt_template, {**self.config, "SWC_name": swc})

        result = self._invoke_with_retry(prompt, [hld_file, func_req], "S4N1")

        # Keep JSON for backward compat
        json_path = self._artifacts_dir / "HLD_LLD_Links.json"
        json_path.write_text(result.raw_response, encoding="utf-8")

        # F-001: also write CSV that trace_loader expects (HLD_LLD_Trace_Matrix.csv)
        csv_path = self._artifacts_dir / "HLD_LLD_Trace_Matrix.csv"
        try:
            links = json.loads(result.raw_response)
            if isinstance(links, list):
                rows = ["HLD_ID,LLD_ID,LINK_TYPE,HLD_TITLE,LLD_TITLE"]
                for lnk in links:
                    rows.append(
                        f"{lnk.get('hld_id','')},{lnk.get('lld_id','')},"
                        f"{lnk.get('link_type','link')},,")
                csv_path.write_text("\n".join(rows), encoding="utf-8")
        except (json.JSONDecodeError, TypeError):
            csv_path.write_text(result.raw_response, encoding="utf-8")

        self._trace(f"S4N1: HLD->LLD links written -> '{json_path}', '{csv_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S4N1", status="complete",
            output=result.raw_response, artifacts=[str(json_path), str(csv_path)],
        )

    def _run_s5n1(self) -> NodeResult:
        """@brief S5N1 — Generate full downstream Code->LLD->HLD traceability matrix.

        F-001: Output renamed to Full_Downstream_Trace.csv to match trace_loader._CSV_MAP.
        """
        self._trace("S5N1: Building full downstream traceability matrix.")
        trace_report = str(self._artifacts_dir / "LLD_Code_Trace_Matrix.csv")
        hld_links    = str(self._artifacts_dir / "HLD_LLD_Links.json")
        prompt_template = self._load_prompt("full_trace_v1.md")
        prompt = self._render_prompt(prompt_template, self.config)
        result = self._invoke_with_retry(prompt, [trace_report, hld_links], "S5N1")

        # F-001: was HLD_LLD_Code_Trace_Matrix.csv — renamed to Full_Downstream_Trace.csv
        out_path = self._artifacts_dir / "Full_Downstream_Trace.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S5N1: Full trace matrix written -> '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S5N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s6n1(self) -> NodeResult:
        """@brief S6N1 — Generate VectorCAST test artifacts + wait for .TST output."""
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S6N1: Generating VectorCAST test artifacts via GCA.")
        source_file = str(self._artifacts_dir / f"updated_{swc}.c")
        func_req    = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")

        prompt = (
            f"Generate a VectorCAST test.bat script and test environment scaffolding "
            f"for SWC '{swc}'. Include all functional requirements from the CSV.\n"
            "Output: test.bat content followed by a ---SEPARATOR--- then the test environment config."
        )
        result = self._invoke_with_retry(prompt, [source_file, func_req], "S6N1")
        bat_path = self._artifacts_dir / "test.bat"
        bat_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S6N1: test.bat written -> '{bat_path}'.")

        msg = (
            f"Run VectorCAST using the generated 'test.bat' file.\n\n"
            f"The platform will wait here until .TST files are produced.\n"
            f"Once execution is complete and .TST files are available, click Continue."
        )
        self._trace("S6N1: Waiting for VectorCAST .TST output — human review gate.")
        approved = self.on_human_review("S6N1", msg)
        if not approved:
            raise WorkflowAbortedError("S6N1: User aborted at VectorCAST wait gate.")

        return NodeResult(
            node_id="S6N1", status="complete",
            output=result.raw_response, artifacts=[str(bat_path)],
        )

    def _run_s7n1(self) -> NodeResult:
        """@brief S7N1 — Parse .TST files and generate formal Unit Test Documentation."""
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S7N1: Parsing .TST files and generating UTD.")

        tst_files = list(Path(self.config.get("workspace_path", ".")).glob("*.tst"))
        if not tst_files:
            tst_files = list(self._artifacts_dir.glob("*.tst"))
        self._trace(f"S7N1: Found {len(tst_files)} .TST file(s).")

        prompt = (
            "Parse the attached VectorCAST .TST execution results and generate "
            "a formal Unit Test Documentation (UTD) in Markdown format.\n"
            "Include: test case ID, description, inputs, expected vs actual outputs, PASS/FAIL status, coverage %."
        )
        result = self._invoke_with_retry(prompt, [str(f) for f in tst_files], "S7N1")
        out_path = self._artifacts_dir / f"{swc}_UTD.md"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S7N1: UTD written -> '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S7N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s8n1(self) -> NodeResult:
        """@brief S8N1 — Link UTD test cases to LLD requirements."""
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S8N1: Linking UTD test cases to LLD requirements.")
        utd_file = str(self._artifacts_dir / f"{swc}_UTD.md")
        func_req = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")
        prompt = (
            "Map each unit test case to its corresponding LLD functional requirement.\n"
            "Output JSON array: [{\"test_case_id\": ..., \"req_id\": ..., \"test_result\": ..., \"coverage_contribution\": ...}]"
        )
        result = self._invoke_with_retry(prompt, [utd_file, func_req], "S8N1")
        out_path = self._artifacts_dir / "UTD_LLD_Links.json"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S8N1: UTD->LLD links written -> '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S8N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s9n1(self) -> NodeResult:
        """@brief S9N1 — Consolidate full traceability matrix: HLD->LLD->Code->Test->UTD."""
        self._trace("S9N1: Building final full traceability matrix.")
        inputs = [
            str(self._artifacts_dir / "Full_Downstream_Trace.csv"),
            str(self._artifacts_dir / "UTD_LLD_Links.json"),
        ]
        prompt_template = self._load_prompt("full_trace_v1.md")
        prompt = self._render_prompt(prompt_template, self.config)
        result = self._invoke_with_retry(prompt, inputs, "S9N1")
        out_path = self._artifacts_dir / "Full_Traceability_Matrix.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S9N1: Full traceability matrix written -> '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S9N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    # ── UC 4.4 Post-Merge Semantic Check ─────────────────────────────────────

    def run_uc4_4_semantic_check(
        self,
        map_file: str | None = None,
        lds_file: str | None = None,
        asil_level: str | None = None,
    ) -> NodeResult:
        """@brief UC 4.4 — Post-merge semantic memory map overlap check."""
        from skills.automotive.uc4_4_skill import UC44SemanticConflictSkill
        from gcl.asil_gate import SemanticConflictError

        override_cfg: dict = {}
        if map_file:
            override_cfg["map_file"] = map_file
        if lds_file:
            override_cfg["lds_file"] = lds_file
        if asil_level:
            override_cfg["asil_level"] = asil_level

        merged_cfg = {**self.config, **override_cfg}

        class _CtxProxy:
            config = merged_cfg

            def get_artifacts_path(self) -> Path:
                return self.run_context._artifacts_dir

            def validate_workspace(self) -> None:
                pass  # proxy skips workspace validation for UC4.4

        ctx_proxy = _CtxProxy()
        ctx_proxy.run_context = self

        self._trace("UC4.4: Starting post-merge semantic memory map check.")

        skill = UC44SemanticConflictSkill(
            run_context=ctx_proxy,
            gca_invoker=self.gca_invoker,
            on_log=self.on_log,
        )

        try:
            summary = skill.run()
        except SemanticConflictError as exc:
            self._trace(f"UC4.4: HARD BLOCK — {exc}", level="ERROR")
            result = NodeResult(
                node_id="UC4_4_POST_MERGE",
                status="error",
                output=str(exc),
                artifacts=[
                    str(self._artifacts_dir / "section_layout.json"),
                    str(self._artifacts_dir / "overlap_report.json"),
                    str(self._artifacts_dir / "asil_gate_decision.json"),
                    str(self._artifacts_dir / "semantic_conflict_report.md"),
                ],
                errors=[str(exc)],
            )
            self.on_node_complete(result)
            raise

        status  = summary.get("status", "pass")
        overlap = summary.get("has_overlap", False)
        self._trace(
            f"UC4.4: Complete | status={status} | overlap={overlap}",
            level="SUCCESS" if status == "pass" else "WARN",
        )

        artifacts = [v for k, v in summary.items() if k.endswith("_path") and v]
        result = NodeResult(
            node_id="UC4_4_POST_MERGE",
            status=status,
            output=summary.get("gca_report", "No overlap detected."),
            artifacts=artifacts,
        )
        self.on_node_complete(result)
        return result

    # ── Helpers ───────────────────────────────────────────────────────────

    def _validate_config(self, required_keys: list[str]) -> None:
        missing = [k for k in required_keys if not self.config.get(k)]
        if missing:
            raise ConfigValidationError(
                f"Missing required config fields: {', '.join(missing)}. "
                "Update config.json via the Config tab."
            )

    def _load_prompt(self, filename: str) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return f"[Prompt template '{filename}' not found — using default instructions]"

    def _render_prompt(self, template: str, context: dict) -> str:
        for key, value in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    @staticmethod
    def _resolve_workspace_path(value: str, workspace: Path) -> Path:
        candidate_path = Path(value)
        if candidate_path.is_absolute():
            return candidate_path
        return (workspace / candidate_path).resolve()

    @staticmethod
    def _default_human_review(node_id: str, message: str) -> bool:
        print(f"\n[DevNex] ── HUMAN REVIEW REQUIRED: {node_id} ──")
        print(message)
        answer = input("\nType 'yes' to continue, 'no' to abort: ").strip().lower()
        return answer == "yes"
