# ADR-0003: POC Scope Lock

- **Status:** Accepted
- **Deciders:** CIPHER Architecture Team
- **Date:** 2026-05-16
- **Layer:** All (cross-cutting governance decision)
- **Tags:** scope, poc, mvp, governance, milestone

---

## 1. Context and Problem Statement

The CIPHER project is building a five-layer agentic architecture for automotive embedded software engineering. The full system encompasses seven layers (DRS, PKL, MKF, TRF, GCL, ARE, AAL), multiple LLM backends, a hybrid RAG memory system, a knowledge graph, full ISO 26262 compliance tooling, and a GUI/voice interface.

Building all of this in a single phase is not feasible. Without a clearly bounded Proof-of-Concept (POC) scope, development effort disperses across the full feature surface, nothing reaches a demonstrable working state, and decisions about architecture are made without empirical validation.

This ADR defines the binding POC scope: what is in scope, what is explicitly out of scope, and the exit criteria that must be satisfied for POC to be declared complete and the project to advance to MVP planning. This scope definition is binding — any feature not listed as in-scope must not be implemented during POC without a scope amendment ADR.

---

## 2. Decision Drivers

- **Risk reduction**: Validate the core architectural pattern (agentic LLM pipeline for V-cycle LLD generation) before committing to full system build.
- **Time constraint**: POC must be completable by a small team (2–4 engineers) in 6–8 weeks.
- **Technology validation**: Key technical risks that must be validated in POC: (a) GCA WebSocket bridge reliability under repeated invocations, (b) HybridWeightedRetriever quality for automotive requirement documents, (c) LangGraph StateGraph viability as workflow orchestrator, (d) OTel + Langfuse observability pipeline end-to-end.
- **ADR stability**: The POC scope lock prevents ADR proliferation during the POC phase. Only ADRs for in-scope components need to be accepted before POC start.
- **Clear DoD**: The exit criterion provides an unambiguous test that determines when POC is done.

---

## 3. Decision

### 3.1 In-Scope for POC

The following components and capabilities are in scope for the POC:

#### Infrastructure (DRS Layer)
- Docker Compose driver scaffold with all required services
- NATS JetStream message broker
- Redis 7 (working memory / StateStore backend)
- Qdrant vector store (MKF vector index)
- SQLite (3 files: LangGraph checkpoint store, audit journal, configuration)
- MinIO object store (artifact storage)
- Langfuse (LLM observability — self-hosted)
- OTel Collector (span aggregation)

#### Event Bus and Workflow (PKL Layer)
- NATS wrapper for pub/sub event routing between agents
- LangGraph StateGraph as workflow orchestrator (replacing AF.json dispatch from DevNex)
- SQLite-backed LangGraph checkpoint store
- Langfuse + OTel Collector observability pipeline

#### Memory Agent (MKF Layer)
- QdrantIndex (REWRITE of ChromaDB from CAR-002)
- BM25Index adapter (WRAP from raglab_core)
- EmbeddingModel adapter (all-MiniLM-L6-v2 default)
- HybridWeightedRetriever (alpha=0.5 default) — vector + sparse hybrid retrieval
- MemoryAgent FastAPI service with A2A server interface
- **Graph expansion**: stub only — returns empty list; Memgraph connection deferred to MVP

#### LLM Gateway (TRF Layer)
- LLMBackend Protocol
- OllamaDriver (WRAP from raglab_core OllamaClient) for TRIAGE task class
- GeminiCLIDriver for PLAN task class
- GCAWebSocketDriver (WRAP from DevNex GCABridge) for CODE_GEN task class
- TaskClassRouter
- LLM Gateway FastAPI + MCP server
- Git MCP server (basic git operations)
- Filesystem MCP server (basic file read/write)
- Tool Broker + MCP Gateway

#### Governance / Compliance (GCL Layer)
- Append-only SQLite audit journal (every tool call and LLM invocation logged)
- OPA sidecar with permissive policy (allow-all in POC; policy evaluation plumbing in place)
- JWT + Ed25519 identity signing (agent identity, not user authentication)

#### Agent Runtime Environment (ARE Layer)
- A2A FastAPI server + AgentCard registry
- SkillLoader stages 1 and 2 (WRAP from DevNex IntentClassifier + SkillRegistry)
- Budget enforcer stub (always permits; actual budget enforcement deferred to MVP)

