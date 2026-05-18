---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# TRF — Low-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | LLD-TRF-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.3 (Software Detailed Design) |
| Layer | TRF — Tool & Resource Fabric |
| Date | 2026-05-17 |
| Status | DRAFT |
| HLD reference | `docs/layers/TRF_HLD.md` (HLD-TRF-001) |
| Implementation dirs | `cipher/trf/`, `cipher/tools/` |
| Authoritative sources | `cipher/trf/mcp_servers/llm_gateway/server.py`, `router.py`, `protocol.py`, `ollama_driver.py`, `gca_http_driver.py`, `tests/unit/test_llm_gateway.py`, `docs/adr/ADR-0001-llm-gateway.md`, `docs/adr/ADR-0002-gca-websocket-bridge.md` |

---

## §1 Module Inventory

| File | Lines | Role | Key Symbols |
|---|---|---|---|
| `cipher/trf/__init__.py` | 4 | Package marker | — |
| `cipher/trf/mcp_servers/__init__.py` | 4 | Package marker | — |
| `cipher/trf/mcp_servers/llm_gateway/__init__.py` | 12 | Public re-exports | `LLMBackend`, `LLMResponse`, `LLMUnavailableError` |
| `cipher/trf/mcp_servers/llm_gateway/protocol.py` | 40 | Backend Protocol + DTOs | `LLMBackend`, `LLMResponse` (pydantic), `LLMUnavailableError` |
| `cipher/trf/mcp_servers/llm_gateway/ollama_driver.py` | 60 | Ollama HTTP driver | `OllamaDriver.complete`, `OllamaDriver.is_available`, `backend_id="ollama"` |
| `cipher/trf/mcp_servers/llm_gateway/gca_http_driver.py` | 57 | GCA bridge HTTP driver | `GCAHttpDriver.complete`, `GCAHttpDriver.is_available`, `backend_id="gca_http"` |
| `cipher/trf/mcp_servers/llm_gateway/router.py` | 55 | TaskClass → driver dispatch | `TaskClassRouter.route`, `_ROUTING_TABLE`, `get_router()` |
| `cipher/trf/mcp_servers/llm_gateway/server.py` | 52 | FastAPI entry | `app`, `CompletionRequest`, `CompletionResponse`, `complete()`, `health()` |
| `cipher/tools/__init__.py` | — | Package marker | — |
| `cipher/tools/llm_gateway/README.md` | 4 | Planned façade (stub) | — |
| `cipher/tools/fs_mcp/README.md` | 4 | Planned sandboxed FS (stub) | — |
| `cipher/tools/git_mcp/README.md` | 4 | Planned git MCP (stub) | — |
| `cipher/tools/reqif_mcp/README.md` | 4 | Planned ReqIF/DOORS (stub) | — |
| `cipher/tools/vectorcast_mcp/README.md` | 4 | Planned VectorCAST CLI (stub) | — |

---

## §2 Routing Logic — TaskClassRouter

### 2.1 Routing table

`router.py` line 14:

```python
_ROUTING_TABLE: dict[TaskClass, type] = {
    TaskClass.TRIAGE:   OllamaDriver,
    TaskClass.PLAN:     OllamaDriver,   # Gemini CLI stub — uses Ollama for POC
    TaskClass.CODE_GEN: GCAHttpDriver,
}
```

The table is a module-level constant and is **not** runtime-configurable. Adding
a new task class requires a code change. `_ROUTING_TABLE` maps to driver
*classes*; instances are created lazily on first use and cached in
`self._drivers` keyed by `task_class.value`.

### 2.2 Dispatch sequence

`TaskClassRouter.route(prompt, task_class, context)` (`router.py` lines 36–47):

1. Resolve / lazily construct the primary driver via `_get_driver`.
2. Call `driver.is_available()`. On `True`, dispatch `driver.complete(...)`.
3. On `False`, construct a fresh `OllamaDriver` and try it as fallback.
4. If the fallback is also unavailable, raise
   `LLMUnavailableError(driver.backend_id, "Backend not available for <task_class>")`.

### 2.3 Singleton

`get_router()` (lines 50–54) returns a module-level singleton. The Gateway
endpoint always uses this instance. There is no teardown / reset; tests use
the constructor directly and inject mock drivers into `_drivers`.

### 2.4 Conformance vs. ADR-0001

ADR-0001 §2 forbids automatic fallover in POC for reproducibility. The
fallback branch above violates that. Either the ADR will be relaxed or the
fallback branch must be removed (see TRF_HLD §7 Open Question 1).

---

## §3 Backend Drivers

### 3.1 `LLMBackend` Protocol (`protocol.py`)

```python
@runtime_checkable
class LLMBackend(Protocol):
    async def complete(self, prompt: str, context: dict) -> LLMResponse: ...
    async def is_available(self) -> bool: ...
    @property
    def backend_id(self) -> str: ...
```

