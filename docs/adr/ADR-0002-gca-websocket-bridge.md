# ADR-0002: GCA WebSocket Bridge Protocol

- **Status:** Accepted
- **Deciders:** CIPHER Architecture Team
- **Date:** 2026-05-16
- **Layer:** TRF (Tool & Resource Fabric)
- **Tags:** gca, websocket, vscode, bridge, trf, poc, security

---

## 1. Context and Problem Statement

CIPHER requires a reliable, deterministic mechanism to invoke the GitHub Copilot Agent (GCA) via its VS Code extension WebSocket interface for `CODE_GEN` task class operations. GCA is a locally-installed VS Code extension that provides access to advanced coding models (GitHub Copilot) without paid API calls.

The DevNex Assistant codebase (CAR-001) implements a working GCA bridge (`bridge/gca_bridge.py`) using a 5-step isolation pattern: (1) validate prompt, (2) create isolated workspace and launch VS Code via VSCodeController, (3) poll `~/.gca_instances.json` until a new GCA instance registers with an open WebSocket port, (4) send prompt via `_DirectGCAClient` WebSocket (5 retries, 5s backoff), (5) store `GCAResponse`.

This pattern is functionally correct and race-free — by capturing the WebSocket port at instance detection time (step 3), the bridge avoids a TOCTOU race between port detection and connection. However, the existing DevNex implementation has two critical portability defects:

1. **DEBT-001 from CAR-001**: `_ADP_ROOT = r"C:\Ipnext\AI_initatives\cb513_ADP_Dev-master2.0+\cb513_ADP_Dev-master"` — an absolute Windows path hardcoded in the source. This breaks on any machine other than the original developer's.
2. **DEBT-006 from CAR-001**: The GCA registry file path and the expected port range are not configurable. Test environments cannot mock the registry.

This ADR defines the canonical CIPHER GCA WebSocket Bridge Protocol that resolves these defects while fully preserving the 5-step isolation pattern.

---

## 2. Decision Drivers

- **Portability**: The bridge must work on any developer machine, in any Docker container, and in CI environments — the hardcoded `_ADP_ROOT` path must be eliminated entirely.
- **Testability**: The bridge must be testable without a real GCA instance. A `MockGCABridge` must be substitutable at the `LLMBackend` Protocol boundary.
- **Race-free connection**: The port-captured-at-detection pattern from DevNex is correct and must be preserved. Do not attempt to re-resolve the port after detection.
- **Configurable registry**: The registry file path (`~/.gca_instances.json`) must be configurable via environment variable for environments where the home directory is non-standard.
- **Session isolation**: Each `CODE_GEN` task creates one isolated VS Code workspace and disposes it on task completion. No persistent VS Code sessions across tasks in POC.
- **Retry policy**: 5 retries with 5s backoff (inherited from DevNex — do not change for POC).
- **ADR-0001 integration**: The bridge is exposed via `GCAWebSocketDriver` implementing `LLMBackend` Protocol. The bridge itself is not a public API — only the driver is.

---

## 3. Considered Options

### Option A: Preserve DevNex GCABridge As-Is (No Changes)
Copy `gca_bridge.py` and `vscode_controller.py` directly into CIPHER without modification.

**Pros**: Zero integration risk; working code.
**Cons**: `_ADP_ROOT` hardcoding breaks on every machine other than the original developer's; not testable in CI; violates CIPHER portability requirement.

### Option B: Environment-Variable Registry Path (Selected)
Replace `_ADP_ROOT` with `os.environ.get("GCA_REGISTRY_PATH", ...)`. Keep all other logic identical to DevNex. Add `MockGCABridge` for test environments.

**Pros**: Minimal change; preserves race-free pattern; testable; portable.
**Cons**: Requires the GCA registry file to be reachable from wherever GCA_REGISTRY_PATH points.

### Option C: Registry as Redis Key
Store GCA instance registry in Redis instead of a file. Poll Redis for new instance entries.

**Pros**: Works in distributed environments.
**Cons**: Requires GCA VSIX extension to write to Redis — the extension only writes to `~/.gca_instances.json`. This would require modifying the GCA VSIX extension itself, which is out of scope. Not feasible.

### Option D: Fixed Port (ws://localhost:7820) Always
Hardcode the GCA WebSocket port to 7820 as stated in the CIPHER spec §1.1. Skip the registry poll.

**Pros**: Simplest possible implementation.
**Cons**: The GCA VSIX extension does not always bind to port 7820 — it registers a dynamically-allocated port in the registry file. Hardcoding the port would break when the extension allocates a different port, introducing the TOCTOU race the DevNex pattern specifically avoids. The spec's "ws://localhost:7820" is a nominal address, not a fixed port assignment.

**Decision on Option D**: REJECTED. The DevNex race-free pattern (capture port at detection time from registry) is architecturally superior to a fixed port. The spec's 7820 notation is used as a documentation placeholder; the actual port is registry-driven.

---

## 4. Decision

**Selected: Option B — Environment-Variable Registry Path with MockGCABridge**

