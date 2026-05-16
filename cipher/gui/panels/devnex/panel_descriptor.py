"""DevNex PanelDescriptor (T-033, ADR-0005)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PanelDescriptor:
    """Describes an agent panel for shell registration."""

    panel_id: str
    title: str
    agent_id: str
    icon: str = ""
    initial_width: int = 400
    initial_height: int = 600


DEVNEX_PANEL = PanelDescriptor(
    panel_id="devnex-workflow",
    title="DevNex V-Cycle",
    agent_id="devnex-001",
    icon="⚙",
)
