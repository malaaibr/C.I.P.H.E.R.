---
doc_id: AGENT-TOOL-001
title: Tool Agent (Tool Broker, AGT-008)
status: STUB
role: Generic MCP tool wrapper agent (planned)
layer: AAL
sources:
  - cipher/agents/tool_agent/README.md
  - cipher/agents/tool_agent/__init__.py
  - docs/CIPHER_archi.md (§6.9, §7.1, AGT-008 row)
  - docs/CIPHER_HLD.md  (§6.9 Tool Broker Agent)
  - docs/CIPHER_LLD.md  (agents inventory table)
  - docs/layers/AAL_HLD.md, docs/layers/AAL_LLD.md
---

# Tool Agent (AGT-008) — Agent LLD

> **Scope.** Per-agent doc for `cipher/agents/tool_agent/`. This is the
> AAL-side counterpart to the **Tool Broker / MCP Gateway** that the
> architecture places inside the TRF (Layer 4). The package is a STUB
> in the local MVP — this document captures the planned role only.

---

## §1 Role & Capabilities (Planned)

`tool_agent` is the agent-side facade for CIPHER's MCP tool fabric. Per
`CIPHER_archi.md` §6.9 / §7.1 and the AGT-008 row of `CIPHER_HLD.md`,
the Tool Broker mediates **all** external tool access for every other
CIPHER agent. The split between this AAL package and the TRF gateway is:

| Concern                                | Lives in      |
|----------------------------------------|---------------|
| MCP server processes (filesystem, git, web fetch, …) | **TRF** |
| MCP JSON-RPC gateway, sandboxing, retries            | **TRF** |
| A2A skill surface (`tool.call`, scoped tool catalog) | **AAL** (this package) |
| Per-agent scope enforcement (JWT + OPA)              | shared with GCL |
| Audit emission for every tool invocation             | shared with GCL |

Planned capabilities (T0 / system tier):

- Expose TRF's MCP servers as A2A skills consumable by DevNex, Compliance,
  Research, Planner, etc.
- Enforce per-agent **scopes** before forwarding any MCP call.
- Inject secrets at call time (agents never see raw credentials).
- Provide the **single audit point** for tool invocations (GCL audit
  journal hook).
- Apply sandboxing / rate-limit policy for execution-capable tools.

## §2 Current State — STUB

Two files only:

```
cipher/agents/tool_agent/
├── README.md       (10 lines, planned-responsibility summary)
└── __init__.py     (1 docstring: "Tool agent scaffold for the local MVP.")
```

No `CIPHERAgent` subclass, no skill registration, no MCP client wiring,
no tests. The AAL roll-up (`docs/layers/AAL_HLD.md` row "tool_agent/")
classifies it as **Stub — 2 files**.

## §3 Planned UC Mapping

Cross-cutting. Tool Agent is not tied to a single use case — it supports
**any UC where an agent needs to call an external tool**. Representative
consumers:

| UC                                   | Tool call examples                          |
|--------------------------------------|---------------------------------------------|
| DevNex V-cycle node execution        | `fs.read`, `fs.write`, `git.diff`, `git.commit` |
| Research Agent literature scan       | `web.fetch`, `web.search`                   |
| Compliance static-analysis gate      | `process.run` (linters), `fs.read`          |
| Traceability impact analysis         | `graph.query` (Memgraph MCP server)         |
| Doc Agent work-product rendering     | `template.render`, `fs.write`               |

## §4 Inputs / Outputs (Planned)

**Inputs** (A2A `TaskContract` to skill `tool.call`):
- `tool_id` — registered MCP tool identifier (e.g. `fs.read`).
- `arguments` — JSON-Schema-validated payload per the tool's manifest.
- `caller_agent` — propagated from A2A context (used for scope check).

**Outputs**:
- `result` — pass-through of MCP server response.
- `invocation_id` — UUID for cross-referencing the audit record in GCL.
- Structured errors for `scope_denied`, `rate_limited`, `tool_unavailable`,
  `sandbox_violation`.

## §5 Dependencies (Planned)

- **TRF** — MCP gateway + MCP tool servers (the actual capability layer).
- **ARE** — A2A skill registration via `SkillLoader`; receives tasks
  through the A2A FastAPI/SSE server.
- **GCL** — OPA policy decisions for per-agent scope, SQLite audit
  journal for tool-call records.
- **Core schemas** — `TaskContract`, `AgentCard`, tool-manifest schema.

## §6 Open Items

- **Not yet implemented.** No code beyond the package marker.
- TRF currently hosts the MCP server scaffolds; `tool_agent` is the
  agent-side **consumer** that is still missing. Until it exists, other
  agents either call MCP directly (bypassing scope/audit) or do not call
  tools at all.
- Promotion-order question (see `AAL_LLD.md` §"Stub promotion order"):
  Tool Agent is high-leverage because it unblocks tool use for every
  downstream agent; it is a strong candidate to follow Compliance and
  Memory Agent out of stub status.
- Decision needed on the **AAL/TRF boundary**: keep the gateway logic
  in TRF and let `tool_agent` be a thin A2A wrapper, or move scope
  enforcement up into AAL. `CIPHER_archi.md` §7.1 currently keeps the
  enforcement inside the TRF gateway.
- No tests, no agent card, no `__init__.py` exports yet.
