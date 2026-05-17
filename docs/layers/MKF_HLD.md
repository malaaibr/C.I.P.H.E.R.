---
doc_id: HLD-MKF-001
layer: MKF
title: Memory & Knowledge Fabric — High-Level Design
status: Draft
owner: Layer-Doc Author
related:
  - docs/CIPHER_HLD.md §3.3 (Layer 3 — MKF)
  - docs/CIPHER_LLD.md §6 (Layer 4 — MKF)
  - cipher/mkf/memory_agent/
  - cipher/memory/
---

# §0 Frontmatter

| Field | Value |
|-------|-------|
| Doc ID | HLD-MKF-001 |
| Layer  | MKF (Memory & Knowledge Fabric — Hybrid RAG) |
| Scope  | High-Level Design |
| Implementation roots | `cipher/mkf/`, `cipher/memory/` |
| Service entrypoint   | `cipher/mkf/memory_agent/service.py` (FastAPI) |

---

# §1 Purpose & Scope

The Memory & Knowledge Fabric (MKF) is the **hybrid retrieval and long-term
memory layer** for CIPHER. It provides agents with semantic recall over
ingested documents (specs, source files, prior artifacts) and exposes a
unified `MemoryAPI`-style interface so callers do not see the underlying
storage technology.

In the current POC code-base the implemented surface is **hybrid RAG only**:

- **Dense retrieval** — sentence-transformers embeddings (default
  `all-MiniLM-L6-v2`, 384-dim) stored in **Qdrant** (`cipher_memory`
  collection, COSINE).
- **Sparse retrieval** — in-memory **BM25Okapi** index over the same corpus.
- **Hybrid fusion** — weighted linear combination
  `score = α·dense + (1-α)·bm25_norm`, default `α=0.5` (ADR-0004).
- **Service surface** — FastAPI app `cipher.mkf.memory_agent.service:app`
  exposing `GET /health` and `POST /v1/memory/query`.

The wider HLD (`docs/CIPHER_HLD.md §3.3`) also scopes a four-tier memory
model (working / episodic / semantic / procedural), Memgraph-backed
temporal knowledge graph, MinIO object store, and a consolidation
scheduler. These are described as **planned** in `cipher/memory/README.md`
but **are not implemented** in the current `cipher/mkf/` tree — see §7.

---

# §2 Position in the 7-Layer Architecture

MKF is the **Memory & Knowledge Fabric** layer, declared by the project
overview in `CLAUDE.md` as: *"Hybrid RAG (sentence-transformers + Qdrant +
BM25)"*.

```
┌────────────────────────────────────────────────────────────┐
│ AAL (Agents — DevNex, …)                                   │
├────────────────────────────────────────────────────────────┤
│ ARE (A2A Server)                                           │
├────────────────────────────────────────────────────────────┤
│ TRF (LLM Gateway)                                          │
├──────────────┐                                             │
│              │   MKF — Hybrid RAG (this layer)             │
│ GCL (policy) │   ├─ Embedder (sentence-transformers)       │
│              │   ├─ QdrantIndex (dense)                    │
│              │   ├─ BM25Index (sparse, in-process)         │
│              │   └─ HybridWeightedRetriever (α-fuse)       │
├──────────────┴─────────────────────────────────────────────┤
│ PKL (NATS + LangGraph)                                     │
├────────────────────────────────────────────────────────────┤
│ DRS (Docker Compose: Qdrant :6333, Memgraph, Redis, …)     │
└────────────────────────────────────────────────────────────┘
```

Per HLD §3.3, MKF is intended as a **cross-cutting fabric** (AUTOSAR-style
Complex Driver) that AAL may invoke directly without traversing every
intermediate layer. In the POC, AAL components reach MKF via the FastAPI
endpoint or by importing `cipher.mkf.memory_agent` directly.

---

# §3 External Interfaces

## §3.1 Search API (implemented)

`POST /v1/memory/query` — `cipher/mkf/memory_agent/service.py`

Request (`MemoryQueryRequest`):

```json
{
  "query": "string",
  "top_k": 5,
  "collection": "cipher_memory"
}
```

Response (`MemoryQueryResponse`):

```json
{
  "query": "...",
  "total": <int>,
  "results": [
    {"document": "...", "score": 0.83, "source": "hybrid", "metadata": {...}}
  ]
}
```

`GET /health` → `{"status": "ok", "service": "memory-agent"}`.

The endpoint is decorated with `@traced(name="memory_agent.query",
attributes={"layer": "mkf"})` from `cipher.core.otel`.

## §3.2 Indexing API (partial)

There is **no HTTP indexing endpoint** in the current service.
Programmatic ingestion is available via:

- `EmbeddingModel.encode(texts)` — produce normalised vectors.
- `QdrantIndex.add(ids, embeddings, documents, metadatas)` — upsert dense
  points.
- `BM25Index.fit(documents)` — (re)build the sparse index.

A higher-level indexer / loader is **not yet present** in the tree —
flagged in §7.

## §3.3 Python client surface

`cipher.mkf.memory_agent._deps.get_retriever(collection)` returns a
process-cached `HybridWeightedRetriever` (one per collection).

---

# §4 Internal Decomposition

