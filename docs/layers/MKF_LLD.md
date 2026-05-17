---
doc_id: LLD-MKF-001
layer: MKF
title: Memory & Knowledge Fabric — Low-Level Design
status: Draft
owner: Layer-Doc Author
related:
  - docs/layers/MKF_HLD.md (HLD-MKF-001)
  - docs/CIPHER_LLD.md §6 (Layer 4 — MKF)
  - cipher/mkf/memory_agent/
---

# §0 Frontmatter

| Field | Value |
|-------|-------|
| Doc ID | LLD-MKF-001 |
| Layer  | MKF |
| Scope  | Low-Level Design |
| Source of truth | files under `cipher/mkf/memory_agent/` |
| Pairs with | `docs/layers/MKF_HLD.md` |

---

# §1 Module Inventory

```
cipher/mkf/
├── __init__.py                       # docstring only; no exports
└── memory_agent/
    ├── __init__.py                   # (not read — assumed marker)
    ├── _deps.py                      # process-level retriever cache
    ├── bm25_index.py                 # BM25Okapi wrapper
    ├── embedder.py                   # sentence-transformers wrapper
    ├── qdrant_index.py               # Qdrant dense index
    ├── retriever.py                  # HybridWeightedRetriever (α-fuse)
    ├── schemas.py                    # Pydantic request/response models
    └── service.py                    # FastAPI app

cipher/memory/                        # stub — README marks Phase-1 boundary
├── __init__.py                       # docstring only
└── README.md                         # responsibilities listed; no code
```

**Public symbols (current):**

| Symbol | Module | Notes |
|--------|--------|-------|
| `EmbeddingModel` | `embedder` | `encode`, `encode_query`, `vector_size`, `model` |
| `QdrantIndex` | `qdrant_index` | `add`, `search`, `delete_collection` |
| `BM25Index`, `BM25Result` | `bm25_index` | `fit`, `search` |
| `HybridWeightedRetriever`, `RetrievalResult` | `retriever` | `retrieve` |
| `get_retriever` | `_deps` | cache by collection name |
| `MemoryQueryRequest`, `MemoryResult`, `MemoryQueryResponse` | `schemas` | Pydantic models |
| `app` | `service` | FastAPI instance |

---

# §2 Embedding Pipeline

**File:** `cipher/mkf/memory_agent/embedder.py`

- Class: `EmbeddingModel`
- Model name resolution order:
  1. Explicit `model_name=` ctor argument
  2. Environment variable `EMBEDDING_MODEL`
  3. Default literal `"all-MiniLM-L6-v2"`
- Vector dimension: derived from the loaded model via
  `get_sentence_embedding_dimension()`. For `all-MiniLM-L6-v2` this is
  **384** (also the default `vector_size=384` in `QdrantIndex`).
- Lazy load: `self._model` stays `None` until first `.model` access; the
  `SentenceTransformer(self._model_name)` call runs on first use.
- Encoding: `encode(texts)` calls
  `self.model.encode(texts, normalize_embeddings=True)` and returns a
  `list[list[float]]`. Normalisation pairs with Qdrant COSINE distance to
  yield bounded `[-1, 1]` scores.
- Query helper: `encode_query(query)` returns the single vector for one
  query string.
- **Batching:** not explicit; passes the list straight to
  `SentenceTransformer.encode` which batches internally. **No batch-size
  parameter is exposed.**

---

# §3 Qdrant Collections

**File:** `cipher/mkf/memory_agent/qdrant_index.py`

## §3.1 Connection

- URL resolution: `url=` ctor arg → `QDRANT_URL` env → `http://localhost:6333`.
- Client: `qdrant_client.QdrantClient(url=self._url)` — synchronous HTTP.
- Construction is eager: `_ensure_collection()` is called inside
  `__init__`, so first instantiation requires Qdrant to be reachable.

## §3.2 Collection naming

- Default collection name: **`cipher_memory`**.
- Also referenced as the default in `MemoryQueryRequest.collection`
  (schemas.py).
