"""DevNexOrchestrator — coordinates V-cycle stage execution."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Any
from dataclasses import dataclass, field

from core.console_logging import format_console_log, utc_timestamp
from core.errors import (
    WorkflowAbortedError, NodeExecutionError,
    ConfigValidationError,
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


@dataclass
class NodeResult:
    """
    @brief Result contract returned by each V-cycle node.

    @details
    UI workers, CLI commands, and tests consume this object to inspect node
    status, raw output, generated artifacts, and non-fatal errors.
    """

    node_id:   str
    status:    str
    output:    str
    artifacts: list[str] = field(default_factory=list)
    errors:    list[str] = field(default_factory=list)


class DevNexOrchestrator:
    """
    @brief Coordinates V-cycle node execution for DevNex Assistant.

    @details
    Mirrors Int_Agent Orchestrator structure:
    - _trace() for structured logging (same pattern)
    - progress_callback(pct, msg) for GUI updates
    - Artifact persistence after each node
    - Human review gates that block on threading.Event

    Stage/Node mapping:
      S1N1 → lld_gen_skill.run_s1n1()
      S1N2 → human review (upload to req mgmt)
      S1N3 → human review (extract IDs)
      S1N4 → lld_gen_skill.run_s1n4()
      S2N1 → code_link_skill.run_s2n1()
      S2N2 → human review (inspect annotated code)
      S3N1 → trace_report_skill.run_s3()
      S4N1 → trace_report_skill.run_s4()
      S5N1 → trace_report_skill.run_s5()
      S6N1 → test_gen_skill.run_s6() + human review (.TST wait)
      S7N1 → test_gen_skill.run_s7()
      S8N1 → test_gen_skill.run_s8()
      S9N1 → full_trace_skill.run_s9()
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
        """
        @brief Initialize stores, callbacks, and run artifact directory.

        @param run_context Run metadata and artifact root for this workflow run.
        @param on_log Optional callback for log messages.
        @param on_node_started Optional callback invoked before node execution.
        @param on_node_complete Optional callback invoked after node execution.
        @param on_human_review Optional callback used by human-review gates.
        @param progress_callback Optional callback used by full-run progress.
        """
        self.run_context       = run_context
        self.on_log            = on_log or (lambda *_: None)
        self.on_node_started   = on_node_started or (lambda _: None)
        self.on_node_complete  = on_node_complete or (lambda _: None)
        self.on_human_review   = on_human_review or self._default_human_review
        self.progress_callback = progress_callback or (lambda *_: None)

        self.state_store  = StateStore()
        self.config_store = ConfigStore()
        self.config       = self.config_store.load()

        self._gca_invoker = None  # lazy-loaded on first use

        self._artifacts_dir = run_context.get_artifacts_path()
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    # ── Lazy GCA invoker ──────────────────────────────────────────────────

    @property
    def gca_invoker(self):
        """
        @brief Lazily construct the GCA invoker for the configured workspace.

        @return `DevNexGCAInvoker` instance reused by subsequent node calls.
        """
        if self._gca_invoker is None:
            from gca.vscode_invoker import DevNexGCAInvoker
            self._gca_invoker = DevNexGCAInvoker(Path(self.config.get("workspace_path", ".")))
        return self._gca_invoker

    # ── Logging ───────────────────────────────────────────────────────────

    def _trace(self, message: str, level: str = "INFO") -> None:
        """
        @brief Emit structured log line — same pattern as Int_Agent Orchestrator._trace().
        Calls both print() (console) and on_log callback (GUI log tail).
        """
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        line = format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller)
        print(line)
        self.on_log(message, level)

    # ── Node execution entry point ─────────────────────────────────────────

    def run_node(self, node_id: str) -> NodeResult:
        """
        @brief Execute a single V-cycle node by ID.

        @param node_id  e.g. "S1N1", "S2N1", "S6N1"
        @return NodeResult with status, output, and artifact paths.

        @raises ConfigValidationError when required config fields are absent.
        @raises NodeExecutionError    when GCA call or artifact write fails.
        @raises WorkflowAbortedError  when user rejects a human review gate.
        """
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
        """
        @brief Execute all nodes S1N1 → S9N1 sequentially.
        Mirrors Int_Agent Orchestrator.run_gui_resolve_flow() progress pattern.
        """
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

    # ── Stage implementations ──────────────────────────────────────────────

    def _run_s1n1(self) -> NodeResult:
        """@brief S1N1 — Collect inputs, build prompt, invoke GCA, write LLD CSV."""
        self._validate_config([
            "SWC_name", "G_SWDD_TEMP", "SWC_name_C", "SWC_name_H",
            "SWC_name_TEMP_LLD", "SWC_name_HLD", "lds_file", "map_file",
        ])
        swc = self.config["SWC_name"]
        self._trace(f"S1N1: Building LLD generation prompt for SWC '{swc}'.")

        workspace = Path(self.config.get("workspace_path", "."))

        # Resolve all configured file paths once so prompt placeholders and
        # attached-file metadata use the same canonical paths.
        resolved: dict[str, Path] = {
            key: self._resolve_workspace_path(self.config[key], workspace)
            for key in LLD_INPUT_FILE_KEYS
        }

        # Bug 1 fix: replace placeholders with full absolute paths so the LLM
        # receives the real file location, not just a bare filename.
        path_config = dict(self.config)
        for k, p in resolved.items():
            path_config[k] = str(p)

        prompt_template = self._load_prompt("lld_gen_v1.md")
        prompt = self._render_prompt(prompt_template, path_config)

        # Bug 2 fix: embed file contents directly in the prompt (Int_Agent pattern).
        # GeminiController has no reliable "attach file" API — content must be
        # included in the prompt text so GCA can see it in context.
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
                content_sections.append(
                    f"\n\n### FILE: {p.name}  ({p})\n[FILE NOT FOUND]"
                )
                self._trace(f"S1N1: Context file not found — '{p}'.", level="WARN")

        prompt += "\n\n## Attached Input Files\n" + "".join(content_sections)

        attached_files = [str(resolved[k]) for k in LLD_EMBEDDED_CONTEXT_KEYS]
        self._trace(f"S1N1: Invoking GCA (prompt={len(prompt)} chars, context_files={len(attached_files)}).")
        result = self.gca_invoker.invoke_prompt(prompt, attached_files)

        if not result.is_response_valid:
            raise NodeExecutionError("S1N1: GCA returned invalid response.")

        out_path = self._artifacts_dir / f"{swc}_TEMP_LLD_updated.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S1N1: Artifact written → '{out_path}'.", level="SUCCESS")

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
        swc = self.config["SWC_name"]
        insp_file = self.config["SWC_nameInspBaseLLD"]
        self._trace(f"S1N4: Categorizing requirements from '{insp_file}'.")

        insp_content = ""
        if Path(insp_file).exists():
            insp_content = Path(insp_file).read_text(encoding="utf-8")

        prompt = (
            "You are a software requirements engineer.\n"
            "Categorize the following LLD requirements into:\n"
            "  - FUNCTIONAL: states core functionality testable by unit test tools\n"
            "  - NON_FUNCTIONAL: configuration, shared variables, KPIs (human-review only)\n\n"
            f"Input requirements:\n{insp_content}\n\n"
            "Output: CSV with columns: REQ_ID, CATEGORY, DESCRIPTION"
        )

        result = self.gca_invoker.invoke_prompt(prompt, [insp_file])
        if not result.is_response_valid:
            raise NodeExecutionError("S1N4: GCA categorization returned invalid response.")

        out_path = self._artifacts_dir / f"{swc}_FUNC_req.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S1N4: Functional requirements written → '{out_path}'.", level="SUCCESS")

        return NodeResult(
            node_id="S1N4", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s2n1(self) -> NodeResult:
        """@brief S2N1 — Embed LLD requirement references in source code as structured comments."""
        self._validate_config(["SWC_name", "SWC_name_C"])
        swc = self.config["SWC_name"]
        source_file = self.config["SWC_name_C"]
        func_req_file = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")

        self._trace(f"S2N1: Embedding LLD references into '{source_file}'.")

        prompt_template = self._load_prompt("code_link_v1.md")
        prompt = self._render_prompt(prompt_template, self.config)

        result = self.gca_invoker.invoke_prompt(prompt, [source_file, func_req_file])
        if not result.is_response_valid:
            raise NodeExecutionError("S2N1: GCA code linking returned invalid response.")

        out_path = self._artifacts_dir / f"updated_{swc}.c"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S2N1: Annotated source written → '{out_path}'.", level="SUCCESS")

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
        """@brief S3N1 — Generate LLD→Code traceability report."""
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S3N1: Generating LLD → Code traceability report.")
        source_file = str(self._artifacts_dir / f"updated_{swc}.c")
        func_req    = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")
        prompt = (
            "Generate a CSV traceability report linking LLD requirement IDs to "
            "code function names and line numbers.\n"
            "Columns: REQ_ID, FUNCTION_NAME, FILE, LINE_NUMBER, COVERAGE_STATUS"
        )
        result = self.gca_invoker.invoke_prompt(prompt, [source_file, func_req])
        out_path = self._artifacts_dir / "LLD_Code_Trace_Report.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S3N1: Trace report written → '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S3N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s4n1(self) -> NodeResult:
        """@brief S4N1 — Map LLD requirements to parent HLD items."""
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S4N1: Linking LLD requirements to HLD items.")
        hld_file = self.config.get("SWC_name_HLD", "")
        func_req = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")
        prompt = (
            "Map each LLD requirement ID to its parent HLD requirement ID.\n"
            "Output JSON array: [{\"lld_id\": ..., \"hld_id\": ..., \"link_type\": ..., \"rationale\": ...}]"
        )
        result = self.gca_invoker.invoke_prompt(prompt, [hld_file, func_req])
        out_path = self._artifacts_dir / "HLD_LLD_Links.json"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S4N1: HLD→LLD links written → '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S4N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s5n1(self) -> NodeResult:
        """@brief S5N1 — Generate full downstream Code→LLD→HLD traceability matrix."""
        self._trace("S5N1: Building full downstream traceability matrix.")
        trace_report = str(self._artifacts_dir / "LLD_Code_Trace_Report.csv")
        hld_links    = str(self._artifacts_dir / "HLD_LLD_Links.json")
        prompt = (
            "Combine HLD→LLD and LLD→Code links into a single traceability matrix CSV.\n"
            "Columns: HLD_ID, LLD_ID, CODE_FUNCTION, FILE, LINE, COVERAGE_STATUS"
        )
        result = self.gca_invoker.invoke_prompt(prompt, [trace_report, hld_links])
        out_path = self._artifacts_dir / "HLD_LLD_Code_Trace_Matrix.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S5N1: Full trace matrix written → '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S5N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s6n1(self) -> NodeResult:
        """
        @brief S6N1 — Generate VectorCAST test artifacts, then wait for .TST output.

        @details
        Two sub-phases:
          1. GCA generates test.bat and test input scaffolding.
          2. Human review gate — user runs VectorCAST and waits for .TST files.
        """
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S6N1: Generating VectorCAST test artifacts via GCA.")
        source_file = str(self._artifacts_dir / f"updated_{swc}.c")
        func_req    = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")

        prompt = (
            f"Generate a VectorCAST test.bat script and test environment scaffolding "
            f"for SWC '{swc}'. Include all functional requirements from the CSV.\n"
            "Output: test.bat content followed by a ---SEPARATOR--- then the test environment config."
        )
        result = self.gca_invoker.invoke_prompt(prompt, [source_file, func_req])
        bat_path = self._artifacts_dir / "test.bat"
        bat_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S6N1: test.bat written → '{bat_path}'.")

        msg = (
            f"Run VectorCAST using the generated 'test.bat' file.\n\n"
            f"The platform will wait here until .TST files are produced.\n"
            f"Once execution is complete and .TST files are available in the workspace, click Continue."
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
        result = self.gca_invoker.invoke_prompt(prompt, [str(f) for f in tst_files])
        out_path = self._artifacts_dir / f"{swc}_UTD.md"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S7N1: UTD written → '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S7N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s8n1(self) -> NodeResult:
        """@brief S8N1 — Link UTD test cases to LLD requirements."""
        swc = self.config.get("SWC_name", "SWC")
        self._trace("S8N1: Linking UTD test cases to LLD requirements.")
        utd_file  = str(self._artifacts_dir / f"{swc}_UTD.md")
        func_req  = str(self._artifacts_dir / f"{swc}_FUNC_req.csv")
        prompt = (
            "Map each unit test case to its corresponding LLD functional requirement.\n"
            "Output JSON array: [{\"test_case_id\": ..., \"req_id\": ..., \"test_result\": ..., \"coverage_contribution\": ...}]"
        )
        result = self.gca_invoker.invoke_prompt(prompt, [utd_file, func_req])
        out_path = self._artifacts_dir / "UTD_LLD_Links.json"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S8N1: UTD→LLD links written → '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S8N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    def _run_s9n1(self) -> NodeResult:
        """@brief S9N1 — Consolidate full traceability matrix: HLD→LLD→Code→Test→UTD."""
        self._trace("S9N1: Building final full traceability matrix.")
        inputs = [
            str(self._artifacts_dir / "HLD_LLD_Code_Trace_Matrix.csv"),
            str(self._artifacts_dir / "UTD_LLD_Links.json"),
        ]
        prompt_template = self._load_prompt("full_trace_v1.md")
        prompt = self._render_prompt(prompt_template, self.config)
        result = self.gca_invoker.invoke_prompt(prompt, inputs)
        out_path = self._artifacts_dir / "Full_Traceability_Matrix.csv"
        out_path.write_text(result.raw_response, encoding="utf-8")
        self._trace(f"S9N1: Full traceability matrix written → '{out_path}'.", level="SUCCESS")
        return NodeResult(
            node_id="S9N1", status="complete",
            output=result.raw_response, artifacts=[str(out_path)],
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _validate_config(self, required_keys: list[str]) -> None:
        """
        @brief Ensure required configuration keys are populated.

        @param required_keys Internal config keys required by a node.
        @raises ConfigValidationError When one or more required values are missing.
        """
        missing = [k for k in required_keys if not self.config.get(k)]
        if missing:
            raise ConfigValidationError(
                f"Missing required config fields: {', '.join(missing)}. "
                "Update config.json via the Config tab."
            )

    def _load_prompt(self, filename: str) -> str:
        """
        @brief Load a prompt template from the package prompts directory.

        @param filename Prompt template filename.
        @return Template text, or a fallback marker when the file is missing.
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return f"[Prompt template '{filename}' not found — using default instructions]"

    def _render_prompt(self, template: str, context: dict) -> str:
        """@brief Replace {{KEY}} placeholders with config values."""
        for key, value in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    @staticmethod
    def _resolve_workspace_path(value: str, workspace: Path) -> Path:
        """
        @brief Resolve a config file path against the active workspace.

        @param value Raw file path from configuration.
        @param workspace Workspace root for relative file paths.
        @return Absolute path when `value` is relative; original path when absolute.
        """
        candidate_path = Path(value)
        if candidate_path.is_absolute():
            return candidate_path
        return (workspace / candidate_path).resolve()

    @staticmethod
    def _default_human_review(node_id: str, message: str) -> bool:
        """@brief CLI fallback for human review gates."""
        print(f"\n[DevNex] ── HUMAN REVIEW REQUIRED: {node_id} ──")
        print(message)
        answer = input("\nType 'yes' to continue, 'no' to abort: ").strip().lower()
        return answer == "yes"
