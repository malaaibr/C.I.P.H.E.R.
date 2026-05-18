---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# Wrap/Rewrite Decision Matrix — CAR-003: RagLab-Main

- **Reference:** CAR-003 (RagLab-Main — Memory Agent Core)
- **Codebase path:** reference/RAG_Lab-main/
- **Date:** 2026-05-16
- **ADRs referenced:** ADR-0004 (Memory Agent Hybrid RAG), ADR-0001 (LLM Gateway)

---

## Decision Matrix

| Module | Disposition | Integration Risk | Effort | Adapter Shape | Reasoning |
|--------|-------------|-----------------|--------|---------------|-----------|
| `raglab_core/chunking.py` → `FixedSizeChunker` | WRAP | Low | S | Expose via `ChunkerProtocol`; `FixedSizeChunker` as POC default | Clean interface, correct logic |
| `raglab_core/chunking.py` → `RecursiveSplitter` | WRAP | Low | S | Alternative chunker behind same protocol | Configurable option |
| `raglab_core/chunking.py` → `SemanticChunker` | WRAP | Low | S | Deferred to MVP (requires embedding model call) | Nice-to-have for MVP |
| `raglab_core/indexing.py` → `ChromaIndex` | **REWRITE** | **High** | **M** | Implement `QdrantIndex` with identical `add()`/`search()`/`delete_collection()` interface using `qdrant-client` | §1.3 hard constraint — ChromaDB forbidden |
| `raglab_core/indexing.py` → `BM25Index` | WRAP | Low | S | Preserve `fit()`/`search()` API; wrap in adapter with pydantic config | Correct algorithm |
| `raglab_core/indexing.py` → `EmbeddingModel` | WRAP | Low | S | Wrap in `EmbeddingModelAdapter`; model name from env var `MKF_EMBED_MODEL` | Clean interface |
| `raglab_core/retrieval.py` → `DenseRetriever` | WRAP | Low | S | Repoint to QdrantIndex instead of ChromaIndex | One import change |
| `raglab_core/retrieval.py` → `HybridWeightedRetriever` | WRAP | Low | S | Alpha from env `MKF_HYBRID_ALPHA`; dense side uses QdrantIndex | POC retrieval strategy |
| `raglab_core/retrieval.py` → `HybridRRFRetriever` | WRAP | Low | S | Alternative retriever for MVP evaluation | Not POC critical |
| `raglab_core/generation.py` → `OllamaClient` | WRAP | Low | M | Becomes `OllamaDriver` implementing `LLMBackend` Protocol in TRF | ADR-0001 integration; MKF calls via gateway |
| `raglab_core/prompting.py` → `PromptBuilder` | WRAP | Low | S | Preserve `build()`/`build_citation()`; add pydantic config | Clean interface |
| `raglab_core/eval.py` | WRAP | Low | S | Copy to `tests/eval/retrieval_metrics.py` | Evaluation tool |
| `raglab_core/io.py` → `RunWriter` | WRAP | Low | S | Redirect to `tests/fixtures/runs/` | Output path change only |
| `raglab_core/io.py` → `DatasetRegistry` | WRAP | Low | S | Point to `tests/fixtures/legacy/ragtest/` | Path change only |
| Rag33-38 (Graph-RAG) | REFACTOR (MVP) | High | L | Replace NetworkX with Memgraph Cypher; **POC: stub returns `[]`** | §1.3 forbids in-memory graphs; POC defers |
| Rag39-42 (Evaluation) | WRAP | Low | M | Adapt to CIPHER fixture format; local Ollama as judge | No external API calls in CI |
| `datasets/ragtest/` | CARRY-FORWARD | Low | S | Copy to `tests/fixtures/legacy/ragtest/` | Golden test data |

---

## Summary

| Disposition | Count | Total Effort |
|-------------|-------|-------------|
| WRAP | 13 | ~13h |
| REFACTOR | 1 (Graph-RAG, MVP) | L (~3d, deferred) |
| REWRITE | 1 (ChromaIndex→QdrantIndex) | M (~1d) |
| CARRY-FORWARD | 1 (test fixtures) | S |

**Primary risk:** The QdrantIndex REWRITE is the single hardest item. It's well-scoped (3 methods: `add`, `search`, `delete_collection`) but requires Qdrant client knowledge and Docker container setup. Must be validated with the POC exit criterion: Recall@5 ≥ 0.70 on the ragtest golden set.

**POC-critical path from this codebase:**
1. QdrantIndex REWRITE (blocks all retrieval)
2. BM25Index WRAP (needed for hybrid)
3. HybridWeightedRetriever WRAP (the actual POC retrieval)
4. EmbeddingModel WRAP (needed for dense indexing)
5. OllamaClient → OllamaDriver WRAP (needed for generation)
