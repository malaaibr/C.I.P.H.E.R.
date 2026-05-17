# DRS — High-Level Design

## §0 Frontmatter

| Field | Value |
|---|---|
| Doc ID | HLD-DRS-001 |
| Version | 1.0 |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Layer | DRS — Deployment & Runtime Substrate |
| Date | 2026-05-17 |
| Status | DRAFT |
| Implementation dirs | `deploy/`, `cipher/deploy/` |
| Authoritative sources | `deploy/local/docker-compose.yml`, `deploy/local/Makefile`, `deploy/local/.env.example`, `docs/CIPHER_HLD.md` §3.1, `docs/CIPHER_LLD.md` §3 |

---

## §1 Purpose & Scope

The Deployment & Runtime Substrate (DRS) is the lowest CIPHER-owned layer. Its
purpose is to **host the infrastructure** that every higher layer depends on at
runtime: backing stores, the event bus, the policy engine, the observability
collector, and the artefact object store. In the Local POC, DRS materializes as
a single Docker Compose stack that runs on a developer workstation
(see `CLAUDE.md` "How to Run", lines 49–53).

Per `docs/CIPHER_HLD.md` (line 286), DRS is what makes CIPHER
*deployment-topology-independent*: it defines the contract that any topology
(Docker Compose now, Nomad/Kubernetes later) must satisfy. The current
POC implementation is the Compose driver only.

**In scope (this doc).**
- The local Docker Compose stack defined in `deploy/local/docker-compose.yml`
- Volume layout under `deploy/local/data/`
- Operator surface (`Makefile` targets, `.env` contract)
- Mounted policy directory (`deploy/local/policies/`)
- OTel collector configuration (`deploy/local/otel-config.yaml`)

**Out of scope.**
- The fabric protocol abstractions in `cipher.core.substrate` (documented under
  the Core layer, not DRS) — DRS HLD is concerned with the running
  infrastructure, not the Python adapters that talk to it.
- Cloud / Kubernetes driver implementations — not yet implemented.

---

## §2 Position in the 7-Layer Architecture

DRS sits at the bottom of the stack. From `docs/CIPHER_HLD.md` (lines 151,
173, 247–268), the dependency graph is:

```
DRS → PKL → MKF → TRF → GCL → ARE → AAL → GUI
```

Every other layer depends on DRS, but DRS depends on nothing inside CIPHER —
only on the host (Docker Engine + host OS). DRS is to CIPHER what the
Microcontroller (MCAL) is to AUTOSAR: the substrate that abstracts the
hardware/topology and provides typed primitives upward.

Concretely, the services DRS runs map to higher layers as follows:

| Higher layer | Consumes from DRS |
|---|---|
| PKL (Platform Kernel) | NATS event bus (`:4222`), OTel collector (`:4317`) |
| MKF (Memory & Knowledge Fabric) | Redis, Memgraph, Qdrant, MinIO |
| GCL (Governance & Compliance) | OPA sidecar (`:8181`) |
| TRF / ARE / AAL | All of the above transitively |

---

## §3 External Interfaces

DRS exposes interfaces in three directions: ports to host applications, volume
mounts to host filesystem, and the `.env` configuration contract.

### 3.1 Exposed ports (host → container, bound to `127.0.0.1` only)

| Service | Host port(s) | Purpose |
|---|---|---|
| Redis | 6379 | RESP working memory |
| Memgraph | 7687 (Bolt), 7444 (monitoring) | Knowledge graph |
| Qdrant | 6333 (HTTP), 6334 (gRPC) | Vector search |
| MinIO | 9000 (S3 API), 9001 (Console) | Artefact object store |
| NATS | 4222 (client), 8222 (monitoring) | Event bus with JetStream |
| OPA | 8181 | Policy decision API |
| OTel Collector | 4317 (gRPC), 4318 (HTTP) | Telemetry ingest |

All ports are bound to `127.0.0.1` (loopback) — no external network exposure.

### 3.2 Volume mount conventions

Two patterns are used in `docker-compose.yml`:

1. **Bind mounts** rooted at `deploy/local/data/<service>/` — used for Redis,
   Qdrant, MinIO. Survives `docker compose down`; removed by `make clean`.