- One Qdrant collection per logical "memory bucket"; `_deps.get_retriever`
  keys its cache by `collection`.

## §3.3 Schema

- Vectors: `VectorParams(size=<vector_size>, distance=Distance.COSINE)`.
- `vector_size` defaults to `384` but at runtime is set by
  `_deps.get_retriever` to `embedder.vector_size`, so any model swap that
  reports a different dim auto-propagates *for a freshly-created
  collection*. **There is no migration path** if the collection already
  exists with another dimension.
- Payload schema (set by `QdrantIndex.add`):
  ```json
  {
    "document": "<raw text>",
    "<metadata keys spread in>": "..."
  }
  ```
  The retriever reads `payload["document"]` and reconstructs the
  metadata dict by stripping the `document` key (see `qdrant_index.py`
  L80–L85).

## §3.4 IDs

- `QdrantIndex.add(ids=...)` accepts an `ids` list but **ignores it**:
  the implementation generates point IDs via `enumerate(...)` at L51.
  This is a known gap — flagged in §7.

## §3.5 Search

- Uses the modern `client.query_points(collection_name, query, limit)`
  API (not the deprecated `search`).
- Returns objects with `.id`, `.score`, `.payload`.

---

# §4 BM25 Index

**File:** `cipher/mkf/memory_agent/bm25_index.py`

- Backend: `rank_bm25.BM25Okapi`.
- Tokenisation: `doc.lower().split()` — pure whitespace, no
  stemming/stopword removal.
- Corpus structure: `BM25Index` holds three parallel lists in memory —
  `self._corpus` (raw docs), `self._tokenized` (token lists), and the
  built `self._bm25` instance.
- Lifecycle:
  - `fit(documents)` rebuilds the whole index (no incremental add).
  - `search(query, top_k=5)`:
    1. tokenise query the same way,
    2. `self._bm25.get_scores(tokens)` → score vector,
    3. `sorted(enumerate(scores), reverse=True)[:top_k]`,
    4. filter out non-positive scores (`if score > 0`),
    5. wrap as `BM25Result(document, score, index)`.
- Empty-state contract: `search` before `fit` returns `[]` (no
  exception). Tested in `tests/unit/test_mkf_retrieval.py::
  test_search_before_fit_returns_empty`.
- **Refresh policy:** there is no auto-refresh. The index is rebuilt
  only when callers re-invoke `fit`. Process restart loses all sparse
  state. There is **no Qdrant→BM25 bootstrap** code path.

---

# §5 Hybrid Fusion

**File:** `cipher/mkf/memory_agent/retriever.py`

- Class: `HybridWeightedRetriever` (ADR-0004).
- Inputs: `qdrant_index: QdrantIndex`, `bm25_index: BM25Index`,
  `embedder: EmbeddingModel`, `alpha: float = 0.5`.
- Strategy: **weighted linear combination**, not RRF.

## §5.1 Algorithm (`retrieve(query, top_k=5)`)

1. `query_vec = embedder.encode_query(query)`.
2. **Over-fetch** `top_k * 2` from each side:
   - `vector_results = qdrant.search(query_vec, top_k=top_k * 2)`
   - `bm25_results   = bm25.search(query, top_k=top_k * 2)`
3. Build `doc_scores: dict[str, {vector_score, bm25_score, metadata}]`
   keyed by **document text** (not by stable ID — see §7).
4. Merge BM25 hits into the same dict; new docs get `vector_score=0`.
5. **Normalise BM25** by dividing by `max_bm25` across the merged set
   (`or 1.0` to avoid divide-by-zero).
6. Combine: `combined = α · vector_score + (1 - α) · norm_bm25`.
7. Sort descending, return first `top_k` `RetrievalResult` items with
   `source="hybrid"`.

## §5.2 Score domain

- `vector_score` ∈ `[-1, 1]` (Qdrant COSINE on normalised vectors,
  typically `[0, 1]`).
