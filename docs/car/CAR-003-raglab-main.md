# CAR-003: RAG_Lab-Main — Codebase Analysis Report

- **Status:** Accepted
- **Codebase path:** references/RAG_Lab-main/
- **Analysed:** 2026-05-16
- **Reference tier:** PRIMARY

---

## 1. Purpose

This Codebase Analysis Report (CAR) examines the RAG_Lab-Main codebase, a comprehensive experimental RAG (Retrieval-Augmented Generation) pipeline reference library. RAG_Lab-Main is the primary reference for the CIPHER MKF (Memory Agent with Hybrid RAG) layer. It contains 42 standalone applications (Rag00–Rag42) covering every major RAG pipeline stage — chunking, indexing, search, query rewriting, reranking, prompt engineering, generation, memory management, context aggregation, graph-RAG, and evaluation — plus a shared `raglab_core` package that provides reusable pipeline components.

The architectural significance for CIPHER is threefold: (1) `raglab_core.retrieval.HybridWeightedRetriever` provides the exact hybrid dense+sparse retrieval formula (score = alpha*dense + (1-alpha)*BM25) that CIPHER MKF adopts for POC; (2) `raglab_core.generation.OllamaClient` is already compatible with the CIPHER Ollama backend (port 11434); (3) the graph-RAG applications (Rag33–Rag38) demonstrate entity and relation extraction patterns that must be adapted to connect to CIPHER's Memgraph Community instance rather than in-memory graphs.

The primary architectural constraint is that `raglab_core.indexing.ChromaIndex` must be completely rewritten as `QdrantIndex` — ChromaDB is not permitted in CIPHER (§1.3 mandates Qdrant as the vector store).

---

## 2. Module Inventory

### 2.1 raglab_core Package (Shared Library)

| Module | Key Classes / Functions | Role |
|---|---|---|
| `raglab_core/__init__.py` | Package init, version | Package root |
| `raglab_core/config.py` | `RAGConfig`, `load_config(dataset_id, app_id, run_slug, seed)` | Configuration loading and dataclass |
| `raglab_core/chunking.py` | `FixedSizeChunker`, `OverlapChunker`, `RecursiveSplitter`, `SemanticChunker`, `get_chunker(strategy)` | Text chunking strategies |
| `raglab_core/indexing.py` | `ChromaIndex`, `BM25Index`, `EmbeddingModel` | Vector and sparse indexing |
| `raglab_core/retrieval.py` | `DenseRetriever`, `HybridWeightedRetriever(dense_index, bm25_index, alpha)`, `HybridRRFRetriever` | Document retrieval strategies |
| `raglab_core/generation.py` | `OllamaClient(config.llm)` | LLM generation via Ollama |
| `raglab_core/prompting.py` | `PromptBuilder(max_context_tokens)` | Prompt assembly with token budgeting |
| `raglab_core/eval.py` | `calculate_retrieval_metrics(retrieved, golden)` | Retrieval evaluation metrics |
| `raglab_core/io.py` | `RunWriter`, `DatasetRegistry`, `get_registry()` | Experiment I/O and dataset management |
| `raglab_core/logging_utils.py` | `RunTracer`, `print_header(title)`, `print_metrics(metrics)` | Run tracing and console output |

### 2.2 RAG Application Suite (Rag00–Rag42)

#### Chunking Apps (Rag01–Rag06)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag00 | Baseline | No chunking, full-doc retrieval baseline |
| Rag01 | FixedSize | Fixed token-size chunks (no overlap) |
| Rag02 | OverlapSweep | Sweep over overlap sizes 0%–50% |
| Rag03 | RecursiveSplitter | Paragraph → sentence → word recursive split |
| Rag04 | Semantic | Embedding-similarity-based semantic boundaries |
| Rag05 | HierarchicalParentChild | Parent chunk stored separately, child chunks retrieved |
| Rag06 | Agentic | LLM-driven adaptive chunking |

#### Indexing Apps (Rag07–Rag10)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag07 | EmbedModelCompare | Compare multiple embedding models (MiniLM, BGE, E5) |
| Rag08 | MetadataFilter_Pre | Pre-retrieval metadata filtering |
| Rag09 | MetadataFilter_Post | Post-retrieval metadata filtering |
| Rag10 | MultiVector_PerDoc | Multiple embedding vectors per document (summary + chunk) |

