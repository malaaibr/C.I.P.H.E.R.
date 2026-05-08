"""Click CLI command groups for DevNex Assistant."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from core.errors import GCANotAvailableError


def _make_orchestrator():
    from core.orchestrator import DevNexOrchestrator
    from core.run_context import DevNexRunContext
    ctx = DevNexRunContext()
    return DevNexOrchestrator(run_context=ctx)


def build_cli():
    """@brief Return a click Group containing all DevNex CLI commands."""

    @click.group("devnex")
    def devnex_group() -> None:
        """DevNex Assistant — V-Cycle AI Automation Tool"""

    @devnex_group.command("run-stage")
    @click.argument("stage")
    def run_stage(stage: str) -> None:
        """Run a specific V-cycle node. STAGE: S1N1, S1N2 … S9N1."""
        _run_single(stage)

    @devnex_group.command("run-all")
    def run_all() -> None:
        """Run the full V-cycle workflow S1N1 → S9N1."""
        orch = _make_orchestrator()
        try:
            def progress(pct: int, msg: str) -> None:
                click.echo(f"[{pct:3d}%] {msg}")

            results = orch.run_all(progress_callback=progress)
            click.echo(f"\nCompleted {len(results)} node(s).")
        except GCANotAvailableError as e:
            click.echo(f"[ERROR] {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"[ERROR] {e}", err=True)
            sys.exit(1)

    @devnex_group.command("status")
    def status() -> None:
        """Show current workflow state and node statuses."""
        from persistence.state_store import StateStore
        state    = StateStore().load()
        statuses = state.get("node_statuses", {})
        if not statuses:
            click.echo("No workflow state found. Run a stage first.")
            return
        click.echo("\nNode statuses:")
        for nid, s in statuses.items():
            marker = "✓" if s == "complete" else ("✗" if s == "error" else "○")
            click.echo(f"  {marker}  {nid:<8} {s}")

    @devnex_group.command("config")
    @click.option("--show", is_flag=True, default=False, help="Print current config")
    def config_cmd(show: bool) -> None:
        """Show or verify the project configuration."""
        from persistence.config_store import ConfigStore
        cfg = ConfigStore().load()
        if show:
            import json
            click.echo(json.dumps(cfg, indent=2))
        else:
            missing = [k for k, v in cfg.items() if not v and k != "workspace_path"]
            if missing:
                click.echo(f"[WARN] Missing config fields: {', '.join(missing)}")
            else:
                click.echo("[OK] All config fields are set.")

    return devnex_group


def _run_single(stage: str) -> None:
    orch = _make_orchestrator()
    try:
        result = orch.run_node(stage)
        click.echo(f"\nStatus: {result.status}")
        if result.artifacts:
            click.echo("Artifacts:")
            for a in result.artifacts:
                click.echo(f"  → {a}")
        if result.errors:
            for e in result.errors:
                click.echo(f"  [ERROR] {e}", err=True)
    except GCANotAvailableError as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