| Component | File | Role |
|-----------|------|------|
| `EmbeddingModel` | `cipher/mkf/memory_agent/embedder.py` | Wraps `sentence_transformers.SentenceTransformer`; lazy-loads model; `encode` and `encode_query`; reports `vector_size`. |
| `QdrantIndex`    | `cipher/mkf/memory_agent/qdrant_index.py` | Dense vector store; ensures collection at init; `add`, `search` (uses `query_points`), `delete_collection`. |
| `BM25Index`      | `cipher/mkf/memory_agent/bm25_index.py` | Sparse retrieval over `BM25Okapi`; lower-case whitespace tokenisation; returns `BM25Result(document, score, index)`. |
| `HybridWeightedRetriever` | `cipher/mkf/memory_agent/retriever.py` | Fuses dense + sparse scores with α weight; over-fetches `top_k * 2` from each side; normalises BM25 by max score. |
| `service.py`     | `cipher/mkf/memory_agent/service.py` | FastAPI app; OTel-traced `/v1/memory/query`. |
| `_deps.py`       | `cipher/mkf/memory_agent/_deps.py` | Process-level retriever cache keyed by collection name. |
| `schemas.py`     | `cipher/mkf/memory_agent/schemas.py` | Pydantic request/response models. |
| `cipher/memory/` | `cipher/memory/__init__.py` + `README.md` | Scaffold only — declared boundary for working/document/vector/graph memory; **stub**. |

Adjacent (not in MKF tree but consumed):

- `cipher/core/adapters/qdrant_client_wrapper.py` — `QdrantHealthClient`
  for `/healthz`. MKF's own client construction goes through
  `qdrant_client.QdrantClient` directly (not the wrapper).

---

# §5 Dependencies

## §5.1 Down-stack (MKF depends on)

- **DRS** — Qdrant container at `QDRANT_URL` (default
  `http://localhost:6333`), brought up by
  `deploy/local/docker-compose.yml`.
- **Python libraries**:
  - `sentence-transformers` (model load, normalised embeddings)
  - `qdrant-client` (`QdrantClient`, `PointStruct`, `VectorParams`,
    `Distance.COSINE`)
  - `rank-bm25` (`BM25Okapi`)
  - `fastapi`, `pydantic`
  - `cipher.core.otel.traced`

## §5.2 Up-stack (depends on MKF)

Per HLD §3.3 and §8.2, ARE/AAL agents call MKF via a `MemoryClient`
wrapper. In the current POC, callers either hit `POST /v1/memory/query`
or import `cipher.mkf.memory_agent` directly. **No `MemoryClient`
abstraction is present** in the tree — see §7.

## §5.3 Cross-cutting

- **GCL** — HLD §3.4 / §8.2 require policy evaluation and audit on
  artifact writes; **not wired into MKF code paths today**.
- **OTel** — `@traced` decorator applied to the query endpoint only.

---

# §6 Quality Attributes

| Attribute | Target / Behaviour | Notes |
|-----------|-------------------|-------|
| Retrieval latency | Not specified in code; CIPHER_HLD references RAG path but no explicit SLO. | Profiling TODO. |
| Recall@k | No measured target; default `top_k=5`, fusion fetches `top_k*2` per modality before merge. | No eval harness in tree. |
| Memory consistency | Single-process retriever cache in `_deps.py`; BM25 corpus is **in-memory**, **non-persistent**, must be re-`fit` per process. | Drift between Qdrant (persistent) and BM25 (volatile) is an open risk. |
| Determinism | Embeddings normalised at encode time; COSINE distance in Qdrant; α-fusion deterministic given identical inputs. | OK. |
| Observability | OTel span on `/v1/memory/query` with `layer=mkf` attribute. | No per-component spans inside retriever. |
| Security | No auth on FastAPI endpoint; no GCL hook. | See §7. |

---

# §7 Open Questions

1. **Four-tier memory** (working / episodic / semantic / procedural) and
   **Memgraph temporal KG** described in `CIPHER_HLD.md §3.3` are not
   implemented in `cipher/mkf/`. `cipher/memory/` is a stub.
2. **BM25 persistence** — `BM25Index` lives in-process only; no fit-from-
   Qdrant bootstrap or on-disk snapshot. Process restarts return empty
   sparse hits until re-fit.
3. **Indexing pipeline** — no document loader, chunker, or HTTP
   `/v1/memory/upsert` endpoint exists. Ingestion must be done by an
   external script using the Python API.
4. **Reranker** — HLD mentions `bge-reranker-large` cross-encoder; **not
   present** in code.
5. **Graph expansion** — HLD §3.3 and §13.3 describe a vector → graph
   expansion → rerank pipeline; only stage 1 + 2 (vector + BM25 fuse)
   exists.
6. **Memory Agent (AGT-007)** — HLD lists a manager-tier Memory Agent on
   port `:7100`; the FastAPI service in this repo has no port binding in
   code (run via uvicorn externally) and no consolidation / retention
   logic.
7. **GCL & audit integration** — writes are not policy-checked.
8. **MemoryClient abstraction** — callers couple to FastAPI HTTP or
   import internals directly; no thin client library yet.
9. **Multi-collection lifecycle** — `_deps.get_retriever` caches per
   collection but never evicts; long-running services will accumulate
   loaded models.