#### Search Apps (Rag11–Rag14)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag11 | BM25 | BM25 keyword-only sparse retrieval |
| Rag12 | SemanticDense | Dense embedding-only retrieval |
| Rag13 | HybridWeighted | `score = alpha*dense + (1-alpha)*BM25` weighted combination |
| Rag14 | HybridRRF | Reciprocal Rank Fusion hybrid |

#### Query Rewriting Apps (Rag15–Rag18)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag15 | Direct | No rewriting, direct query pass-through |
| Rag16 | MultiRewrite | Generate N query rewrites, retrieve for each, merge |
| Rag17 | HyDE | Hypothetical Document Embeddings |
| Rag18 | StepBack | Step-back prompting for abstract query expansion |

#### Reranking Apps (Rag19–Rag21)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag19 | None | No reranking baseline |
| Rag20 | CrossEncoder | Cross-encoder neural reranker |
| Rag21 | LLMJudge_Local | Local Ollama LLM as relevance judge/reranker |

#### Prompt Engineering Apps (Rag22–Rag25)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag22 | Stuffing | Concatenate all retrieved chunks into context |
| Rag23 | CitationMode | Force LLM to cite source chunk IDs |
| Rag24 | StructuredAnswer | JSON-structured answer extraction |
| Rag25 | NoContextTrap | Detect and handle "no relevant context" case |

#### Generation Apps (Rag26–Rag28)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag26 | TemperatureSweep | Sweep temperature 0.0–1.0 for generation diversity |
| Rag27 | TopP_TopK | Top-p and top-k sampling parameter sweep |
| Rag28 | TokenBudgetBar | Visual token budget indicator and enforcement |

#### Memory Apps (Rag29–Rag31)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag29 | BufferWindow | Sliding window conversation buffer memory |
| Rag30 | Summary | Summarised conversation memory |
| Rag31 | VectorRecall | Vector-indexed conversation memory retrieval |

#### Context Apps (Rag32)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag32 | MapReduce_SummarizeDocs | Map-reduce summarisation over retrieved document set |

#### Graph-RAG Apps (Rag33–Rag38)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag33 | Graph_Construct_EntitiesOnly | Entity extraction and graph construction (nodes only) |
| Rag34 | Graph_Construct_EntityRelations | Entity + relation extraction (full KG construction) |
| Rag35 | Graph_Query_LocalTraversal | Subgraph traversal for local context retrieval |
| Rag36 | Graph_Query_GlobalThemes | Global theme extraction via graph community detection |
| Rag37 | VectorFirst_ThenWalk | Vector retrieval seeding graph walk |
| Rag38 | Graph_Vs_Vector_Showdown | Side-by-side benchmark: graph-RAG vs vector-only |

#### Evaluation Apps (Rag39–Rag42)

| App | Name | Strategy Demonstrated |
|---|---|---|
| Rag39 | BEIR | BEIR benchmark evaluation against external datasets |
| Rag40 | RAGAS_Local | RAGAS faithfulness/relevance evaluation using local Ollama |
| Rag41 | HumanSideBySide | Human annotation side-by-side comparison tool |
| Rag42 | RegressionSuite | Full regression suite comparing run history |

### 2.3 Test Fixtures

| Path | Contents |
|---|---|
| `datasets/ragtest/docs.jsonl` | Document corpus for integration tests |
| `datasets/ragtest/golden.jsonl` | Golden retrieval answers for evaluation |
| `datasets/ragtest/meta.json` | Dataset metadata (doc count, source, licence) |

---

## 3. Key Classes and Public Interfaces

### 3.1 Configuration (`raglab_core/config.py`)

```python
@dataclass
class RAGConfig:
    dataset_id: str
    app_id: str
    run_slug: str
    seed: int

    # Embedding config
    embeddings: EmbeddingConfig  # model_name, device
    # Retrieval config
    retrieval: RetrievalConfig   # top_k, strategy, hybrid_alpha
    # Chunking config
    chunking: ChunkingConfig     # strategy, chunk_size_tokens, overlap_tokens
    # LLM config
    llm: LLMConfig               # model, context_limit_tokens

def load_config(dataset_id: str, app_id: str, run_slug: str, seed: int) -> RAGConfig: ...
```