`LLMResponse` fields: `text`, `backend_id`, `task_class`, `duration_ms`,
optional `prompt_tokens`, `completion_tokens`, `instance_id` (GCA-only).
Note: `task_class` is `str` here, **not** the `TaskClass` enum. Drivers set it
to a hard-coded literal (`"TRIAGE"` for Ollama line 55, `"CODE_GEN"` for GCA
line 53) — this is a known stub (see §7 TODO 1).

### 3.2 `OllamaDriver`

| Aspect | Value | Source |
|---|---|---|
| `backend_id` | `"ollama"` | `ollama_driver.py` line 23 |
| Base URL | `OLLAMA_BASE_URL` env or `http://localhost:11434` | line 18 |
| Model | `OLLAMA_MODEL` env or `qwen2.5-coder:1.5b` | line 19 |
| Per-call model override | `context["model"]` | line 41 |
| Availability probe | `GET /api/tags`, 5 s timeout, expects 200 | lines 26–31 |
| Completion call | `POST /api/generate`, body `{model, prompt, stream:false}`, 120 s timeout | lines 37–46 |
| Span | `@traced("ollama.complete", attributes={"layer":"trf","backend":"ollama"})` | line 33 |
| Token accounting | `prompt_eval_count` / `eval_count` from response | lines 57–58 |
| Failure → exception | `httpx.ConnectError` or `TimeoutException` → `LLMUnavailableError("ollama", ...)` | lines 47–48 |

`.env.example` overrides the default model to `qwen2.5-coder:7b` (line 6); the
driver default disagrees. The repo's CLAUDE.md "How to Run" pulls the 1.5b
variant matching the driver.

### 3.3 `GCAHttpDriver`

| Aspect | Value | Source |
|---|---|---|
| `backend_id` | `"gca_http"` | `gca_http_driver.py` line 22 |
| Bridge URL | `GCA_BRIDGE_URL` env or `http://127.0.0.1:37778` | line 18 |
| Availability probe | `GET /health`, 5 s timeout | lines 25–30 |
| Completion call | `POST /v1/generate`, body `{prompt, workspace_hint}`, 300 s timeout | lines 36–44 |
| Span | `@traced("gca.complete", attributes={"layer":"trf","backend":"gca_http"})` | line 32 |
| Response text key | `text` (fallback `response`) | line 51 |
| `instance_id` propagation | from response body | line 55 |
| Failure → exception | `httpx.ConnectError` or `TimeoutException` → `LLMUnavailableError("gca_http", ...)` | lines 45–46 |

The driver assumes an HTTP-fronted shim already exists at `:37778`. The
ADR-0002 WebSocket bridge with the 5-step isolation pattern is implemented in
`cipher/agents/devnex_assistant/bridge/` (DevNex-local), not as a TRF process.
Wiring between the two is not present in this repo — this is a stub
(see §7 TODO 2).

### 3.4 Driver-level retry

There is **no** retry inside either driver. The `max_gca_retries: 3` budget
(see §5) is honoured by `DevNexOrchestrator._invoke_with_retry`
(`cipher/agents/devnex_assistant/core/orchestrator.py` line 143), which calls
the gateway and retries on failure. From the gateway's perspective each call
is single-shot.

---

## §4 MCP Server Layout

`cipher/tools/` is the planned home for tool-side MCP servers — currently
README-only scaffolds.

| Directory | Planned Capability | Notes |
|---|---|---|
| `cipher/tools/llm_gateway/` | MCP façade onto the existing FastAPI gateway so non-HTTP MCP clients can call `llm.complete` as an MCP tool | README states "initially routed through the existing DevNex bridge" |
| `cipher/tools/fs_mcp/` | Sandboxed FS reads/writes for agents | "Planned" |
| `cipher/tools/git_mcp/` | Local git wrapper exposed via MCP | "Planned" |
| `cipher/tools/reqif_mcp/` | ReqIF / DOORS export | "Planned" |
| `cipher/tools/vectorcast_mcp/` | VectorCAST CLI driver | "Planned" |

None has a `server.py`, transport binding, tool schema, or test. The MCP
transport choice (stdio vs. HTTP-SSE) is not yet decided. The CIPHER_LLD §7
status table (line 737–741) lists `llm_gateway/` as "Stub".

