# GCL — High-Level Design

## 0. Frontmatter

| Field            | Value                                  |
|------------------|----------------------------------------|
| Doc ID           | HLD-GCL-001                            |
| Version          | 1.0                                    |
| ASPICE Process   | SUP.1 (Quality Assurance) + MAN.5 (Risk Management) |
| Layer            | GCL — Governance Control Layer (Layer 5) |
| Date             | 2026-05-17                             |
| Status           | DRAFT                                  |
| Implementation   | `cipher/gcl/`, `cipher/governance/`    |
| Upstream Sources | `docs/CIPHER_HLD.md` §3.5, `docs/CIPHER_LLD.md` §4, `docs/ASDLC.md` |

---

## 1. Purpose & Scope

The Governance Control Layer (GCL) provides cross-cutting governance services to every other CIPHER layer. It is the highest layer of the platform infrastructure and is responsible for three concerns:

1. **Policy enforcement** — every consequential action across the platform (tool calls in TRF, task submissions in ARE, graph writes in MKF, agent actions in AAL) is evaluated against a policy-as-code engine (Open Policy Agent / Rego) before it is allowed to execute.
2. **Audit journaling** — every executed action is recorded into an append-only SQLite audit log with the originating OpenTelemetry `trace_id` and `span_id`, providing an immutable evidence trail for compliance and forensic review.
3. **ASDLC gate enforcement** — the GCL is the enforcement point for the gates defined in `docs/ASDLC.md` (PROC-001). It mediates the transition between V-cycle phases so that no irreversible action proceeds without the configured authorization and (where required) human approval.

**Out of scope for MVP / current implementation:** Cryptographic agent identity (Ed25519), HITL approval workflow signing, domain pack loader, immutability via signatures. These are described in the HLD as future work but are **not present** in the current code; the current implementation is a thin POC of OPA + SQLite. Mark these as stubs/future in §7.

## 2. Position in the 7-Layer Architecture

GCL sits at Layer 5 of the 7-layer model defined in `CLAUDE.md` and `docs/CIPHER_HLD.md`:

```
+------------------------------------------------------+
|  AAL  — Agents (DevNex + 9 stubs)                    |
|  ARE  — Agent Runtime Environment (A2A, SkillLoader) |
|  GCL  — Governance Control Layer  *** this doc ***   |
|  TRF  — Tool & Resource Fabric (LLM Gateway, MCP)    |
|  MKF  — Memory & Knowledge Fabric                    |
|  PKL  — Platform Kernel (NATS, LangGraph)            |
|  DRS  — Deployment Runtime Substrate                 |
+------------------------------------------------------+
```

GCL sits **above** DRS, MKF, PKL, and TRF, and **beneath** the orchestration / agent layers (ARE, AAL). The architectural property that distinguishes GCL from a normal stacked layer is that **it cross-cuts every other layer**: an action originating anywhere in the stack routes through GCL for `policy.evaluate(...)` before execution and `audit.record(...)` after execution. The Layer Interaction Matrix in `CIPHER_HLD.md` confirms GCL has read access to all governed layers and write access to its own audit journal.

The OPA decision engine itself is operated as an OPA sidecar container provisioned by DRS (`opa:0.62.1` in `deploy/local/docker-compose.yml`); the GCL Python code is the in-process client that consults that sidecar.

## 3. External Interfaces

### 3.1 OPA HTTP API (consumed)

- Endpoint: `OPA_URL` env var, default `http://localhost:8181`.
- `GET /health` — used by `OpaClient.health_check()` for readiness probing.
- `POST /v1/data/{policy_path}` — used by `OpaClient.evaluate()`. Request body `{"input": {...}}`. Response shape `{"result": {"allow": bool, ...}}`.
- Default policy package: `cipher.authz` (mounted from `deploy/local/policies/`).

### 3.2 Audit Query API (in-process)

- Python-level interface exposed by `AuditJournal`:
  - `async record(agent_id, action, detail, trace_id, span_id) -> int`
  - `query(agent_id=None, limit=100) -> list[dict]`
- No HTTP surface today; consumers import `AuditJournal` directly. A FastAPI read API is described in `CIPHER_HLD.md` as future work.

### 3.3 Gate Decision JSON Contract

The gate decision contract returned by `OpaClient.evaluate()` is currently reduced to a single boolean (`allow`), extracted from `result.allow`. The richer decision schema defined in HLD (signed decision, obligation list, reason codes) is **not yet implemented**. See §7.

## 4. Internal Decomposition