### 3.2 Chunking (`raglab_core/chunking.py`)

```python
class FixedSizeChunker:
    def __init__(self, chunk_size_tokens: int): ...
    def chunk(self, text: str) -> list[str]: ...

class RecursiveSplitter:
    def __init__(self, chunk_size_tokens: int, overlap_tokens: int): ...
    def chunk(self, text: str) -> list[str]: ...

class SemanticChunker:
    def __init__(self, embedding_model: EmbeddingModel, threshold: float = 0.8): ...
    def chunk(self, text: str) -> list[str]: ...

def get_chunker(strategy: str, **kwargs) -> FixedSizeChunker | RecursiveSplitter | SemanticChunker:
    """Factory: strategy in {"fixed", "recursive", "semantic", "hierarchical", "agentic"}"""
```

### 3.3 Indexing (`raglab_core/indexing.py`)

```python
class ChromaIndex:
    """ChromaDB-backed vector index. NOT PERMITTED IN CIPHER — must be replaced by QdrantIndex."""
    def __init__(self, collection_name: str, embedding_model: EmbeddingModel): ...
    def add(self, docs: list[str], metadata: list[dict]) -> None: ...
    def search(self, query: str, top_k: int) -> list[dict]: ...
    def delete_collection(self) -> None: ...

class BM25Index:
    """BM25 sparse index using rank_bm25."""
    def __init__(self): ...
    def fit(self, corpus: list[str]) -> None: ...
    def search(self, query: str, top_k: int) -> list[tuple[str, float]]: ...

class EmbeddingModel:
    """Sentence-transformers wrapper."""
    def __init__(self, model_name: str, device: str = "cpu"): ...
    def encode(self, texts: list[str]) -> list[list[float]]: ...
    # Default: model_name="all-MiniLM-L6-v2"
```

### 3.4 Retrieval (`raglab_core/retrieval.py`)

```python
class DenseRetriever:
    def __init__(self, dense_index, embedding_model: EmbeddingModel): ...
    def retrieve(self, query: str, top_k: int) -> list[dict]: ...

class HybridWeightedRetriever:
    """
    Hybrid retrieval: score = alpha * dense_score + (1 - alpha) * bm25_score
    alpha=0.5 gives equal weight to dense and sparse.
    """
    def __init__(self, dense_index, bm25_index: BM25Index, alpha: float = 0.5): ...
    def retrieve(self, query: str, top_k: int) -> list[dict]: ...

class HybridRRFRetriever:
    """Reciprocal Rank Fusion alternative to weighted hybrid."""
    def __init__(self, dense_index, bm25_index: BM25Index, k: int = 60): ...
    def retrieve(self, query: str, top_k: int) -> list[dict]: ...
```

### 3.5 Generation (`raglab_core/generation.py`)

```python
class OllamaClient:
    """Ollama LLM client — compatible with CIPHER Ollama backend at port 11434."""
    def __init__(self, llm_config: LLMConfig): ...
    def generate(self, prompt: str, context_docs: list[str] | None = None) -> str:
        """POST http://localhost:11434/api/generate with model and prompt."""
    def chat(self, messages: list[dict]) -> str:
        """POST http://localhost:11434/api/chat for multi-turn conversation."""
```

### 3.6 Prompting (`raglab_core/prompting.py`)

```python
class PromptBuilder:
    """Assembles retrieved context into LLM prompt with token budget enforcement."""
    def __init__(self, max_context_tokens: int): ...
    def build(self, query: str, retrieved_docs: list[dict], system_prompt: str = "") -> str:
        """Truncates retrieved_docs to fit max_context_tokens before assembling prompt."""
    def build_citation(self, query: str, retrieved_docs: list[dict]) -> str:
        """Citation-mode prompt: forces LLM to reference chunk IDs."""
```

### 3.7 Evaluation (`raglab_core/eval.py`)

```python
def calculate_retrieval_metrics(
    retrieved: list[list[str]],
    golden: list[list[str]],
    k_values: list[int] = [1, 3, 5, 10]
) -> dict[str, float]:
    """
    Returns: {
        "precision@k": float,
        "recall@k": float,
        "ndcg@k": float,
        "mrr": float
    } for each k in k_values
    """
```

