"""Run-level metadata model for DevNex Assistant.

F-010 fix: workspace_path is now validated — raises ConfigValidationError when
the path does not exist or is not a directory, so UC 4.4 and other skills that
rely on correct workspace resolution fail fast with a clear message.
"""

from __future__ import annotations

from datetime import timezone, datetime
from pathlib import Path
from uuid import uuid4

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc  # Python 3.10 compat

from pydantic import BaseModel, Field, model_validator

from core.errors import ConfigValidationError


class DevNexRunContext(BaseModel):
    """
    @brief Carries immutable identifiers and paths for one DevNex workflow run.
    """

    run_id:         str      = Field(default_factory=lambda: str(uuid4()))
    start_time:     datetime = Field(default_factory=lambda: datetime.now(UTC))
    swc_name:       str      = ""
    workspace_path: Path     = Field(default_factory=Path.cwd)
    run_dir:        Path | None = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def set_default_run_dir(self) -> "DevNexRunContext":
        if self.run_dir is None:
            self.run_dir = Path.home() / ".devnex" / "runs"
        return self

    def validate_workspace(self) -> None:
        """
        @brief F-010 — Assert workspace_path exists and is a directory.

        Call this before any node that resolves relative file paths against
        workspace_path (S1N1, UC 4.4, etc.).

        @raises ConfigValidationError When workspace_path is absent or not a dir.
        """
        wp = Path(self.workspace_path)
        if not wp.exists():
            raise ConfigValidationError(
                f"workspace_path does not exist: '{wp}'. "
                "Update the path in Config -> workspace_path."
            )
        if not wp.is_dir():
            raise ConfigValidationError(
                f"workspace_path is not a directory: '{wp}'."
            )

    def get_artifacts_path(self) -> Path:
        """@brief Returns the concrete artifact directory for this run."""
        return self.run_dir / self.run_id  # type: ignore[operator]