The CIPHER GCA WebSocket Bridge adopts the 5-step isolation pattern from DevNex `gca_bridge.py` (CAR-001) with the following specific changes:

### 4.1 Registry Path Parameterisation

```python
import os
from pathlib import Path

# BEFORE (DevNex — PROHIBITED):
# _ADP_ROOT = r"C:\Ipnext\AI_initatives\cb513_ADP_Dev-master2.0+\cb513_ADP_Dev-master"
# _GCA_INSTANCES_FILE = os.path.join(_ADP_ROOT, ".gca_instances.json")

# AFTER (CIPHER — REQUIRED):
GCA_REGISTRY_PATH: str = os.environ.get(
    "GCA_REGISTRY_PATH",
    str(Path.home() / ".gca_instances.json")
)
# GCA_REGISTRY_PATH is read once at module load time.
# Override in .env file or SecretFabric for non-standard environments.
```

### 4.2 The 5-Step Protocol (Canonical CIPHER Form)

```python
class GCABridge:
    """
    CIPHER GCA WebSocket Bridge — canonical 5-step isolation protocol.
    Ported from DevNex bridge/gca_bridge.py (CAR-001 WRAP + REFACTOR).
    """

    _GCA_SEND_RETRIES: int = 5
    _GCA_RETRY_BACKOFF: float = 5.0  # seconds

    async def invoke_gca(self, prompt: str, workspace_hint: str = "") -> GCAResponse:
        """
        Step 1 — Validate prompt.
            - Raise GCABridgeError if prompt is empty or exceeds 32,000 chars.

        Step 2 — Create isolated workspace + launch VS Code.
            - Call VSCodeController.create_workspace(workspace_hint) → workspace_path: Path
            - Call VSCodeController.launch(workspace_path) → launches VS Code process
            - Record pre-launch instance set from GCA_REGISTRY_PATH.

        Step 3 — Poll registry until new instance registers.
            - Poll GCA_REGISTRY_PATH (JSON file) every 1s for up to 60s.
            - New instance = entry whose key was not in pre-launch instance set.
            - Capture port = new_entry["wsPort"] at detection time.
            - Raise GCANotAvailableError if no new instance within 60s.

        Step 4 — Send prompt via WebSocket (5 retries, 5s backoff).
            - _DirectGCAClient(ws://localhost:{port}).send(prompt)
            - On WebSocket error: wait _GCA_RETRY_BACKOFF seconds, retry.
            - After _GCA_SEND_RETRIES failures: raise GCABridgeError.

        Step 5 — Store and return GCAResponse.
            - GCAResponse(text=response_text, instance_id=instance_uuid, duration_ms=elapsed)
        """

class GCANotAvailableError(Exception):
    """Raised when no GCA instance registers within the poll timeout."""

class GCABridgeError(Exception):
    """Raised when the prompt send fails after all retries."""

class GCAResponse:
    text: str
    instance_id: str   # UUID from registry entry
    duration_ms: float
```

### 4.3 WebSocket Message Schema

All messages exchanged over the GCA WebSocket use JSON encoding:

**Outbound (CIPHER → GCA Extension)**:
```json
{
  "command": "gca.sendPrompt",
  "payload": {
    "prompt": "<string — max 32000 chars>"
  },
  "instanceId": "<uuid — from registry entry>"
}
```

**Outbound (reset chat context)**:
```json
{
  "command": "gca.resetChat",
  "payload": {},
  "instanceId": "<uuid>"
}
```

**Inbound (GCA Extension → CIPHER)**:
```json
{
  "status": "success | error",
  "response": "<llm text — may be empty string on error>",
  "instanceId": "<uuid — must match sent instanceId>",
  "errorMessage": "<string — only present if status==error>"
}
```

### 4.4 Session Lifecycle

```
[CODE_GEN Task Received]
        │
        ▼
GCABridge.invoke_gca(prompt, workspace_hint)
        │
Step 2: VSCodeController.create_workspace() → /tmp/cipher_ws_{uuid}/
Step 2: VSCodeController.launch(workspace_path)
        │
Step 3: poll GCA_REGISTRY_PATH until new entry
        │
Step 4: send prompt via ws://localhost:{port}
        │
Step 5: receive GCAResponse
        │
        ▼
[GCAWebSocketDriver returns LLMResponse]
        │
        ▼
VSCodeController.dispose(workspace_path)  ← workspace deleted after task
        │
        ▼
[Task Complete]
```

Each `CODE_GEN` task gets exactly one workspace and one VS Code instance. The workspace is deleted synchronously after the response is received. No persistent VS Code sessions across tasks in POC.

### 4.5 Reconnection Policy

- **Within a task**: 5 retries with 5s backoff (inherited from DevNex `_GCA_SEND_RETRIES`, `_GCA_RETRY_BACKOFF`).
- **Across tasks**: No reconnection. Each task creates a new VS Code instance from scratch. This avoids stale chat context contaminating subsequent tasks.
- **POC hard rule**: Retry count and backoff are not configurable in POC. They may be exposed as env vars (`GCA_SEND_RETRIES`, `GCA_RETRY_BACKOFF`) in MVP.

