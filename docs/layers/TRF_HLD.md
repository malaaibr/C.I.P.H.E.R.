# TRF — High-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | HLD-TRF-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Layer | TRF — Tool & Resource Fabric (LLM Gateway + MCP servers) |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dirs | `cipher/trf/`, `cipher/tools/` |
| Authoritative sources | `cipher/trf/mcp_servers/llm_gateway/*.py`, `docs/CIPHER_HLD.md` §3.4, `docs/CIPHER_LLD.md` §7, `docs/adr/ADR-0001-llm-gateway.md`, `docs/adr/ADR-0002-gca-websocket-bridge.md` |

---

## §1 Purpose & Scope

The Tool & Resource Fabric (TRF) is the layer through which every CIPHER agent
reaches an external capability — an LLM, a filesystem, a Git repository, a
VectorCAST CLI run, or a DOORS export. Its architectural role is identical to
AUTOSAR's ECU Abstraction Layer (`CIPHER_HLD.md` line 124): it hides which
physical backend (`qwen2.5-coder:1.5b` on Ollama vs. GitHub Copilot Agent via
VS Code) is fulfilling a call, exposing only a single Protocol surface.

In the POC, TRF materialises as **one running MCP server** — the LLM Gateway —
plus four planned tool MCP scaffolds. The LLM Gateway is an in-process FastAPI
app bound on `127.0.0.1:8200` (started as a daemon thread by `run_poc.py` line 53).
It exposes a single `POST /v1/complete` endpoint that takes a `TaskClass` and
returns a uniform `LLMResponse` regardless of which backend served the request.

**In scope (this doc).**
- The LLM Gateway FastAPI service (`cipher/trf/mcp_servers/llm_gateway/`)
- The `TaskClassRouter` and `LLMBackend` Protocol contract (ADR-0001 §4)
- The `OllamaDriver` (local) and `GCAHttpDriver` (HTTP shim to the GCA bridge)
- Routing semantics and fallback policy
- The planned MCP server scaffolds under `cipher/tools/`

**Out of scope.**
- The GCA WebSocket bridge implementation itself — see ADR-0002 and the DevNex
  bridge in `cipher/agents/devnex_assistant/bridge/`. TRF only consumes it via
  an HTTP shim presumed to be reachable at `GCA_BRIDGE_URL`.
- The MKF retrieval API and the GCL policy/audit calls that wrap tool calls in
  the full design — neither is wired into the POC gateway today.

---

## §2 Position in 7-Layer Architecture

Per `CIPHER_HLD.md` §1.1 (line 169) and the Layer Interaction Matrix (line 266),
TRF sits between MKF (memory) and GCL (governance) in the upward call chain, and
is invoked from AAL agents through ARE — never called directly from AAL in the
full design. In the POC the agent-side call path is shorter: `DevNexOrchestrator`
nodes call the LLM Gateway HTTP endpoint directly (no Tool Broker, no per-call
policy check yet — see §7).

```
AAL (DevNex)
  └── HTTP POST :8200 /v1/complete  ──► TRF: LLM Gateway
                                          ├─► OllamaDriver  ──► DRS: Ollama :11434
                                          └─► GCAHttpDriver ──► GCA bridge :37778
```

TRF depends downward on:
- **DRS** for the Ollama process at `:11434` (an out-of-Compose local daemon in
  the POC — see `CIPHER_LLD.md` line 111).
- **GCA bridge** (a VS Code-side process) for `CODE_GEN`, treated as an external
  resource per ADR-0002.

---

## §3 External Interfaces

### 3.1 Gateway HTTP API (`:8200`)

Defined in `cipher/trf/mcp_servers/llm_gateway/server.py`.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | — | `{"status":"ok","service":"llm-gateway"}` |
| POST | `/v1/complete` | `CompletionRequest{prompt, task_class, context}` | `CompletionResponse{text, backend_id, task_class, duration_ms, prompt_tokens?, completion_tokens?}` |

`task_class` is the enum `cipher.core.schemas.task_contract.TaskClass`. The POC
recognises `TRIAGE`, `PLAN`, and `CODE_GEN` (router table in `router.py` line 14).
Unknown values raise `KeyError` inside the router (no default route — stub).

Errors: a backend failure surfaces as HTTP `503` with the
`LLMUnavailableError` message as `detail` (`server.py` line 42).

### 3.2 MCP Server Endpoints

The four MCP servers under `cipher/tools/` are **scaffolds only**. Each
sub-directory contains a single `README.md` describing the planned wrapper
(Git, sandboxed FS, ReqIF/DOORS, VectorCAST CLI, LLM gateway façade). No
server process, transport, or tool schema is implemented today.

### 3.3 TaskClass Routing Protocol

Each call carries one of the `TaskClass` enum values. The routing rule
(`router.py` line 14) is a static dict — see TRF_LLD §2. Per ADR-0001 §2
("POC determinism") the design intent is *one backend per class with no
auto-fallover*; the code currently implements a single fallback to Ollama
(see `router.py` lines 41–46), which deviates from the ADR and is flagged
in §7.