`cipher/trf/mcp_servers/llm_gateway/` is colocated under TRF rather than
under `cipher/tools/`; the duplication between `cipher/trf/mcp_servers/
llm_gateway` (working FastAPI service) and `cipher/tools/llm_gateway`
(README stub) is intentional per the README ("planned model-access boundary
for audited LLM calls"). Consolidation is deferred.

---

## §5 Configuration

### 5.1 Environment variables

Read directly via `os.environ.get`:

| Variable | Default | Used by | Notes |
|---|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `OllamaDriver.__init__` | Sandbox or remote Ollama |
| `OLLAMA_MODEL` | `qwen2.5-coder:1.5b` | `OllamaDriver.__init__` | `.env.example` overrides to `:7b` |
| `GCA_BRIDGE_URL` | `http://127.0.0.1:37778` | `GCAHttpDriver.__init__` | Same default appears in `cipher/core/substrate/compose_driver.py` line 84 |

There is no centralised settings object yet; each driver reads env at
construction time.

### 5.2 `ruleset.yaml`

`cipher/agents/devnex_assistant/configs/ruleset.yaml` carries the call-side
retry budget consumed by AAL, not by TRF itself:

```yaml
# Maximum GCA retry attempts (F-002)
max_gca_retries: 3
```

`config.json` `max_gca_retries` overrides the YAML at the
`DevNexOrchestrator` layer (`docs/ASDLC.md` line 138, `docs/DEMO_RUNBOOK_DIO.md`
line 228). The TRF gateway has no knowledge of this value — see TODO 3.

### 5.3 Routing rules

Routing is encoded in Python (`_ROUTING_TABLE` in `router.py`). There is no
external YAML/JSON ruleset for backend selection in the POC. ADR-0001 §4.4
sketches such a config but it is not implemented.

### 5.4 Port binding

Gateway listens on `127.0.0.1:8200` — bound in `run_poc.py` line 28
(`GATEWAY_PORT = 8200`) and verified by the splash log line 79
("LLM Gateway online — :8200"). The gateway itself does not declare its port.

---

## §6 Test Coverage

Single test module: `tests/unit/test_llm_gateway.py` (T-010 .. T-013).

| Test class | What it covers | Approach |
|---|---|---|
| `TestProtocol` | `LLMBackend` runtime conformance for both drivers; `LLMResponse` JSON round-trip; `LLMUnavailableError` carries backend name | Direct construction |
| `TestOllamaDriver` | `is_available()` happy path (HTTP 200); `complete()` returns parsed text + token counts | `httpx.AsyncClient` mocked with `AsyncMock` |
| `TestGCAHttpDriver` | `complete()` returns text + `instance_id` | `httpx.AsyncClient` mocked |
| `TestTaskClassRouter` | `TRIAGE` routed to ollama; `CODE_GEN` routed to gca_http; raises `LLMUnavailableError` when primary unavailable | Driver objects injected directly into `router._drivers` |

Gaps:
- No test exercises the fallback branch (`router.py` lines 41–46).
- No test exercises driver failure paths (`httpx.ConnectError`,
  `httpx.TimeoutException`).
- No FastAPI-level test (`server.py` `complete()` and `/health` are
  uncovered).
- No tests under `cipher/tools/*` — none implemented.

Async tests rely on `pytest.mark.asyncio` (configured project-wide).

---

## §7 TODOs

1. **`task_class` literal in driver responses.** Both drivers set
   `LLMResponse.task_class` to a hard-coded string (`"TRIAGE"` /
   `"CODE_GEN"`). It should be threaded through from the router so PLAN
   responses don't masquerade as TRIAGE on the Ollama path.
2. **GCA WebSocket bridge wiring.** Replace `GCAHttpDriver` HTTP shim (or
   document/host the shim) with a real adapter to the ADR-0002 5-step bridge
   currently in `cipher/agents/devnex_assistant/bridge/`. Decide whether the
   bridge is a TRF-owned process or stays under AAL.
3. **Surface `max_gca_retries` to TRF.** Today the retry budget lives in
   `DevNexOrchestrator`. Either move retries into `GCAHttpDriver` or document
   the boundary explicitly.
4. **Implement Gemini CLI driver.** `_ROUTING_TABLE[TaskClass.PLAN]` is
   marked stub in `router.py` line 16; create `gemini_cli_driver.py` per
   ADR-0001.
5. **Fallback policy decision.** Reconcile `router.py` lines 41–46 with
   ADR-0001 §2 — either drop the fallback or amend the ADR.
6. **Periodic re-probe.** Driver instances are cached for the process
   lifetime; an outage caches the cached driver indefinitely. Add TTL or
   on-call re-check.
7. **GCL/ARE integration.** Wire `policy.evaluate()` and `audit.record()`
   into `server.complete()` per `CIPHER_HLD.md` §3.4 lines 770–773.
8. **Build out `cipher/tools/*` MCP servers.** Start with `fs_mcp` and
   `git_mcp` to unblock non-DevNex agents.
9. **Consolidate `cipher/tools/llm_gateway` and `cipher/trf/mcp_servers/
   llm_gateway`.** Two parallel locations for the same concept.
10. **Externalise routing rules.** Move `_ROUTING_TABLE` to a YAML loaded at
    boot so QA can edit task-class → backend mappings without code changes
    (ADR-0001 §4.4 intent).