### 4.6 MockGCABridge for Testing

```python
class MockGCABridge:
    """Test double for GCABridge. Does not launch VS Code or connect to WebSocket."""

    def __init__(self, response_text: str = "mock GCA response"):
        self.response_text = response_text
        self.calls: list[dict] = []   # records invocations for assertion

    async def invoke_gca(self, prompt: str, workspace_hint: str = "") -> GCAResponse:
        self.calls.append({"prompt": prompt, "workspace_hint": workspace_hint})
        return GCAResponse(
            text=self.response_text,
            instance_id="mock-instance-uuid",
            duration_ms=0.0
        )
```

`MockGCABridge` is injected into `GCAWebSocketDriver` via constructor parameter in test environments:
```python
# Production:
driver = GCAWebSocketDriver(bridge=GCABridge())

# Test:
driver = GCAWebSocketDriver(bridge=MockGCABridge(response_text="ID,HLD_REF,..."))
```

---

## 5. Configuration Reference

All configurable parameters are read from environment variables (populated via `deploy/.env` in Docker Compose):

| Environment Variable | Default | Description |
|---|---|---|
| `GCA_REGISTRY_PATH` | `~/.gca_instances.json` | Path to GCA instance registry file |
| `GCA_POLL_TIMEOUT_S` | `60` | Maximum seconds to wait for new GCA instance in Step 3 |
| `GCA_POLL_INTERVAL_S` | `1` | Registry poll interval in seconds |
| `GCA_WORKSPACE_BASE` | `/tmp` | Base directory for isolated VS Code workspaces |
| `VSCODE_PATH` | `code` | VS Code executable path or command name |

---

## 6. Security Considerations

- **WebSocket is localhost-only**: `ws://localhost:{port}` — the GCA WebSocket is never exposed outside the host machine. Docker Compose network isolation ensures this.
- **Workspace isolation**: Each task runs in a separate temporary directory (`/tmp/cipher_ws_{uuid}/`). Workspaces are deleted after task completion. No cross-task file system contamination.
- **No credentials in prompt**: The GCA WebSocket bridge sends only the prompt text and instance UUID. No API keys, auth tokens, or secrets are transmitted over the WebSocket.
- **Registry file permissions**: `~/.gca_instances.json` is owned by the local user. No elevated privileges required.

---

## 7. Reference Codebase Impact

| CAR | Module | Disposition | Change from DevNex |
|---|---|---|---|
| CAR-001 | `bridge/gca_bridge.py` | WRAP + REFACTOR | Remove `_ADP_ROOT`; parameterise registry path via `GCA_REGISTRY_PATH` env var; all 5-step logic preserved |
| CAR-001 | `bridge/vscode_controller.py` | WRAP | Read workspace base from `GCA_WORKSPACE_BASE` env var; otherwise unchanged |
| CAR-001 (DEBT-001) | Hardcoded `_ADP_ROOT` | RESOLVED | Replaced by `GCA_REGISTRY_PATH` env var with `~/.gca_instances.json` default |
| CAR-001 (DEBT-006) | Non-configurable registry path | RESOLVED | All registry/port parameters now env-var configurable |

---

## 8. Consequences

**Positive**:
- The bridge is portable: works on any developer machine, any OS, any CI environment with VS Code + GCA VSIX installed.
- The `MockGCABridge` test double enables full unit testing of `GCAWebSocketDriver`, skills that use CODE_GEN tasks, and the LLM Gateway routing layer — without requiring a real VS Code instance.
- The race-free port-capture-at-detection pattern is preserved exactly, ensuring WebSocket connections are always made to the correct live port.
- Session isolation (new workspace per task) prevents GCA chat context from leaking between CIPHER tasks.

**Negative**:
- VS Code launch time (~5–15s) + GCA extension startup time (~3–10s) adds significant latency to every `CODE_GEN` task. This is a GCA architectural characteristic that cannot be optimised at the bridge layer.
- If the GCA VSIX extension changes its registry format or WebSocket protocol, this bridge must be updated. There is no formal API contract with the GCA extension.

**Neutral**:
- The `/tmp` workspace base is appropriate for Linux Docker containers. On Windows developer machines, `GCA_WORKSPACE_BASE` should be set to a path on a fast local drive (e.g., `C:\Temp`).

---

## 9. Related Decisions

- **ADR-0001**: LLM Gateway — `GCAWebSocketDriver` wraps this bridge and exposes it via the `LLMBackend` Protocol
- **ADR-0003**: POC Scope Lock — GCA WebSocket is the CODE_GEN backend for POC; all S1N1–S4 V-cycle tasks use this bridge
- **ADR-0005**: DevNex Agent A2A Wrapping — the DevNex orchestrator calls GCAWebSocketDriver via the LLM Gateway
- **CAR-001**: DevNex GCABridge — source of the 5-step pattern; DEBT-001 and DEBT-006 resolved by this ADR
