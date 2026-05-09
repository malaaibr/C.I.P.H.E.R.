"""DevNex Assistant — CLI entry point."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import click
from interfaces.cli.cli_commands import build_cli


@click.group()
def cli() -> None:
    """DevNex Assistant — V-Cycle AI Automation Tool"""


cli.add_command(build_cli())

if __name__ == "__main__":
    cli()