- `norm_bm25` ∈ `[0, 1]` by construction.
- `combined` therefore ∈ approximately `[α·-1 + (1-α)·0, 1]`; at `α=0.5`,
  `[-0.5, 1.0]`.

## §5.3 Design notes

- Joining by document text is fragile when the same chunk appears with
  different metadata or when whitespace differs — see §7.
- Vector scores are **not** renormalised, which means at `α=0.5` BM25
  effectively gets a `(1-α)` share of a `[0, 1]` axis while dense gets a
  `α` share of a similar axis — acceptable when both are bounded.

---

# §6 Test Coverage

**File:** `tests/unit/test_mkf_retrieval.py` — covers retrieval components.

- `TestBM25Index`
  - `test_fit_and_search` — fits 4 docs, asserts AUTOSAR query surfaces
    the AUTOSAR doc first.
  - `test_search_before_fit_returns_empty` — empty-state contract.
  - `test_no_results_for_unrelated_query` — filters non-positive scores.
- `TestQdrantIndex` (mocks `QdrantClient`)
  - `test_add_and_search_mocked` — verifies `create_collection` on
    missing collection and `upsert` on `.add`.
  - `test_delete_collection_mocked` — verifies pass-through.
- `TestHybridRetriever`
  - `test_retrieve_combines_scores` — mocks embedder, qdrant, bm25;
    asserts top doc is the one present in both result sets and that
    `source=="hybrid"`.

**File:** `tests/unit/test_memory_service.py` — schema round-trip only:

- `test_request_defaults` — `top_k=5`, `collection="cipher_memory"`.
- `test_response_round_trip` — Pydantic JSON serialisation.

**Gaps:** no integration test against a live Qdrant (the e2e file
`tests/e2e/test_live_infra.py` is matched by grep but its MKF coverage
was not opened here — verify before claiming integration coverage).
No latency/recall benchmarks. No test for `_deps.get_retriever` caching.

---

# §7 TODOs

1. **`QdrantIndex.add` ignores `ids`** (`qdrant_index.py` L51). Replace
   `enumerate(...)` with the caller-supplied `ids` list; today every
   `add` call **overwrites** points 0..N-1 in the collection.
2. **Persist / rebuild BM25 from Qdrant** — currently BM25 is empty on
   every process start; add a `fit_from_collection(qdrant)` bootstrap.
3. **Indexing endpoint** — add `POST /v1/memory/upsert` (chunk, embed,
   add to both indices) to match the HLD's RAG path.
4. **Join key in hybrid fuse** — replace document-text keying in
   `retriever.py` with a stable ID (e.g. content hash or Qdrant point
   id) propagated through BM25 results.
5. **Reranker stage** — HLD names `bge-reranker-large` but no
   cross-encoder is wired in.
6. **Graph expansion** — `cipher/memory/` README mentions Memgraph; no
   Memgraph client used inside `cipher/mkf/`.
7. **OTel attributes** — only the FastAPI endpoint is traced; add spans
   inside `HybridWeightedRetriever.retrieve` for `embed`, `qdrant.search`,
   `bm25.search`, `fuse` to make latency attributable.
8. **Config surface** — `α`, `top_k`, model name, Qdrant URL, and
   collection are read from constructor defaults or env vars
   piecemeal; centralise in a typed settings object.
9. **Retriever cache eviction** — `_deps._retrievers` grows unbounded
   keyed by collection name.
10. **Auth/GCL** — service has no auth, no `policy.evaluate()` hook on
    query, no audit trail on indexing.
11. **`vector_size` mismatch** — if `EMBEDDING_MODEL` is changed for an
    existing collection, `_ensure_collection` silently no-ops and the
    next `add` will fail with a dim mismatch. Add explicit guard.
12. **Resolve `cipher/memory/` vs `cipher/mkf/` boundary** — the
    `memory/` package is a stub README declaring intent that overlaps
    with `mkf/`. Decide whether `memory/` is the storage-adapter side
    and `mkf/` the agent-facing side, then document and split
    accordingly.
