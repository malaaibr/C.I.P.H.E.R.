"""AF.json graph executor — evolves from LLD WorkflowEngine specification."""

from __future__ import annotations

import inspect
import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List

from core.console_logging import format_console_log, utc_timestamp
from core.errors import WorkflowAbortedError

MODULE_NAME = "WorkflowEngine"


class WorkflowEngine:
    """
    @brief Loads and executes AF.json workflow graphs.

    @details
    Supported node serviceIds:
      - logic.internal          : start / end (no-op)
      - extension.llm.sendPrompt: calls GCA via bridge
      - atomic.executionService : runs subprocess
      - logic.humanReview       : pauses for human input
    """

    def __init__(
        self,
        gca_bridge,
        on_node_start:    Callable[[str, str], None] | None = None,
        on_node_complete: Callable[[str, str], None] | None = None,
        on_human_review:  Callable[[str, dict], bool] | None = None,
    ) -> None:
        self.gca_bridge       = gca_bridge
        self.on_node_start    = on_node_start or (lambda *_: None)
        self.on_node_complete = on_node_complete or (lambda *_: None)
        self.on_human_review  = on_human_review or self._default_human_review

    def _trace(self, message: str, level: str = "INFO") -> None:
        caller = "<unknown>"
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back.f_code.co_name
        print(format_console_log(MODULE_NAME, level, message, utc_timestamp(), caller))

    def execute(self, workflow_path: str, inputs: Dict[str, str]) -> str:
        """
        @brief Execute an AF.json workflow graph and return the final LLM response.

        @param workflow_path Path to the AF.json workflow definition.
        @param inputs        Template variable substitutions for {{nodeId.output.port}} refs.
        @return Raw LLM response from the last sendPrompt node.
        """
        self._trace(f"Loading workflow from '{workflow_path}'.")
        graph = json.loads(Path(workflow_path).read_text(encoding="utf-8"))
        node_outputs: Dict[str, Dict[str, str]] = {}
        ordered = self._topological_sort(graph)
        self._trace(f"Executing {len(ordered)} node(s) in topological order.")

        for node in ordered:
            resolved   = self._resolve_templates(node["data"], node_outputs, inputs)
            service_id = resolved.get("serviceId", "")

            if service_id == "logic.internal":
                node_outputs[node["id"]] = {"next": "done"}

            elif service_id == "extension.llm.sendPrompt":
                prompt    = resolved.get("prompt", "")
                files_raw = resolved.get("attachedFiles", "[]")
                files     = json.loads(files_raw) if isinstance(files_raw, str) else files_raw
                self.on_node_start(node["id"], resolved.get("label", "GCA Call"))
                self._trace(f"GCA call for node '{node['id']}'.")
                response = self.gca_bridge.send_prompt(prompt, files)
                node_outputs[node["id"]] = {"llmResponse": response, "next": "done"}
                self.on_node_complete(node["id"], response)

            elif service_id == "atomic.executionService":
                script = resolved.get("scriptPath", "")
                args   = resolved.get("args", [])
                cwd    = resolved.get("cwd", ".")
                result = subprocess.run(
                    [script] + args, capture_output=True, text=True, cwd=cwd
                )
                node_outputs[node["id"]] = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "code":   str(result.returncode),
                    "next":   "done",
                }
                self._trace(f"Script node '{node['id']}' exited with code {result.returncode}.")

            elif service_id == "logic.humanReview":
                approved = self.on_human_review(node["id"], resolved)
                if not approved:
                    raise WorkflowAbortedError(f"User rejected review gate at node '{node['id']}'.")
                node_outputs[node["id"]] = {"approved": "true", "next": "done"}

        for node in reversed(ordered):
            if node["data"].get("serviceId") == "extension.llm.sendPrompt":
                return node_outputs[node["id"]]["llmResponse"]
        return ""

    def _topological_sort(self, graph: dict) -> List[dict]:
        """@brief Kahn's algorithm on node graph edges (control edges only)."""
        nodes     = {n["id"]: n for n in graph["nodes"]}
        in_degree = {nid: 0 for nid in nodes}
        adjacency: Dict[str, List[str]] = {nid: [] for nid in nodes}

        for edge in graph["edges"]:
            if edge.get("sourceHandle") == "next":
                adjacency[edge["source"]].append(edge["target"])
                in_degree[edge["target"]] += 1

        queue  = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            nid = queue.pop(0)
            result.append(nodes[nid])
            for neighbor in adjacency[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return result

    def _resolve_templates(
        self,
        data:    dict,
        outputs: Dict[str, Dict[str, str]],
        inputs:  Dict[str, str],
    ) -> dict:
        """@brief Replace {{nodeId.output.portId}} with actual node output values."""
        def resolve(val):
            if not isinstance(val, str):
                return val

            def replace(match):
                parts   = match.group(1).split(".")
                node_id = parts[0]
                port_id = parts[2] if len(parts) > 2 else parts[-1]
                return outputs.get(node_id, {}).get(port_id, inputs.get(node_id, match.group(0)))

            return re.sub(r"\{\{([^}]+)\}\}", replace, val)

        return {k: resolve(v) for k, v in data.items()}

    @staticmethod
    def _default_human_review(node_id: str, data: dict) -> bool:
        msg    = data.get("message", "Human review required. Continue?")
        print(f"\n[DevNex] REVIEW REQUIRED: {msg}")
        answer = input("Type 'yes' to continue, 'no' to abort: ").strip().lower()
        return answer == "yes"
