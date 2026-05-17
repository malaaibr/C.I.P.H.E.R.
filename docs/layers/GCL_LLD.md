# GCL — Low-Level Design

## 0. Frontmatter

| Field            | Value                                  |
|------------------|----------------------------------------|
| Doc ID           | LLD-GCL-001                            |
| Version          | 1.0                                    |
| ASPICE Process   | SUP.1 (Quality Assurance) + MAN.5 (Risk Management) |
| Layer            | GCL — Governance Control Layer (Layer 5) |
| Date             | 2026-05-17                             |
| Status           | DRAFT                                  |
| Implementation   | `cipher/gcl/`, `cipher/governance/`    |
| Companion HLD    | `docs/layers/GCL_HLD.md` (HLD-GCL-001) |

---

## 1. Module Inventory

### 1.1 `cipher/gcl/` — Implemented POC modules

| File                                              | LOC* | Responsibility                                                                 | Status |
|---------------------------------------------------|------|--------------------------------------------------------------------------------|--------|
| `cipher/gcl/__init__.py`                          | 3    | Package marker; docstring "Governance, Compliance & Lifecycle"                | Stub   |
| `cipher/gcl/policy_engine/__init__.py`            | 3    | Sub-package marker                                                            | Stub   |
| `cipher/gcl/policy_engine/opa_client.py`          | 36   | `OpaClient` — async OPA REST client (`health_check`, `evaluate`)              | Implemented |
| `cipher/gcl/audit_journal/__init__.py`            | 3    | Sub-package marker                                                            | Stub   |
| `cipher/gcl/audit_journal/journal.py`             | 49   | `AuditJournal` — append-only SQLite audit log (`record`, `query`)             | Implemented |

\*Approximate line counts.

### 1.2 `cipher/governance/` — Scaffold only

| File                                       | Responsibility                                | Status      |
|--------------------------------------------|-----------------------------------------------|-------------|
| `cipher/governance/__init__.py`            | Package docstring only                        | Empty stub  |
| `cipher/governance/README.md`              | "Policy, approval, and audit-governance boundary for the local MVP." | Placeholder |
| `cipher/governance/policies/README.md`     | Placeholder describing agent scopes, approval gates, tool authz rules, compliance blocking | Placeholder |

No Python code exists under `cipher/governance/` yet. The directory is reserved for the HITL Gate Manager, Identity Manager, Domain Pack Loader, and policy authoring helpers described in the HLD.

### 1.3 Related (outside `cipher/gcl/` but load-bearing)

| File                                              | Relevance                                                              |
|---------------------------------------------------|-----------------------------------------------------------------------|
| `cipher/core/adapters/sqlite_factory.py`          | `create_audit_db()` creates the WAL-mode `audit.db` and `audit_log` schema consumed by `AuditJournal`. |
| `cipher/core/otel/tracing.py`                     | `@traced` decorator applied to `AuditJournal.record`.                 |
| `deploy/local/policies/poc_allow_all.rego`        | Active Rego bundle (POC permissive policy in package `cipher.authz`). |
| `deploy/local/docker-compose.yml`                 | Mounts the OPA sidecar (`opa:0.62.1`) on port 8181.                    |
| `tests/unit/test_sprint2.py`                      | Unit tests for `OpaClient` and `AuditJournal`.                         |
| `tests/e2e/test_poc_spine.py`                     | E2E POC exit-criteria tests for both submodules.                       |

## 2. Key Data Structures

### 2.1 `AuditRecord` (implicit — SQL row schema)

There is **no Python `AuditRecord` dataclass** in the code; records are passed as positional args to `AuditJournal.record` and read back as `dict`s in `query`. The implicit schema is the `audit_log` table.

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
    agent_id    TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    trace_id    TEXT,
    span_id     TEXT
);
CREATE INDEX idx_audit_agent ON audit_log(agent_id);
CREATE INDEX idx_audit_ts    ON audit_log(timestamp);
```

Source: `cipher/core/adapters/sqlite_factory.py::create_audit_db`.

The `query()` method reconstructs each row as:
```python
{
    "id": int, "timestamp": str, "agent_id": str,
    "action": str, "detail_json": str (JSON-encoded),
    "trace_id": str | None, "span_id": str | None,
}
```

### 2.2 `PolicyDecision` — **not implemented**

The HLD describes a signed `PolicyDecision` object (decision, obligations, reason codes, signature). In code, `OpaClient.evaluate()` returns a bare `bool`:

```python
async def evaluate(self, policy_path: str = "cipher/authz",
                   input_data: dict | None = None) -> bool:
    ...
    return result.get("result", {}).get("allow", False)
```

A richer typed schema is a TODO (see §7).

## 3. OPA Integration

### 3.1 Client construction

```python
# cipher/gcl/policy_engine/opa_client.py
class OpaClient:
    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.environ.get("OPA_URL", "http://localhost:8181")
```

Notes:
- No shared `httpx.AsyncClient` is reused; a new client is constructed inside each call via `async with httpx.AsyncClient(timeout=5.0) as client`. The LLD prose in `CIPHER_LLD.md` shows a long-lived client; the actual code does **not** match that — flagged as a minor divergence.

### 3.2 Health check

```
GET {OPA_URL}/health
→ 200  ⇒ True
→ any other / ConnectError / TimeoutException ⇒ False
```

### 3.3 Decision evaluation

```
POST {OPA_URL}/v1/data/{policy_path}
Content-Type: application/json
Body: {"input": <input_data>}