### 3.8 I/O (`raglab_core/io.py`)

```python
class RunWriter:
    """Writes experiment results to structured output directory."""
    def __init__(self, run_slug: str, output_dir: str = "runs/"): ...
    def write_results(self, results: dict) -> str:
        """Returns path to written results file."""
    def write_metrics(self, metrics: dict) -> None: ...

class DatasetRegistry:
    """Registry of available RAG test datasets."""
    def get(self, dataset_id: str) -> dict:
        """Returns dataset metadata including docs_path, golden_path."""
    def list(self) -> list[str]: ...

def get_registry() -> DatasetRegistry: ...
```

---

## 4. Data Flow

```
Input Query
    │
    ▼
[Chunking Stage] — get_chunker(strategy).chunk(text) → list[str] (chunks)
    │
    ▼
[Indexing Stage]
    ├── EmbeddingModel.encode(chunks) → list[list[float]] → ChromaIndex.add() [REWRITE→QdrantIndex]
    └── BM25Index.fit(chunks)
    │
    ▼
[Retrieval Stage] — HybridWeightedRetriever.retrieve(query, top_k)
    ├── DenseRetriever: EmbeddingModel.encode(query) → ChromaIndex.search() [REWRITE→QdrantIndex]
    └── BM25Index.search(query, top_k)
    merged: score = alpha * dense_score + (1 - alpha) * bm25_score
    │
    ▼
[Optional: Reranking] — CrossEncoder / LLMJudge_Local (Rag20/Rag21)
    │
    ▼
[Optional: Graph Expansion] — Rag33-38 in-memory graph walk [REFACTOR→Memgraph]
    │
    ▼
[Prompt Assembly] — PromptBuilder.build(query, retrieved_docs)
    │
    ▼
[Generation] — OllamaClient.generate(prompt) → str response
    │
    ▼
[Evaluation] — calculate_retrieval_metrics(retrieved, golden) → metrics dict
    │
    ▼
RunWriter.write_results(results) → runs/{run_slug}/results.json
```

**Graph-RAG data flow (Rag33–Rag38, current — in-memory)**:
```
Documents → Entity extraction (Ollama LLM) → in-memory NetworkX graph
Query → Entity detection → graph.neighbors() → subgraph context → LLM prompt
```

**Graph-RAG data flow (target — Memgraph)**:
```
Documents → Entity extraction (Ollama via TRF LLM Gateway) → Cypher: MERGE (:Entity{name})
Query → Entity detection → Cypher: MATCH (e)-[r]->(t) WHERE e.name IN entities → context
```

---

## 5. External Dependencies

| Dependency | Version | Used By | CIPHER Notes |
|---|---|---|---|
| chromadb | ≥0.4 | raglab_core/indexing.py | NOT PERMITTED — replace with qdrant-client |
| rank_bm25 | ≥0.2.2 | raglab_core/indexing.py | WRAP — BM25 algorithm, keep |
| sentence-transformers | ≥2.6 | raglab_core/indexing.py | WRAP — EmbeddingModel, keep |
| httpx / requests | ≥0.26 | raglab_core/generation.py | WRAP — Ollama HTTP calls |
| tiktoken | ≥0.6 | raglab_core/prompting.py | WRAP — token counting |
| networkx | ≥3.1 | Rag33-38 | REFACTOR — replace with Memgraph Cypher driver |
| beir | ≥2.0 | Rag39 | WRAP for CI eval fixtures |
| ragas | ≥0.1 | Rag40 | WRAP for local RAGAS eval |
| datasets | ≥2.18 | Rag39-42 | WRAP — HuggingFace datasets loader |
| pytest | ≥7.4 | tests/ | WRAP — test framework |
| numpy | ≥1.26 | raglab_core/retrieval.py | Keep |
| scipy | ≥1.12 | raglab_core/retrieval.py | Keep — cosine similarity |
| transformers | ≥4.40 | Rag20 | Keep — CrossEncoder reranker |

**Missing dependencies (debt):**
- `qdrant-client` not present (must add for QdrantIndex)
- `neo4j` (Python driver for Memgraph) not present (must add for graph-RAG)
- `opentelemetry-sdk` not present (no OTel spans)
- `pydantic` v2 not imported (raw dicts / dataclasses throughout)

