---
id: AGENT-MEM-001
name: memory_agent
status: STUB
layer: AAL (planned bridge to MKF)
role: Long-term memory + RAG retrieval agent (planned)
implementation_path: cipher/agents/memory_agent/
related_adrs:
  - ADR-0004-memory-agent-rag.md
related_hld_sections:
  - CIPHER_HLD.md §6.8 — Memory / Context Agent (AGT-007)
---

# memory_agent — Agent Doc

## 1. Role & Capabilities (Planned)

The `memory_agent` is the planned AAL-side wrapper around the MKF Memory Agent
(AGT-007). It is intended to expose CIPHER's memory subsystem as an
agent-callable interface — so other AAL agents (DevNex, planner stubs,
compliance stubs) reach long-term memory through a uniform A2A skill rather
than embedding raw `MemoryAPI` HTTP calls.

Planned capabilities:

- Wrap MKF hybrid retrieval (`score = alpha * dense + (1 - alpha) * BM25`)
  behind an A2A skill consumable by any AAL agent.
- Persist agent-conversation memory across sessions (episodic tier; ADR-0004
  marks conversation memory itself as MVP, so the agent stub anticipates that
  surface area).
- Drive long-term knowledge curation: trigger episodic-to-semantic
  consolidation, retention enforcement, and temporal-edge maintenance owned
  by MKF AGT-007 (HLD §6.8).
- Bridge `TaskContract` requests from PKL/ARE into MKF `MemoryAPI` calls.

It is **not** the storage layer itself. Qdrant, BM25, Memgraph, Redis, MinIO,
and SQLite remain owned by MKF; this agent is the AAL-facing facade.

## 2. Current State — STUB

Per the AAL roll-up, this agent is a scaffold only. Files present:

- `cipher/agents/memory_agent/README.md` — single-line scope statement
  ("Phase 1 ownership boundary for memory reads, writes, consolidation, and
  temporal graph persistence.").
- `cipher/agents/memory_agent/__init__.py` — empty module docstring only
  (`"""Memory agent scaffold for the local MVP."""`).

No service, no client, no `MemoryAPI` calls, no A2A registration, no tests.

## 3. Reference to ADR-0004

ADR-0004 (`docs/adr/ADR-0004-memory-agent-rag.md`, **Accepted**, 2026-05-16)
defines the substrate this agent will front. Key decisions to honour:

- **§4 Decision (Option B):** REWRITE `ChromaIndex` → `QdrantIndex`; WRAP all
  other `raglab_core` components. The agent must never reintroduce ChromaDB
  (violates §1.3 hard constraint).
- **§4.1 Component Disposition Table:** target module layout is `mkf/memory_agent/`
  (chunker, qdrant_index, bm25_index, embedder, retriever, graph_expansion,
  service). The AAL `memory_agent` is the consumer, not the owner, of those.
- **§4.3 Hybrid retriever:** POC alpha = 0.5 (env `MKF_HYBRID_ALPHA`);
  alpha=0.3 recommended later for requirement-ID-heavy queries.
- **§4.4 Graph expansion:** POC stub returns `[]`; Memgraph integration is MVP.
  The agent must not depend on graph results in POC.
- **§4.5 Service surface:** `POST /ingest`, `POST /query`, `DELETE /collection/{n}`,
  `GET /health` on `MKF_SERVICE_PORT=8002`. The AAL agent calls these.
- **§6 POC scope boundary:** conversation memory, reranking, query rewriting,
  and RRF are explicitly deferred to MVP — the agent should not advertise them
  as skills in POC.

## 4. Planned UC Mapping

- **UC 4.1 — Trace Q&A** (`ASDLC.md` line 95; `WBS-0002` §G4b; `WBS-0003`
  §G4b cross-component join): produces a `QAAnswer` object with `question`,
  `answer`, and a non-empty `sources[]` citing rows of
  `Full_Traceability_Matrix.csv`. The `memory_agent` is the planned A2A
  entry point for that retrieval: it takes the audience question, calls MKF
  hybrid retrieval over the indexed matrix, and returns the cited rows used to
  populate `QAAnswer.sources`.

Other UCs (1.x LLD generation, 3.1 ASIL gate, 4.4 post-merge semantic check)
read memory via DevNex orchestration; the dedicated `memory_agent` becomes
relevant when a UC needs memory access independent of DevNex.

## 5. Inputs / Outputs (Planned)

**Inputs**
- `TaskContract` carrying a memory request: `query`, `collection`, `top_k`,
  `strategy ∈ {hybrid, dense, sparse}`, optional filters.
- Ingest requests: `docs[]` plus `metadata[]` (matrix rows, requirement
  artifacts, LLD outputs, code snippets).
- Consolidation triggers (scheduled or on-demand).

**Outputs**
- Retrieval result list: `{text, score, ...metadata}` per ADR-0004 §4.2.
- `QAAnswer.sources[]` payload for UC 4.1.
- Health / status responses for ARE registration.
- OTel spans (`memory_agent.query`, `memory_agent.ingest`) per ADR-0008.

## 6. Dependencies (Planned)

- **MKF Memory Agent service** (FastAPI `:8002`) — Qdrant index, BM25 index,
  `HybridWeightedRetriever`, embedder, graph-expansion stub.
- **Qdrant** (`MKF_QDRANT_HOST:6333`) — vector store, §1.3 mandate.
- **BM25 in-process index** — sparse leg.
- **Core schemas** — `TaskContract`, `AgentCard` from `cipher.core.schemas`.
- **ARE / A2A Server** (`:8100`) — AgentCard registration so other agents can
  call this one.
- **OTel tracing adapter** from `cipher.core` per ADR-0008.
- **TRF LLM Gateway** (`:8200`) — only relevant in MVP when graph entity
  extraction needs an LLM; POC has no LLM dependency for retrieval.

## 7. Open Items

- Not yet implemented. The directory is a scaffold; ADR-0004's decisions
  (QdrantIndex REWRITE, BM25 WRAP, HybridWeightedRetriever WRAP, FastAPI
  service, GraphExpander stub) are all unrealised in code.
- Define the AAL-side AgentCard and A2A skill schema for `memory.query` and
  `memory.ingest`.
- Decide whether this agent calls MKF over HTTP (`localhost:8002`) or imports
  MKF modules in-process; ADR-0004 specifies the HTTP surface but the AAL
  facade pattern is not yet ADR-covered.
- Wire UC 4.1 `QAAnswer` assembly: where does the citation formatter live —
  here, or in DevNex? Pending decision.
- Confirm UC 4.1 wiring against `Full_Traceability_Matrix.csv` ingestion
  path (matrix rows → MKF collection name → retrieval filter).
- Conversation memory (ADR-0004 §6) deferred to MVP; reflect in roadmap once
  POC closes.

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
