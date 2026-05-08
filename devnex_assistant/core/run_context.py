"""Run-level metadata model for DevNex Assistant — adapted from Int_Agent RunContext."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class DevNexRunContext(BaseModel):
    """
    @brief Carries immutable identifiers and paths for one DevNex workflow run.
    Adapted from Int_Agent RunContext.
    """

    run_id:         str      = Field(default_factory=lambda: str(uuid4()))
    start_time:     datetime = Field(default_factory=lambda: datetime.now(UTC))
    swc_name:       str      = ""
    workspace_path: Path     = Field(default_factory=Path.cwd)
    run_dir:        Path | None = None

    @model_validator(mode="after")
    def set_default_run_dir(self) -> "DevNexRunContext":
        if self.run_dir is None:
            self.run_dir = Path.home() / ".devnex" / "runs"
        return self

    def get_artifacts_path(self) -> Path:
        """@brief Returns the concrete artifact directory for this run."""
        return self.run_dir / self.run_id  # type: ignore[operator]
