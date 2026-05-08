"""Click CLI command groups for DevNex Assistant."""

from __future__ import annotations

import json
import sys
from typing import Callable

import click

from core.errors import GCANotAvailableError

ProgressCallback = Callable[[int, str], None]


def _make_orchestrator():
    """
    @brief Build the default orchestrator used by CLI commands.

    @return A `DevNexOrchestrator` with default run context and callbacks.
    """
    from core.orchestrator import DevNexOrchestrator
    from core.run_context import DevNexRunContext

    run_context = DevNexRunContext()
    return DevNexOrchestrator(run_context=run_context)


def build_cli() -> click.Group:
    """
    @brief Return a Click group containing all DevNex CLI commands.

    @return Configured root Click command group.
    """

    @click.group("devnex")
    def devnex_group() -> None:
        """DevNex Assistant - V-Cycle AI Automation Tool."""

    @devnex_group.command("run-stage")
    @click.argument("stage")
    def run_stage(stage: str) -> None:
        """Run a specific V-cycle node. STAGE: S1N1, S1N2 ... S9N1."""
        _run_single(stage)

    @devnex_group.command("run-all")
    def run_all() -> None:
        """Run the full V-cycle workflow S1N1 -> S9N1."""
        orchestrator = _make_orchestrator()

        try:

            def progress(percent: int, message: str) -> None:
                """Emit a progress line for the active full-run command."""
                click.echo(f"[{percent:3d}%] {message}")

            results = orchestrator.run_all(progress_callback=progress)
            click.echo(f"\nCompleted {len(results)} node(s).")
        except GCANotAvailableError as exc:
            click.echo(f"[ERROR] {exc}", err=True)
            sys.exit(1)
        except Exception as exc:
            click.echo(f"[ERROR] {exc}", err=True)
            sys.exit(1)

    @devnex_group.command("status")
    def status() -> None:
        """Show current workflow state and node statuses."""
        from persistence.state_store import StateStore

        workflow_state = StateStore().load()
        node_statuses = workflow_state.get("node_statuses", {})
        if not node_statuses:
            click.echo("No workflow state found. Run a stage first.")
            return

        click.echo("\nNode statuses:")
        for node_id, status_text in node_statuses.items():
            marker = "OK" if status_text == "complete" else ("ERR" if status_text == "error" else "--")
            click.echo(f"  {marker:<3} {node_id:<8} {status_text}")

    @devnex_group.command("config")
    @click.option("--show", is_flag=True, default=False, help="Print current config")
    def config_cmd(show: bool) -> None:
        """Show or verify the project configuration."""
        from persistence.config_store import ConfigStore

        config = ConfigStore().load()
        if show:
            click.echo(json.dumps(config, indent=2))
            return

        missing_keys = [
            key for key, value in config.items() if not value and key != "workspace_path"
        ]
        if missing_keys:
            click.echo(f"[WARN] Missing config fields: {', '.join(missing_keys)}")
            return

        click.echo("[OK] All config fields are set.")

    return devnex_group


def _run_single(stage: str) -> None:
    """
    @brief Execute one V-cycle node and print its result.

    @param stage Node ID to execute, for example `S1N1`.
    """
    orchestrator = _make_orchestrator()

    try:
        node_result = orchestrator.run_node(stage)
        click.echo(f"\nStatus: {node_result.status}")

        if node_result.artifacts:
            click.echo("Artifacts:")
            for artifact_path in node_result.artifacts:
                click.echo(f"  -> {artifact_path}")

        for error_message in node_result.errors:
            click.echo(f"  [ERROR] {error_message}", err=True)
    except GCANotAvailableError as exc:
        click.echo(f"[ERROR] {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"[ERROR] {exc}", err=True)
        sys.exit(1)


cli = build_cli()