Response (200): {"result": {"allow": true|false, ...}}
Response (non-200): treated as deny (return False)
```

- `policy_path` defaults to `cipher/authz` (matches the Rego `package cipher.authz` declared in `poc_allow_all.rego`).
- Only the `allow` key is consumed; any other fields in `result` are ignored.

### 3.4 Active Rego bundle

```rego
# deploy/local/policies/poc_allow_all.rego
package cipher.authz
default allow := true
```

This is mounted read-only into the OPA container via `deploy/local/docker-compose.yml`. Per LLD §2 of the upstream doc, the bundle directory is `./policies` and the container is `opa:0.62.1`.

## 4. Audit Journal

### 4.1 Write path

```python
@traced(name="audit.record", attributes={"layer": "gcl"})
async def record(self, agent_id, action, detail=None,
                 trace_id=None, span_id=None) -> int:
    cursor = self._conn.execute(
        "INSERT INTO audit_log "
        "(agent_id, action, detail_json, trace_id, span_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (agent_id, action, json.dumps(detail or {}), trace_id, span_id),
    )
    self._conn.commit()
    return cursor.lastrowid
```

Behavioural notes:
- The function is declared `async` but performs synchronous `sqlite3` I/O. There is no thread-pool executor — under heavy concurrency this will block the event loop. Flagged as a TODO.
- `detail` is serialised with `json.dumps`; non-JSON-serialisable values will raise `TypeError`.
- `timestamp` is set by SQLite's `datetime('now')` default (UTC, second resolution).

### 4.2 Read path

```python
def query(self, agent_id=None, limit=100) -> list[dict]:
    # SELECT * FROM audit_log [WHERE agent_id = ?]
    # ORDER BY id DESC LIMIT ?
```

The only filter exposed today is `agent_id`. The HLD describes additional filters (`action`, `since` timestamp) — these are **not** implemented in code (the upstream `CIPHER_LLD.md` text shows them, but the actual `query()` method does not accept them).

### 4.3 Retention

- No retention policy in code. The table grows monotonically.
- WAL mode is enabled (`PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`) — see `sqlite_factory.py`.
- Backup / archival is not implemented.

### 4.4 Immutability

- Only `INSERT` statements exist in `AuditJournal`.
- There is **no cryptographic signature** of records (Ed25519 signing described in HLD is not present).
- Immutability is therefore limited to the absence of `UPDATE`/`DELETE` code paths and the host filesystem's protection of the SQLite file.

## 5. Configuration

| Env var                | Default                                          | Consumer                          |
|------------------------|--------------------------------------------------|-----------------------------------|
| `OPA_URL`              | `http://localhost:8181`                          | `OpaClient.__init__`              |
| `CIPHER_SQLITE_DIR`    | `deploy/local/data/sqlite`                       | `sqlite_factory._default_data_dir` (used by `create_audit_db`) |

**OPA bundle config** — Static file mount via `deploy/local/docker-compose.yml`; no remote bundle service, no signing key, no decision-log shipping configured. Bundle directory: `deploy/local/policies/` (currently 1 file: `poc_allow_all.rego`).

**SQLite pragmas** (from `sqlite_factory.py`):
- `PRAGMA journal_mode=WAL`
- `PRAGMA synchronous=NORMAL`

## 6. Test Coverage

| Test                                                                 | What it covers                                  |
|----------------------------------------------------------------------|-------------------------------------------------|
| `tests/unit/test_sprint2.py::TestAuditJournal::test_record_and_query`| Insert a row via raw SQL, then `journal.query(agent_id=...)` round-trip. Does not exercise the async `record()` directly. |
| `tests/unit/test_sprint2.py::TestOpaClient::test_health_check`       | Mocks `httpx.AsyncClient`, verifies `health_check()` returns `True` on 200. |
| `tests/unit/test_sprint2.py::TestOpaClient::test_evaluate_allow`     | Mocks POST response `{"result": {"allow": True}}`, verifies `evaluate()` returns `True`. |
| `tests/e2e/test_poc_spine.py::TestPOCExitCriterion4_AuditJournal`    | E2E exercise of audit journal as part of POC spine. |
| `tests/e2e/test_poc_spine.py` (OPA section, ~line 188)               | E2E OPA client wiring against a real or mocked sidecar. |

Gaps:
- No test for `evaluate_deny` (missing `allow=False` path).
- No test for OPA non-200 responses or for `record()` under concurrency.
- No test verifies OTel `trace_id`/`span_id` are written into the audit row.

## 7. TODOs

1. **Typed `PolicyDecision` dataclass** — return obligations, reason codes, and the full OPA `result` payload, not just `bool`.
2. **Shared `httpx.AsyncClient`** — reuse a single client to avoid per-call connection setup; align with the long-lived client shown in `docs/CIPHER_LLD.md` §4.1.
3. **Async-correct SQLite writes** — move `INSERT` off the event loop (e.g. `asyncio.to_thread`) or migrate to `aiosqlite`.
4. **Sign audit records** — add Ed25519 signing per HLD §3.5; introduce key management under `cipher/governance/`.
5. **Implement HITL Gate Manager** — owner of `cipher.gate.pending` CloudEvents and LangGraph workflow suspension/resumption.
6. **Implement Identity Manager** — JWT issuance, validation, and agent Ed25519 keypair lifecycle.
7. **Implement Domain Pack Loader** — load `cipher/governance/domain_packs/{pack_id}/` and register policies / evidence schemas / approval matrices.
8. **Restrictive OPA bundle** — replace `poc_allow_all.rego` with per-agent, per-action policies and add a deny-by-default fallback in the in-process client.
9. **Audit query enhancements** — accept `action`, `since`, and pagination filters as documented in `docs/CIPHER_LLD.md` §4.2.
10. **Audit retention/rotation** — define a policy (size-based or time-based) and add an archival path.
11. **HTTP read API for audit log** — expose `GET /audit?...` for the dashboard.
12. **ASDLC gate wiring (PROC-001)** — currently DevNex gates run inline in the GUI; route them through GCL so every gate decision is auditable.