---

## 6. CIPHER Layer Mapping

| Source Module | CIPHER Layer | CIPHER Target Path | Disposition | Notes |
|---|---|---|---|---|
| `raglab_core/chunking.py` → `FixedSizeChunker` | MKF / memory_agent | `mkf/memory_agent/chunker.py` | WRAP | FixedSizeChunker as default; RecursiveSplitter as configurable option; expose via `ChunkerProtocol` |
| `raglab_core/indexing.py` → `ChromaIndex` | MKF / memory_agent | `mkf/memory_agent/qdrant_index.py` | REWRITE | ChromaDB not permitted (§1.3); implement `QdrantIndex` with identical `add()` / `search()` interface using `qdrant-client`; collection per agent context |
| `raglab_core/indexing.py` → `BM25Index` | MKF / memory_agent | `mkf/memory_agent/bm25_index.py` | WRAP | Preserve `fit()` and `search()` API; wrap in `BM25IndexAdapter` with pydantic v2 config |
| `raglab_core/indexing.py` → `EmbeddingModel` | MKF / memory_agent | `mkf/memory_agent/embedder.py` | WRAP | Wrap in `EmbeddingModelAdapter`; model name read from `MKF_EMBED_MODEL` env var (default `all-MiniLM-L6-v2`) |
| `raglab_core/retrieval.py` → `DenseRetriever` | MKF / memory_agent | `mkf/memory_agent/retriever.py` | WRAP | Repoint to QdrantIndex instead of ChromaIndex |
| `raglab_core/retrieval.py` → `HybridWeightedRetriever` | MKF / memory_agent | `mkf/memory_agent/retriever.py` | WRAP | Alpha-weighted formula is the POC hybrid strategy; alpha=0.5 default, configurable via env `MKF_HYBRID_ALPHA` |
| `raglab_core/generation.py` → `OllamaClient` | TRF / llm_gateway | `trf/mcp_servers/llm_gateway/ollama_driver.py` | WRAP | OllamaClient already targets `http://localhost:11434`; wrap as `OllamaDriver` implementing `LLMBackend` Protocol; no direct Ollama calls from MKF |
| `raglab_core/prompting.py` → `PromptBuilder` | core / memory_client | `core/memory_client/prompt_builder.py` | WRAP | Preserve `build()` and `build_citation()`; add pydantic v2 `PromptBuilderConfig` |
| `raglab_core/eval.py` → `calculate_retrieval_metrics()` | tests / eval | `tests/eval/retrieval_metrics.py` | WRAP | Preserve metric calculation; adapt to CIPHER fixture format (docs.jsonl / golden.jsonl) |
| `raglab_core/io.py` → `RunWriter` | tests / eval | `tests/eval/run_writer.py` | WRAP | Preserve output format; redirect to `tests/fixtures/runs/` |
| `raglab_core/io.py` → `DatasetRegistry` | tests / fixtures | `tests/fixtures/dataset_registry.py` | WRAP | Point to `tests/fixtures/legacy/ragtest/` |
| Rag01 `FixedSizeChunker` pattern | MKF | `mkf/memory_agent/chunker.py` | WRAP | Default strategy for POC |
| Rag13 `HybridWeighted` pattern | MKF | `mkf/memory_agent/retriever.py` | WRAP | POC retrieval strategy (alpha=0.5) |
| Rag33-38 graph construction | MKF / graph_expansion | `mkf/memory_agent/graph_expansion.py` | REFACTOR | Replace in-memory NetworkX graph with Memgraph Community via neo4j Python driver; Cypher queries for entity/relation upsert and subgraph retrieval |
| Rag39 BEIR | tests / eval | `tests/eval/beir_adapter.py` | WRAP | Adapt BEIR harness to CIPHER fixture format |
| Rag40 RAGAS_Local | tests / eval | `tests/eval/ragas_adapter.py` | WRAP | RAGAS faithfulness/relevance using local Ollama; no external API calls |
| Rag41 HumanSideBySide | tests / eval | `tests/eval/human_sbs.py` | WRAP | Adapt annotation tool to CIPHER run format |
| Rag42 RegressionSuite | tests / eval | `tests/eval/regression_suite.py` | WRAP | Compare run history from `tests/fixtures/runs/` |
| `datasets/ragtest/` | tests / fixtures | `tests/fixtures/legacy/ragtest/` | CARRY-FORWARD | Move docs.jsonl, golden.jsonl, meta.json as-is |
| Rag29 BufferWindow | MKF / memory_agent | `mkf/memory_agent/conversation_memory.py` | WRAP | Sliding window; backed by Redis 7 for POC (not in-memory list) |
| Rag30 Summary | MKF / memory_agent | `mkf/memory_agent/conversation_memory.py` | WRAP | Summarised memory variant; Ollama-powered summarisation |
| Rag31 VectorRecall | MKF / memory_agent | `mkf/memory_agent/conversation_memory.py` | WRAP | Vector-indexed recall backed by QdrantIndex |

