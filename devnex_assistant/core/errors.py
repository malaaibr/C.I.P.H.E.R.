"""Domain error hierarchy for DevNex Assistant."""


class DevNexError(Exception):
    """Base for all DevNex exceptions."""


class GCABridgeError(DevNexError):
    """GCA communication failure (bridge unreachable, empty response, timeout)."""


class GCANotAvailableError(GCABridgeError):
    """VS Code or Bridge VSIX not reachable."""


class WorkflowAbortedError(DevNexError):
    """User rejected a human review gate — workflow halted."""


class NodeExecutionError(DevNexError):
    """A V-cycle node failed during execution."""


class ArtifactMissingError(DevNexError):
    """Required input artifact not found on disk."""


class ConfigValidationError(DevNexError):
    """config.json is missing required fields for the requested stage."""