2. **Named volume** `memgraph_data` — used for Memgraph (declared at the
   bottom of the compose file). Managed by Docker.

Read-only config mounts: `./otel-config.yaml` and `./policies/`.

### 3.3 `.env` contract

The `.env` file (gitignored; template at `deploy/local/.env.example`) is the
single source of truth for service URLs and credentials consumed by both the
Compose stack and the Python application. See LLD §4 for the full key list.

---

## §4 Internal Decomposition

The DRS internal structure has four parts:

### 4.1 Compose service set
Seven long-running services plus one init job (`minio-init`) that creates
the `cipher-artifacts` and `cipher-checkpoints` buckets on first boot.
See LLD §1 for the full inventory.

### 4.2 Makefile operator surface
`deploy/local/Makefile` provides developer ergonomics: `make up`, `down`,
`status`, `logs`, `health`, `clean`, plus test passthroughs (`lint`, `test`,
`test-unit`, `test-integration`, `test-e2e`, `poc-demo`).

### 4.3 Policy directory
`deploy/local/policies/` is bind-mounted read-only into the OPA container.
Currently contains a single permissive POC policy
(`poc_allow_all.rego`, `default allow := true`). The Rego content itself is
governed by the GCL layer; DRS only owns the mount.

### 4.4 OTel collector config
`deploy/local/otel-config.yaml` defines a minimal OTLP-in → logging-out
pipeline for traces and metrics. No persistent backend is wired up in the
POC.

---

## §5 Dependencies

DRS has no upstream CIPHER dependencies. Its host-level prerequisites are:

| Dependency | Version / note |
|---|---|
| Docker Engine | Any recent version supporting Compose v2 (`docker compose` subcommand) |
| Host OS | Windows 11 Pro (primary dev target, per env) or Linux |
| Available host ports | All ports listed in §3.1 must be free on `127.0.0.1` |
| Free disk | Sufficient for `deploy/local/data/` (varies with MKF/MinIO usage) |
| GNU Make | Optional — only for the Makefile shortcuts |
| Ollama | Not run by Compose; expected on host at `:11434` (see `.env.example`) |

---

## §6 Quality Attributes

| Attribute | Current state |
|---|---|
| Startup time | `docker compose up -d --wait` blocks on healthchecks; observed start-up dominated by Memgraph (`start_period: 10s`) and image pull on first run. |
| Port collision policy | Hard-fails fast (Docker reports bind error). No fallback ports defined. |
| Data persistence | All stateful services persist to host bind mounts or named volumes. `make clean` is explicitly destructive (`docker compose down -v && rm -rf ./data`). |
| Health probes | Every service except `otel-collector` defines a healthcheck. `minio-init` exits after bucket creation by design. |
| Network exposure | All ports loopback-only (`127.0.0.1:`). No external attack surface from the stack itself. |
| Secret handling | Credentials live in `.env` (gitignored). `.env.example` lists keys with placeholder values only. |
| Restart policy | `unless-stopped` on all long-running services; `minio-init` has none (one-shot). |

---

## §7 Open Questions

1. **Langfuse service is referenced but not declared.** `Makefile` `health`
   target curls `http://localhost:3000/api/public/health` and `.env.example`
   defines `LANGFUSE_HOST`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`. A
   `deploy/local/data/langfuse/langfuse.db` file also exists. However, no
   `langfuse` service is declared in `docker-compose.yml`. Is Langfuse run
   out-of-band, or is the compose service missing / not yet implemented?
2. **SQLite directory.** `.env.example` defines
   `CIPHER_SQLITE_DIR=deploy/local/data/sqlite`, but no such directory is
   present and no compose service produces it. Audit journal location is
   stub / not yet implemented at the DRS level.
3. **No `cipher/deploy/` content.** The path `cipher/deploy/local/README.md`
   exists but contains only a placeholder note. Intended scope vs. the active
   `deploy/local/` is unclear.
4. **No staging / production compose variants.** Only `deploy/local/` exists;
   the multi-topology promise in HLD §3.1 (Compose vs. Nomad vs. K8s) has not
   been materialized — not yet implemented.
5. **OTel exporter is `logging` only.** No durable trace backend (Tempo,
   Jaeger, Langfuse) is wired in `otel-config.yaml`. Wrap-only state.