| Sub-module                | Implementation                              | Status              |
|---------------------------|---------------------------------------------|---------------------|
| Policy Engine client      | `cipher/gcl/policy_engine/opa_client.py`    | Implemented (POC)   |
| Audit Journal             | `cipher/gcl/audit_journal/journal.py`       | Implemented (POC)   |
| Audit DB schema factory   | `cipher/core/adapters/sqlite_factory.py::create_audit_db` | Implemented |
| OPA policy bundle (POC)   | `deploy/local/policies/poc_allow_all.rego`  | Permissive stub     |
| Governance scaffold       | `cipher/governance/`, `cipher/governance/policies/` | Empty scaffold (README only) |
| HITL Gate Manager         | —                                           | **Not yet present** |
| Identity Manager (JWT/Ed25519) | —                                      | **Not yet present** |
| Domain Pack Loader        | —                                           | **Not yet present** |

`cipher/governance/` exists as a placeholder for future policy definitions and approval gates, but currently contains only documentation stubs.

## 5. Dependencies

| Depends on | Why                                                                |
|------------|---------------------------------------------------------------------|
| DRS        | OPA container, SQLite WAL data directory (`deploy/local/data/sqlite`) |
| `httpx`    | Async HTTP client used by `OpaClient`                              |
| `sqlite3` (stdlib) | Audit journal backing store                                 |
| `cipher.core.otel` | `@traced` decorator on `AuditJournal.record` to attach span context |
| `cipher.core.adapters.sqlite_factory` | Creates the `audit_log` table + WAL pragmas |
| `ASDLC.md` PROC-001 | Source of ASDLC gates that GCL is expected to enforce      |

Reverse dependencies (callers): the orchestrator (`cipher/core/orchestrator.py`), DevNex orchestrator, ARE skill executors, and the LLM Gateway are all designed to call GCL before consequential actions. Current call-sites are limited — the POC primarily exercises GCL through the e2e test (`tests/e2e/test_poc_spine.py`) rather than every action path.

## 6. Quality Attributes

| Attribute             | Target / Current State                                                  |
|-----------------------|-------------------------------------------------------------------------|
| Audit immutability    | Append-only schema (no `UPDATE`/`DELETE` SQL paths in `AuditJournal`). Cryptographic signing (Ed25519) **not yet implemented** — relies on filesystem and SQLite WAL guarantees only. |
| OPA decision latency  | OPA is a local sidecar; the current `OpaClient.evaluate()` uses a 5-second `httpx` timeout. Sub-10 ms typical local round-trip; no explicit SLO codified yet. |
| Gate enforcement determinism | Determined by Rego evaluation. POC bundle (`poc_allow_all.rego`) is trivially deterministic (`default allow := true`). MVP-grade per-agent policies are TBD. |
| Observability         | Every audit record is wrapped in an OTel span (`audit.record`, `layer=gcl`) and stores `trace_id`/`span_id` for correlation with the broader trace. |
| Availability of OPA   | `OpaClient.health_check()` returns `False` on `ConnectError`/`TimeoutException`; consumers can fail-closed. There is no in-process fallback policy yet. |
| Storage growth        | No retention/rotation policy in code; index on `agent_id` and `timestamp` are created but pruning is a future concern. |

## 7. Open Questions / Future Work

1. **Restrictive policies** — `poc_allow_all.rego` allows everything. MVP must replace this with per-agent, per-action authorization bundles. Open question: are bundles delivered statically (file mount) or via OPA Bundle API?
2. **Decision schema** — Today `evaluate()` collapses to a bool. The HLD calls for a signed decision object with obligations and reason codes. The Python data class for `PolicyDecision` is not defined.
3. **Audit signing** — `AuditRecord` is not cryptographically signed; the HLD references Ed25519 signatures. No keypair management exists in code.
4. **HITL Gate Manager** — Suspending a LangGraph workflow on a `cipher.gate.pending` CloudEvent and resuming on signed approval is described in the HLD but not implemented.
5. **Identity Manager** — JWT issuance/validation and agent Ed25519 keypair generation are absent.
6. **Domain Pack Loader** — `cipher/governance/domain_packs/{pack_id}/` directory layout is described but not present.
7. **ASDLC gate wiring** — `docs/ASDLC.md` PROC-001 gates are not yet exposed through a GCL API; current gates in DevNex are enforced inline via `threading.Event` and GUI dialogs, bypassing GCL.
8. **Audit read API** — No HTTP endpoint yet; query is in-process only.