---

## §4 Internal Decomposition

```
cipher/trf/
└── mcp_servers/
    └── llm_gateway/
        ├── server.py          FastAPI app, /health + /v1/complete
        ├── router.py          TaskClassRouter + module-level singleton
        ├── protocol.py        LLMBackend Protocol, LLMResponse, LLMUnavailableError
        ├── ollama_driver.py   OllamaDriver — HTTP to :11434/api/generate
        └── gca_http_driver.py GCAHttpDriver — HTTP to :37778/v1/generate

cipher/tools/
├── llm_gateway/    (README only — planned façade onto the bridge)
├── fs_mcp/         (README only — planned sandboxed filesystem)
├── git_mcp/        (README only — planned git wrapper)
├── reqif_mcp/      (README only — planned ReqIF/DOORS export)
└── vectorcast_mcp/ (README only — planned VectorCAST CLI wrapper)
```

Component roles:

- **Gateway** (`server.py`) — single HTTP entry. Thin: builds a router via the
  `get_router()` singleton and forwards.
- **TaskClassRouter** (`router.py`) — lazy-instantiates the driver for each
  task class; checks `is_available()` before dispatching; falls back to a
  fresh `OllamaDriver` if the primary is down.
- **Drivers** (`ollama_driver.py`, `gca_http_driver.py`) — each conforms to the
  `LLMBackend` Protocol (`protocol.py` line 31). Both are decorated with
  `cipher.core.otel.traced` so every call emits an OTel span.
- **Tool MCP scaffolds** — placeholders pending implementation.

---

## §5 Dependencies

| Direction | Layer / Component | Used For | Source |
|---|---|---|---|
| Downward | DRS — Ollama daemon `:11434` | Local LLM inference | `CIPHER_LLD.md` line 111 |
| Downward | GCA WebSocket bridge `:37778` (HTTP shim) | `CODE_GEN` completions | ADR-0002, `gca_http_driver.py` line 18 |
| Lateral  | `cipher.core.otel.traced` | Span emission per backend call | `ollama_driver.py` line 10 |
| Lateral  | `cipher.core.schemas.task_contract.TaskClass` | Routing key | `router.py` line 5 |
| Upward (consumers) | AAL — `DevNexOrchestrator` retry wrapper | All LLM calls | `CIPHER_LLD.md` lines 1333–1336 |

Not yet wired (HLD-level contracts only, see ADR-0001 §4 and `CIPHER_HLD.md`
line 1190 "Skip-layer rule"):
- **GCL** — every tool call should be policy-gated and audited; gateway does
  not yet call OPA or write to the audit journal.
- **ARE Tool Broker** — agents should call TRF *through* the broker for scope
  injection; today DevNex calls the gateway HTTP endpoint directly.

---

## §6 Quality Attributes

| Attribute | Target | Status |
|---|---|---|
| Routing latency overhead | ≤ 5 ms p95 above raw driver call | not measured |
| Backend availability check | < 5 s timeout, non-fatal on failure | enforced (`ollama_driver.py` line 27, `gca_http_driver.py` line 26) |
| Completion timeout — Ollama | 120 s | enforced (`ollama_driver.py` line 37) |
| Completion timeout — GCA | 300 s | enforced (`gca_http_driver.py` line 36) |
| Retry budget — GCA path | `max_gca_retries: 3` (default per `ruleset.yaml` line 29) | enforced **in caller** (`DevNexOrchestrator._invoke_with_retry`), **not** in the gateway |
| Observability | OTel span per backend call w/ `layer=trf`, `backend=<id>` | enforced via `@traced` |
| Fallback policy | ADR-0001 §2: none in POC; code currently falls back primary → Ollama | **deviation** — see §7 |

---

## §7 Open Questions

1. **Fallback policy mismatch with ADR-0001.** Router currently silently
   falls back to a fresh `OllamaDriver` when the primary backend is
   unavailable (`router.py` lines 41–46). ADR-0001 §2 mandates "no automatic
   fallover" for POC determinism. Either the code or the ADR must move.
2. **PLAN backend stub.** ADR-0001 routes `PLAN` to Gemini CLI; the code
   routes it to `OllamaDriver` (`router.py` line 16) with an inline `# stub`
   comment. Gemini CLI driver is not implemented.
3. **GCA driver is HTTP, not WebSocket.** `gca_http_driver.py` calls an HTTP
   shim at `:37778`. ADR-0002 specifies a WebSocket bridge with the 5-step
   isolation pattern; the shim's location and lifecycle are not documented
   in this repo.
4. **No GCL/ARE integration.** Tool Broker, scope injection, and audit
   recording specified in `CIPHER_HLD.md` §3.4 are absent in POC.
5. **Tool MCP servers unimplemented.** All five `cipher/tools/*` directories
   contain README stubs only.
6. **Singleton router and per-task-class driver caching.** `_drivers` is
   keyed by `task_class.value`, so a driver outage caches indefinitely; no
   periodic re-probe. Acceptable for POC; revisit before multi-tenant use.