---

## 7. Architectural Debt

### DEBT-001: ChromaDB Instead of Qdrant (CRITICAL — Hard Constraint Violation)
- **Location**: `raglab_core/indexing.py` — `ChromaIndex` class; used in all Rag00–Rag38 apps
- **Description**: All vector indexing uses ChromaDB. CIPHER §1.3 mandates Qdrant as the exclusive vector store. ChromaDB and Qdrant have incompatible storage formats, APIs, and deployment models.
- **Impact**: Cannot use any RAG app as-is in CIPHER without violating the hard constraint. Blocks all MKF layer integration.
- **Resolution**: REWRITE `ChromaIndex` as `QdrantIndex` implementing identical `add(docs, metadata)` / `search(query, top_k)` interface using `qdrant-client`. Qdrant collection naming: `cipher_{collection_name}`. Deploy Qdrant via Docker Compose service. Target: T-007.

### DEBT-002: In-Memory Graph (Not Memgraph)
- **Location**: `Rag33–Rag38` graph-RAG applications
- **Description**: All graph construction (Rag33, Rag34) and graph queries (Rag35, Rag36, Rag37, Rag38) use in-memory NetworkX graphs. Graphs are not persisted. There is no connection to any graph database.
- **Impact**: Graph state lost between invocations; cannot build a cumulative knowledge graph across documents and sessions; no CIPHER Memgraph integration.
- **Resolution**: REFACTOR graph construction to emit Cypher queries via the neo4j Python driver connected to Memgraph Community (`bolt://localhost:7687`). Entity upsert: `MERGE (:Entity {name: $name, type: $type})`. Relation upsert: `MERGE (a)-[:RELATION {type: $rel}]->(b)`. Graph query: `MATCH (e)-[r*1..2]->(t) WHERE e.name IN $entities RETURN e, r, t`. Target: T related to graph expansion (post-POC MVP milestone).

### DEBT-003: No OpenTelemetry Instrumentation
- **Location**: All of raglab_core and all Rag apps
- **Description**: `opentelemetry-sdk` is not a dependency. No spans, traces, or metrics are emitted.
- **Impact**: No observability for retrieval latency, embedding model performance, LLM generation time.
- **Resolution**: Add `@traced` decorator (from CIPHER `core/otel/tracing.py`) to: `QdrantIndex.add()`, `QdrantIndex.search()`, `BM25Index.search()`, `HybridWeightedRetriever.retrieve()`, `OllamaClient.generate()`. Target: ADR-0008 / T-003.

### DEBT-004: No Pydantic v2 Models
- **Location**: `raglab_core/config.py` (`RAGConfig` as dataclass), all app main() functions
- **Description**: Configuration and result types use Python `@dataclass` or raw dicts. No pydantic v2 validation.
- **Impact**: No runtime type checking; incompatible with CIPHER FastAPI MCP server response models; no schema export for A2A protocol.
- **Resolution**: Convert `RAGConfig` and all sub-configs to pydantic v2 `BaseModel` during WRAP. Add `MemoryQueryRequest` / `MemoryQueryResponse` pydantic models for MKF FastAPI service. Target: T-011 (MemoryAgent service).