#### Application / Agent Layer (AAL Layer)
- DevNex GCABridge adapter (WRAP + REFACTOR _ADP_ROOT removal)
- DevNex pydantic v2 schemas (REFACTOR from types.py dataclasses)
- LLD generation skill for S1N1 stage only (vcycle_s1n1): reads HLD → builds S1N1 prompt → GCA CODE_GEN → writes {swc}_FUNC_req.csv
- SKILL.md metadata file for vcycle_s1n1
- Orchestrator LangGraph agent (single-agent orchestration: intent → skill dispatch → result)

#### Core Infrastructure (cross-layer)
- Pydantic v2 schemas: TaskContract, ArtifactRelation, AgentCard, CloudEvent
- OTel `@traced` decorator + OTel SDK setup
- SecretFabric (env-var config and .env file loading)

#### Testing
- Test environment conftest
- OllamaDriver unit tests
- QdrantIndex unit tests
- Multi-layer spine integration test (end-to-end from TaskContract through all layers)
- E2E test: TaskContract → Orchestrator → DevNex(S1N1) → artifacts written + OTel span emitted + audit journal entry

#### Documentation
- Gate G5 sign-off checklist (compliance map stub)

### 3.2 Explicitly Out of Scope for POC

The following are explicitly NOT in scope for POC. Implementing any of these during POC constitutes scope creep and requires a formal scope amendment ADR:

#### Features Deferred to MVP
- V-cycle stages S1N23, S1N4, S2N12, S3, S4, S5, S6, S7, S8, S9 — POC implements S1N1 only
- HITL gate implementation (WorkflowEngine `logic.humanReview` dispatch) — POC has S1N4 stub that returns `awaiting_review` without blocking
- Memgraph graph database connection and graph expansion (Rag33–38 patterns) — POC has stub returning empty list
- Graph-RAG retrieval (VectorFirst_ThenWalk, GlobalThemes) — deferred to MVP
- Cross-encoder reranker (Rag20 pattern) — POC uses HybridWeightedRetriever with no reranking
- Query rewriting (MultiRewrite, HyDE, StepBack — Rag16/17/18 patterns) — POC uses direct query
- Auto-failover between LLM backends — POC has single backend per task_class with no fallover
- OPA policy enforcement (non-permissive policies) — POC installs OPA in allow-all mode
- Budget enforcement (actual token/cost limits) — POC has stub that always permits
- Voice interface (AGT-006 Garvis) — deferred to MVP
- PyQt6 GUI (DevNex gui/) — GUI preserved in reference codebase; CIPHER POC is CLI/API only
- DevNex skills beyond S1N1: code_link, trace_report, test_gen, full_trace, explain, free_form — deferred to MVP
- VSS signal catalog integration (CAR-004 domain) — deferred to MVP
- AUTOSAR ARXML parsing — deferred to MVP
- Multi-agent orchestration (more than one active agent per task) — POC is single-agent
- BEIR/RAGAS evaluation harness integration — POC uses basic retrieval metric tests only
- MinIO large file storage integration (beyond basic connection test) — deferred to MVP
- Kubernetes deployment — explicitly excluded from all CIPHER phases (Docker Compose only)

#### Third-Party Services Not Approved
- Any paid cloud LLM API (OpenAI, Anthropic, Google Cloud Vertex, Azure OpenAI)
- Any cloud vector database (Pinecone, Weaviate Cloud, Chroma Cloud)
- Any cloud monitoring service (DataDog, New Relic, Splunk)
- GitHub Actions / CI pipeline integration — POC testing is local only

### 3.3 POC Exit Criteria

The POC is declared complete when ALL of the following criteria are satisfied simultaneously. Partial satisfaction does not constitute POC completion:

#### Criterion 1: E2E Spine Test Passes
The automated E2E test `tests/e2e/test_poc_spine.py` must pass without manual intervention:
- **Input**: A `TaskContract` with `task_class=CODE_GEN`, a SWC name, and HLD content
- **Processing**: Routes through Orchestrator → DevNex S1N1 skill → GCA WebSocket → LLM response
- **Outputs verified**:
  - `{swc}_FUNC_req.csv` written to MinIO artifact store with ≥5 requirements rows
  - `current_stage` set to `S1N1` in Redis StateStore
  - At least one OTel span with attribute `llm.backend_id=gca_websocket` present in Langfuse
  - At least one audit journal entry in SQLite for the GCA WebSocket call
  - `TaskResult.status = "success"`