### DEBT-005: OllamaClient Makes Direct Calls (Bypasses LLM Gateway)
- **Location**: `raglab_core/generation.py` — `OllamaClient`
- **Description**: `OllamaClient` directly calls `http://localhost:11434/api/generate`. In CIPHER, all LLM calls must route through the TRF LLM Gateway to enable task-class routing, observability, and budget enforcement.
- **Impact**: Direct Ollama calls from MKF bypass the `TaskClassRouter` and produce no OTel spans at the gateway layer.
- **Resolution**: In CIPHER MKF, `OllamaClient` is WRAP'd into `OllamaDriver` at the TRF LLM Gateway. MKF services call the gateway via MCP tool invocation rather than calling Ollama directly. Target: ADR-0001 / T-012.

### DEBT-006: Evaluation Harness Uses External APIs
- **Location**: `Rag39` (BEIR), `Rag40` (RAGAS)
- **Description**: BEIR evaluation downloads datasets from HuggingFace. RAGAS may call external LLM APIs for evaluation (GPT-4 as judge).
- **Impact**: CI pipelines cannot run evaluation tests without internet access or paid API keys.
- **Resolution**: WRAP evaluation adapters to use: (a) CIPHER local fixture files at `tests/fixtures/legacy/ragtest/` for dataset, (b) local Ollama as the RAGAS judge model. No external network calls in CI eval. Target: tests/eval/ tasks.

---

## 8. Forward Brief

This CAR shapes the following Architecture Decision Records (ADRs) and Work Breakdown Structure (WBS) tasks:

| ADR / Task | Trigger from CAR-002 |
|---|---|
| **ADR-0001** (LLM Gateway) | `OllamaClient` is the `OllamaDriver` source; DEBT-005 (direct Ollama calls) drives the need for gateway routing |
| **ADR-0004** (Memory Agent Hybrid RAG) | `HybridWeightedRetriever` formula is the POC retrieval strategy; `ChromaIndex→QdrantIndex` REWRITE is the central decision; alpha=0.5 POC default |
| **ADR-0009** (Graph Expansion) | Rag33-38 in-memory graph patterns → Memgraph Cypher refactor; DEBT-002 defines the migration path |
| **ADR-0010** (Evaluation Harness) | Rag39-42 evaluation suite → CIPHER fixture-adapted eval; DEBT-006 (external APIs) drives local-only constraint |
| **T-007** (QdrantIndex REWRITE) | DEBT-001 (ChromaDB); direct implementation task; hardest CAR-002 integration item |
| **T-008** (BM25Index adapter) | WRAP from `raglab_core.indexing.BM25Index`; straightforward |
| **T-009** (EmbeddingModel adapter) | WRAP from `raglab_core.indexing.EmbeddingModel`; add env-var model name |
| **T-010** (HybridWeightedRetriever adapter) | WRAP; repoint dense side to QdrantIndex |
| **T-011** (MemoryAgent FastAPI service) | New service wrapping all MKF components; pydantic v2 API models |
| **T-012** (OllamaDriver) | WRAP from OllamaClient; implement `LLMBackend` Protocol |

---

## 9. Summary Assessment

**Fitness for CIPHER integration: HIGH (with one mandatory REWRITE)**

RAG_Lab-Main is an exceptionally thorough RAG experimentation suite. The 42-app structure provides battle-tested patterns for every pipeline stage. The `raglab_core` package is well-factored and its interfaces are clean enough to WRAP directly.

The `HybridWeightedRetriever` (Rag13) with `score = alpha*dense + (1-alpha)*BM25` is exactly the formula CIPHER MKF adopts for POC. The `OllamaClient` already targets the correct local Ollama endpoint. The graph-RAG apps (Rag33–38) provide the algorithmic patterns for entity/relation extraction and graph traversal.

The single mandatory REWRITE (ChromaDB → Qdrant) is well-scoped: the `ChromaIndex` interface (`add()`, `search()`, `delete_collection()`) is small and the `QdrantIndex` replacement must match it exactly so that `HybridWeightedRetriever` and `DenseRetriever` require no changes above the index layer.

The graph-RAG refactor (in-memory NetworkX → Memgraph Cypher) is larger but deferred to MVP — for POC the `graph_expansion` stub returns an empty list, allowing the hybrid retrieval path to be validated independently.

**Recommended action**: REWRITE ChromaIndex as QdrantIndex (T-007); WRAP all other raglab_core components; CARRY-FORWARD test fixtures; REFACTOR graph apps to Memgraph in MVP phase; adapt evaluation harness to local-only operation.