#### Criterion 2: All Unit Tests Pass
`pytest tests/unit/` passes with zero failures and zero errors. Minimum coverage: 80% on `trf/mcp_servers/llm_gateway/` and `mkf/memory_agent/`.

#### Criterion 3: HybridWeightedRetriever Quality Gate
Running `tests/eval/` against `tests/fixtures/legacy/ragtest/` golden set:
- Recall@5 ≥ 0.70 for the QdrantIndex + BM25 hybrid retriever with alpha=0.5
- Test must complete using only local Ollama (no external API calls)

#### Criterion 4: Docker Compose Stack Starts Clean
`docker compose up --wait` on `deploy/docker-compose.yml` must bring all services to `healthy` status within 120 seconds on a clean machine (no pre-existing volumes). Services: NATS, Redis, Qdrant, SQLite (file-based, no service), MinIO, Langfuse, OTel Collector, LLM Gateway, Memory Agent, A2A Server.

#### Criterion 5: Type Check and Lint Pass
`pyright .` on the CIPHER codebase must report zero errors. `ruff check .` must report zero errors. Both must be runnable via `make lint`.

#### Criterion 6: Gate G5 Sign-Off Checklist Completed
The compliance map stub at `docs/qa/gate_g5.md` must be filled in by the architecture team, attesting that: (a) all in-scope ADRs are Accepted, (b) no out-of-scope features were implemented, (c) all POC exit criteria have been demonstrated, (d) all architectural debt items identified in CAR-001 and CAR-002 that affect POC-scope modules have been resolved or explicitly deferred with a tracked item.

---

## 4. Scope Amendment Process

If during POC a feature listed as out-of-scope is determined to be necessary for POC completion, the following process must be followed:

1. **Raise**: Open a scope amendment discussion identifying the feature, the reason it is now believed necessary, and the impact on POC timeline.
2. **ADR**: Write a scope amendment ADR (numbered ADR-0003a, ADR-0003b, etc.) with the specific in-scope addition and the rationale.
3. **Review**: The amendment ADR must be reviewed and accepted by at least one additional team member before any implementation begins.
4. **Update WBS**: Update WBS-0001-poc-spine.md to add the new tasks and update the critical path.

Features that are merely useful but not necessary for POC exit criteria do not qualify for scope amendment — they are deferred to MVP.

---

## 5. Consequences

**Positive**:
- Clear DoD for POC. Every team member knows exactly what done looks like.
- Forces architectural discipline: the spine (TaskContract → Orchestrator → S1N1 → artifacts + OTel + audit) is the primary value deliverable. Everything else is secondary.
- Prevents the most common POC failure mode: scope creep leading to a large half-finished system with no demonstrable working path.
- Gates G5 sign-off creates a forcing function for documentation and compliance map completeness before MVP funding decisions.

**Negative**:
- Some stakeholders may perceive the POC as "too small" because only S1N1 is implemented. Clear communication that S1N1 validates the entire LLM-to-artifact pipeline is required.
- Strict out-of-scope rules may create friction if a discovery during POC reveals that a deferred feature is unexpectedly necessary (mitigated by the scope amendment process).

**Neutral**:
- The POC exit criteria specifically do not include performance benchmarks (latency, throughput) — these are MVP concerns. POC only requires functional correctness.

---

## 6. Related Decisions

- **ADR-0001**: LLM Gateway — in-scope (3 backends, TRIAGE/PLAN/CODE_GEN task classes)
- **ADR-0002**: GCA WebSocket Bridge — in-scope (CODE_GEN backend)
- **ADR-0004**: Memory Agent Hybrid RAG — in-scope (QdrantIndex + BM25 + HybridWeightedRetriever)
- **ADR-0005**: DevNex Agent A2A Wrapping — in-scope (S1N1 only)
- **ADR-0006**: HITL Gate — out-of-scope for POC (stub only)
- **ADR-0007**: Skill Loader — in-scope (stages 1+2)
- **ADR-0008**: Observability — in-scope (OTel + Langfuse)
- **WBS-0001**: POC Spine — all T-001 through T-035 tasks are POC scope tasks governed by this decision
