# CIPHER — Low-Level Design Document

**Version**: 1.0.0-MVP
**Date**: 2026-05-17
**Audience**: Junior AI Engineers, new team members
**Scope**: Full platform — every layer, agent, and technology component

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Layer 1 — DRS (Deployment & Runtime Substrate)](#3-layer-1--drs)
4. [Layer 2 — GCL (Governance Control Layer)](#4-layer-2--gcl)
5. [Layer 3 — PKL (Pipeline & Workflow Layer)](#5-layer-3--pkl)
6. [Layer 4 — MKF (Memory Knowledge Foundation)](#6-layer-4--mkf)
7. [Layer 5 — TRF (Transport Relay Framework)](#7-layer-5--trf)
8. [Layer 6 — ARE (Agent Runtime Environment)](#8-layer-6--are)
9. [Layer 7 — AAL (Agent Application Layer)](#9-layer-7--aal)
10. [Core Module — Schemas & Adapters](#10-core-module)
11. [GUI Layer — User Interface](#11-gui-layer)
12. [DevNex Agent — Full LLD](#12-devnex-agent)
13. [Data Flow Diagrams](#13-data-flow-diagrams)
14. [Deployment Architecture](#14-deployment-architecture)

---

## 1. System Overview

CIPHER (V-Cycle Intelligence Platform) is a **multi-agent desktop application** for automotive software verification. It follows a 7-layer architecture where each layer is an independent Python package under `cipher/`.

### Architecture Diagram

```
+------------------------------------------------------------------+
|                        GUI Layer (PyQt6)                         |
|  CipherMainWindow  |  Dashboard  |  DevNex Panels  |  Voice     |
+------------------------------------------------------------------+
           |                    |                    |
+------------------------------------------------------------------+
|                 AAL — Agent Application Layer                    |
|    DevNex Adapter  |  S1N1 Skill  |  Future Agents (stubs)      |
+------------------------------------------------------------------+
           |                    |                    |
+------------------------------------------------------------------+
|                 ARE — Agent Runtime Environment                  |
|       A2A Server (:8100)  |  Skill Loader / Registry            |
+------------------------------------------------------------------+
           |                    |                    |
+----------+--------+----------+----------+---------+--------------+
|   TRF Layer       |   PKL Layer         |   MKF Layer            |
| LLM Gateway       | NATS Event Bus      | Hybrid RAG Retriever   |
| (:8200)            | Workflow Engine      | Vector + BM25 Index    |
| Ollama + GCA       | Langfuse Check       | Qdrant + Embeddings    |
+--------------------+---------------------+------------------------+
           |                    |                    |
+------------------------------------------------------------------+
|                 GCL — Governance Control Layer                   |
|           OPA Policy Engine  |  SQLite Audit Journal             |
+------------------------------------------------------------------+
           |                    |                    |
+------------------------------------------------------------------+
|                 Core Module — Schemas & Adapters                 |
|  TaskContract | AgentCard | CloudEvent | Redis | Memgraph |      |
|  Qdrant | MinIO | SQLite | OTel Tracing | ComposeDriver         |
+------------------------------------------------------------------+
           |                    |                    |
+------------------------------------------------------------------+
|                 DRS — Deployment & Runtime Substrate             |
|  Docker Compose: Redis, Memgraph, Qdrant, MinIO, NATS, OPA,     |
|  OTel Collector, Ollama                                          |
+------------------------------------------------------------------+
```

---

## 2. Technology Stack

### 2.1 Runtime & Languages

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | All backend and GUI code |
| GUI Framework | PyQt6 | 6.6+ | Desktop application |
| Web Framework | FastAPI | 0.111+ | REST APIs (LLM Gateway, A2A Server) |
| ASGI Server | Uvicorn | 0.29+ | Serves FastAPI apps |
| Data Validation | Pydantic | 2.7+ | Request/response models |

### 2.2 Databases & Storage

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| Working Memory | Redis 7 | 6379 | Key-value cache, session state |
| Knowledge Graph | Memgraph 2.18 | 7687 | Traceability graph (Neo4j protocol) |
| Vector Store | Qdrant 1.9 | 6333 | Embedding storage for RAG |
| Artifact Store | MinIO | 9000 | S3-compatible object storage |
| Local State | SQLite (WAL) | file | Audit journal, checkpoints, cipher.db |

### 2.3 Messaging & Events

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| Event Bus | NATS JetStream | 4222 | CloudEvents pub/sub |
| Task Streaming | SSE (Server-Sent Events) | — | Real-time task progress |

### 2.4 AI / LLM

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| Local LLM | Ollama | 11434 | Local inference (qwen2.5-coder:1.5b) |
| Code Gen | GCA Bridge (VS Code) | 37778 | VS Code extension for code generation |
| Embeddings | sentence-transformers | — | Text embeddings for RAG |
| Sparse Search | rank-bm25 | — | BM25 keyword matching |

### 2.5 Governance & Observability

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| Policy Engine | OPA (Open Policy Agent) | 8181 | Authorization & compliance |
| Tracing | OpenTelemetry + OTLP | 4317 | Distributed tracing |
| LLM Observability | Langfuse | 3000 | LLM call monitoring |

### 2.6 Workflow Orchestration

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent Orchestration | LangGraph | StateGraph-based multi-agent workflows |
| Checkpointing | AsyncSqliteSaver | Workflow state persistence |
| V-Cycle Engine | Custom (DevNexOrchestrator) | 13-node sequential pipeline |

---

## 3. Layer 1 — DRS (Deployment & Runtime Substrate)

**Module**: `deploy/local/`
**Purpose**: Infrastructure provisioning and service orchestration.

### 3.1 Docker Compose Stack

**File**: `deploy/local/docker-compose.yml`

All services run on localhost with port forwarding. Each service has health checks for readiness probes.

```
┌──────────────────────────────────────────────────────┐
│              Docker Compose Stack                    │
│                                                      │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────┐ │
│  │  Redis   │  │ Memgraph │  │ Qdrant │  │  MinIO │ │
│  │  :6379   │  │  :7687   │  │ :6333  │  │ :9000  │ │
│  └─────────┘  └──────────┘  └────────┘  └────────┘ │
│                                                      │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐ │
│  │  NATS   │  │   OPA    │  │   OTel Collector    │ │
│  │  :4222   │  │  :8181   │  │  :4317 (gRPC)      │ │
│  └─────────┘  └──────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 3.2 Compose Driver

**File**: `cipher/core/substrate/compose_driver.py`

**Class**: `ComposeDriver`
- Dataclass holding all service URLs and ports
- `ComposeConfig` bundles: project_name, compose_file path, data_dir
- Properties expose each service endpoint: `redis_url`, `memgraph_uri`, `qdrant_url`, `minio_endpoint`, `nats_url`, `opa_url`, `otel_endpoint`
- Environment-variable backed with sensible defaults

```python
@dataclass
class ComposeDriver:
    redis_url:      str = "redis://127.0.0.1:6379/0"
    memgraph_uri:   str = "bolt://127.0.0.1:7687"
    qdrant_url:     str = "http://127.0.0.1:6333"
    minio_endpoint: str = "127.0.0.1:9000"
    nats_url:       str = "nats://127.0.0.1:4222"
    opa_url:        str = "http://127.0.0.1:8181"
    otel_endpoint:  str = "http://127.0.0.1:4317"
```

### 3.3 Service Configuration Details

| Service | Image | Config | Volume |
|---------|-------|--------|--------|
| Redis | redis:7-alpine | appendonly, 256MB LRU | ./data/redis |
| Memgraph | memgraph:2.18.1 | log-to-stderr | named volume |
| Qdrant | qdrant:v1.9.7 | gRPC on 6334 | ./data/qdrant |
| MinIO | minio/minio:latest | cipher/cipherdev123 | ./data/minio |
| NATS | nats:2.10-alpine | JetStream enabled (-js) | none |
| OPA | opa:0.62.1 | /policies mounted | ./policies (read-only) |
| OTel | otel-collector-contrib:0.96.0 | otel-config.yaml | config mount |

---

## 4. Layer 2 — GCL (Governance Control Layer)

**Module**: `cipher/gcl/`
**Purpose**: Policy enforcement and audit logging for compliance.

### 4.1 OPA Policy Client

**File**: `cipher/gcl/policy_engine/opa_client.py`

**Class**: `OpaClient`

```python
class OpaClient:
    def __init__(self, base_url="http://127.0.0.1:8181"):
        self._url = base_url
        self._client = httpx.AsyncClient()

    async def health_check(self) -> bool:
        # GET /health → True if status 200

    async def evaluate(self, policy_path: str, input_data: dict) -> dict:
        # POST /v1/data/{policy_path}
        # Body: {"input": input_data}
        # Returns: {"result": {"allow": True/False, ...}}
```

**How it works**:
1. OPA runs as a Docker sidecar with Rego policies mounted
2. Before any agent action, the orchestrator calls `opa_client.evaluate()`
3. OPA evaluates the Rego policy against the input context
4. Returns allow/deny decision

**Policy file**: `deploy/local/policies/poc_allow_all.rego` — POC policy that allows everything.

### 4.2 Audit Journal

**File**: `cipher/gcl/audit_journal/journal.py`

**Class**: `AuditJournal`

```python
class AuditJournal:
    def __init__(self, db_path="~/.cipher/audit.db"):
        # Creates SQLite DB with WAL mode
        # Table: audit_log (id, timestamp, agent_id, action, detail_json, trace_id, span_id)

    @traced(name="audit.record")
    async def record(self, agent_id: str, action: str, detail: dict):
        # INSERT into audit_log with current OTel trace/span IDs

    async def query(self, agent_id=None, action=None, since=None) -> list[dict]:
        # SELECT from audit_log with optional filters
```

**Key design**: Append-only — records are never deleted or modified. Each record captures the OpenTelemetry trace_id and span_id for correlation with distributed traces.

---

## 5. Layer 3 — PKL (Pipeline & Workflow Layer)

**Module**: `cipher/pkl/`
**Purpose**: Event-driven messaging, workflow orchestration, and observability.

### 5.1 NATS Event Bus

**File**: `cipher/pkl/event_bus/nats_bus.py`

**Class**: `NatsBus`

```python
class NatsBus:
    def __init__(self, url="nats://127.0.0.1:4222"):
        self._nc = None  # NATS connection
        self._js = None  # JetStream context

    async def connect(self):
        self._nc = await nats.connect(self._url)
        self._js = self._nc.jetstream()

    async def publish(self, subject: str, event: CloudEvent):
        # Serialize CloudEvent to JSON bytes
        # Publish to JetStream subject

    async def subscribe(self, subject: str, durable: str, handler: Callable):
        # Subscribe with durable consumer (survives reconnects)
        # handler receives CloudEvent objects
```

**CloudEvent envelope** (from `cipher/core/schemas/cloud_event.py`):
```python
class CloudEvent(BaseModel):
    id:          str       # UUID
    source:      str       # e.g., "cipher.devnex.s1n1"
    type:        str       # e.g., "node.complete"
    subject:     str       # e.g., "S1N1"
    time:        datetime
    data:        dict      # Payload
    specversion: str = "1.0"
```

### 5.2 Workflow Engine (LangGraph)

**File**: `cipher/pkl/workflow/workflow_engine.py`

**Class**: `WorkflowEngine`

```python
class WorkflowState(TypedDict):
    task: TaskContract
    result: TaskResult | None
    step: str

class WorkflowEngine:
    def __init__(self):
        self._checkpointer = AsyncSqliteSaver(db_path)

    def build_sequential(self, steps: list[str], executors: dict) -> StateGraph:
        # Creates a LangGraph StateGraph with linear step sequence
        # Each step calls executors[step_name](state)
        # Edges: step_1 → step_2 → ... → END

    async def run(self, graph: StateGraph, initial_state: dict) -> dict:
        # Execute graph with checkpointing
        # Returns final state

    async def resume(self, graph: StateGraph, thread_id: str) -> dict:
        # Resume from checkpoint (interrupt recovery)
```

**Key concept**: LangGraph provides a state-machine abstraction. Each node is a function that receives and returns state. The engine handles execution order, checkpointing, and recovery.

### 5.3 Langfuse Health Check

**File**: `cipher/pkl/observability/langfuse_check.py`

Simple HTTP health probes for Langfuse and OTel Collector. Returns boolean availability.

---

## 6. Layer 4 — MKF (Memory Knowledge Foundation)

**Module**: `cipher/mkf/`
**Purpose**: Retrieval-Augmented Generation (RAG) — hybrid vector + keyword memory.

### 6.1 Architecture

```
┌──────────────────────────────────────────────┐
│  POST /v1/memory/query  (FastAPI endpoint)   │
│         │                                    │
│  ┌──────▼──────────────────────────────────┐ │
│  │     HybridWeightedRetriever             │ │
│  │  alpha=0.5 (50% vector, 50% BM25)      │ │
│  │         │                  │             │ │
│  │  ┌──────▼──────┐  ┌───────▼──────┐     │ │
│  │  │ QdrantIndex  │  │  BM25Index   │     │ │
│  │  │ (vectors)    │  │ (keywords)   │     │ │
│  │  └──────┬──────┘  └───────┬──────┘     │ │
│  │         │                  │             │ │
│  │  ┌──────▼──────┐          │             │ │
│  │  │EmbeddingModel│         │             │ │
│  │  │(sentence-    │         │             │ │
│  │  │ transformers)│         │             │ │
│  │  └─────────────┘          │             │ │
│  └───────────────────────────┘             │ │
└──────────────────────────────────────────────┘
```

### 6.2 Embedding Model

**File**: `cipher/mkf/memory_agent/embedder.py`

```python
class EmbeddingModel:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts)

    def encode_query(self, query: str) -> np.ndarray:
        return self._model.encode([query])[0]
```

### 6.3 Vector Index (Qdrant)

**File**: `cipher/mkf/memory_agent/qdrant_index.py`

```python
class QdrantIndex:
    def __init__(self, url="http://127.0.0.1:6333", collection="cipher_memory"):
        self._client = QdrantClient(url=url)
        self._collection = collection

    def ensure_collection(self, vector_size: int):
        # Create collection if not exists, COSINE distance

    def upsert(self, ids: list, vectors: list, payloads: list):
        # Batch upsert points to Qdrant

    def search(self, query_vector: list, top_k: int = 10) -> list:
        # Nearest-neighbor search, returns scored points
```

### 6.4 BM25 Sparse Index

**File**: `cipher/mkf/memory_agent/bm25_index.py`

```python
class BM25Index:
    def __init__(self):
        self._index = None  # BM25Okapi instance
        self._corpus = []

    def fit(self, documents: list[str]):
        # Tokenize and build BM25 index
        tokenized = [doc.lower().split() for doc in documents]
        self._index = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        # Returns (doc_index, score) pairs
```

### 6.5 Hybrid Retriever

**File**: `cipher/mkf/memory_agent/retriever.py`

```python
class HybridWeightedRetriever:
    def __init__(self, qdrant: QdrantIndex, bm25: BM25Index,
                 embedder: EmbeddingModel, alpha: float = 0.5):
        # alpha: weight for vector score (1-alpha for BM25)

    def retrieve(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        # 1. Encode query to vector
        # 2. Search Qdrant (vector similarity)
        # 3. Search BM25 (keyword match)
        # 4. Fuse scores: final = alpha * vector_score + (1-alpha) * bm25_score
        # 5. Sort by fused score, return top_k
```

### 6.6 Memory Service API

**File**: `cipher/mkf/memory_agent/service.py`

```python
# FastAPI endpoint
@app.post("/v1/memory/query")
async def query_memory(req: MemoryQueryRequest) -> MemoryQueryResponse:
    retriever = get_retriever()
    results = retriever.retrieve(req.query, top_k=req.top_k)
    return MemoryQueryResponse(results=results)
```

---

## 7. Layer 5 — TRF (Transport Relay Framework)

**Module**: `cipher/trf/`
**Purpose**: LLM abstraction — routes prompts to the right LLM backend.

### 7.1 Architecture

```
┌──────────────────────────────────────────┐
│  FastAPI  POST /v1/complete              │
│         │                                │
│  ┌──────▼───────────────────────────┐    │
│  │     TaskClassRouter               │    │
│  │  TRIAGE   → OllamaDriver         │    │
│  │  PLAN     → OllamaDriver         │    │
│  │  CODE_GEN → GCAHttpDriver         │    │
│  │  (fallback → OllamaDriver)        │    │
│  └──────┬──────────────┬────────────┘    │
│         │              │                 │
│  ┌──────▼──────┐ ┌─────▼──────────┐     │
│  │OllamaDriver │ │GCAHttpDriver   │     │
│  │:11434       │ │:37778          │     │
│  └─────────────┘ └────────────────┘     │
└──────────────────────────────────────────┘
```

### 7.2 LLM Protocol

**File**: `cipher/trf/mcp_servers/llm_gateway/protocol.py`

```python
class LLMResponse(BaseModel):
    text:       str
    backend_id: str
    model:      str
    tokens_in:  int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0

class LLMBackend(Protocol):
    async def complete(self, prompt: str, context: dict) -> LLMResponse: ...
    async def is_available(self) -> bool: ...
    @property
    def backend_id(self) -> str: ...
```

### 7.3 Ollama Driver

**File**: `cipher/trf/mcp_servers/llm_gateway/ollama_driver.py`

```python
class OllamaDriver:
    def __init__(self, base_url="http://127.0.0.1:11434", model="qwen2.5-coder:1.5b"):
        self._client = httpx.AsyncClient(base_url=base_url)
        self._model = model

    @traced(name="ollama.complete")
    async def complete(self, prompt: str, context: dict) -> LLMResponse:
        # POST /api/generate {"model": ..., "prompt": ..., "stream": false}
        # Returns LLMResponse with text, token counts, latency

    async def is_available(self) -> bool:
        # GET /api/tags → True if model exists
```

### 7.4 GCA HTTP Driver

**File**: `cipher/trf/mcp_servers/llm_gateway/gca_http_driver.py`

```python
class GCAHttpDriver:
    def __init__(self, base_url="http://127.0.0.1:37778"):
        self._client = httpx.AsyncClient(base_url=base_url)

    @traced(name="gca.complete")
    async def complete(self, prompt: str, context: dict) -> LLMResponse:
        # POST /v1/generate {"prompt": ..., "files": ...}

    async def is_available(self) -> bool:
        # GET /health
```

### 7.5 Task Class Router

**File**: `cipher/trf/mcp_servers/llm_gateway/router.py`

```python
class TaskClassRouter:
    def __init__(self):
        self._ollama = OllamaDriver()
        self._gca = GCAHttpDriver()
        self._routing = {
            TaskClass.TRIAGE:   self._ollama,
            TaskClass.PLAN:     self._ollama,
            TaskClass.CODE_GEN: self._gca,
        }

    async def route(self, prompt: str, task_class: TaskClass, context: dict) -> LLMResponse:
        driver = self._routing.get(task_class, self._ollama)
        if not await driver.is_available():
            driver = self._ollama  # Fallback to Ollama
        return await driver.complete(prompt, context)
```

### 7.6 Gateway API

**File**: `cipher/trf/mcp_servers/llm_gateway/server.py`

```python
app = FastAPI(title="CIPHER LLM Gateway")

class CompletionRequest(BaseModel):
    prompt:     str
    task_class: TaskClass = TaskClass.TRIAGE
    context:    dict = {}

@app.post("/v1/complete")
async def complete(req: CompletionRequest) -> CompletionResponse:
    router = get_router()
    response = await router.route(req.prompt, req.task_class, req.context)
    return CompletionResponse(text=response.text, ...)
```

---

## 8. Layer 6 — ARE (Agent Runtime Environment)

**Module**: `cipher/are/`
**Purpose**: Agent-to-Agent communication and skill lifecycle.

### 8.1 A2A Server

**File**: `cipher/are/a2a_server/server.py`

```python
app = FastAPI(title="CIPHER A2A Server")

# In-memory task queue
_tasks: dict[str, TaskContract] = {}
_queues: dict[str, asyncio.Queue] = {}

@app.post("/v1/tasks")
async def submit_task(req: TaskContract) -> dict:
    _tasks[req.task_id] = req
    _queues[req.task_id] = asyncio.Queue()
    # Dispatch to skill asynchronously
    asyncio.create_task(_dispatch(req))
    return {"task_id": req.task_id, "status": "accepted"}

@app.get("/v1/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    return _tasks[task_id].dict()

@app.get("/v1/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    # SSE (Server-Sent Events) stream
    queue = _queues[task_id]
    async def event_generator():
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("status") in ("completed", "failed"):
                break
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 8.2 Task Handler

**File**: `cipher/are/a2a_server/task_handler.py`

```python
@traced(name="a2a.dispatch")
async def handle_task(task: TaskContract, queue: asyncio.Queue):
    loader = get_skill_loader()
    skill = loader.resolve(task.skill_id)
    if skill is None:
        queue.put_nowait({"status": "failed", "error": f"Unknown skill: {task.skill_id}"})
        return
    result = await skill.execute(task)
    queue.put_nowait({"status": result.status, "output": result.output})
```

### 8.3 Skill Loader

**File**: `cipher/are/skill_loader/loader.py`

```python
class Skill(Protocol):
    @property
    def skill_id(self) -> str: ...
    async def execute(self, task: TaskContract) -> TaskResult: ...

class SkillLoader:
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.skill_id] = skill

    def resolve(self, skill_id: str) -> Skill | None:
        return self._skills.get(skill_id)

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())

_loader: SkillLoader | None = None

def get_skill_loader() -> SkillLoader:
    global _loader
    if _loader is None:
        _loader = SkillLoader()
    return _loader
```

---

## 9. Layer 7 — AAL (Agent Application Layer)

**Module**: `cipher/agents/`
**Purpose**: Individual agent implementations that plug into the ARE.

### 9.1 Agent Portfolio

| Agent | Status | Module | Purpose |
|-------|--------|--------|---------|
| DevNex Assistant | Full | `devnex_assistant/` | V-Cycle verification engine (93+ files) |
| DevNex Adapter | Implemented | `devnex/` | A2A bridge to DevNex skills |
| ASIL Reviewer | Stub | `asil_reviewer/` | Automotive safety review |
| Compliance | Stub | `compliance/` | Standards compliance checking |
| Memory Agent | Stub | `memory_agent/` | Knowledge management |
| Planner | Stub | `planner/` | Planning & orchestration |
| Research | Stub | `research/` | Research & analysis |
| Test Agent | Stub | `test_agent/` | Test generation |
| Tool Agent | Stub | `tool_agent/` | Tool integration |
| Traceability | Stub | `traceability/` | Requirements traceability |

### 9.2 DevNex A2A Adapter

**File**: `cipher/agents/devnex/adapter.py`

```python
class DevNexAdapter:
    @property
    def skill_id(self) -> str:
        return "devnex_orchestrator"

    @traced(name="devnex.execute", attributes={"layer": "aal"})
    async def execute(self, task: TaskContract) -> TaskResult:
        skill = S1N1Skill()
        return await skill.execute(task)
```

### 9.3 S1N1 Skill (POC)

**File**: `cipher/agents/devnex/skills/vcycle_s1n1/skill.py`

```python
class S1N1Skill:
    @property
    def skill_id(self) -> str:
        return "vcycle_s1n1"

    @traced(name="skill.s1n1.execute")
    async def execute(self, task: TaskContract) -> TaskResult:
        # 1. Route prompt to CODE_GEN via TaskClassRouter
        router = get_router()
        llm_response = await router.route(task.prompt, TaskClass.CODE_GEN, task.context)

        # 2. Store LLD artifact in MinIO
        store = MinioStore()
        store.put_object(f"lld/{task.task_id}.csv", lld_content, "text/csv")

        # 3. Return result with artifact reference
        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED,
            artifact_refs=[f"minio://cipher-artifacts/lld/{task.task_id}.csv"]
        )
```

### 9.4 Tool Abstractions

**Module**: `cipher/tools/`

| Tool MCP | Purpose | Status |
|----------|---------|--------|
| `fs_mcp/` | Filesystem operations | Stub |
| `git_mcp/` | Git/SCM operations | Stub |
| `llm_gateway/` | LLM Gateway bridge | Stub |
| `reqif_mcp/` | Requirements interchange | Stub |
| `vectorcast_mcp/` | VectorCAST integration | Stub |

---

## 10. Core Module — Schemas & Adapters

**Module**: `cipher/core/`
**Purpose**: Shared data models, database clients, and observability.

### 10.1 Task Contract Schema

**File**: `cipher/core/schemas/task_contract.py`

```python
class TaskClass(str, Enum):
    TRIAGE   = "triage"
    PLAN     = "plan"
    CODE_GEN = "code_gen"

class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"

class TaskContract(BaseModel):
    task_id:   str = Field(default_factory=lambda: str(uuid4()))
    skill_id:  str
    prompt:    str
    context:   dict = {}
    status:    TaskStatus = TaskStatus.PENDING

class TaskResult(BaseModel):
    task_id:       str
    status:        TaskStatus
    output:        dict = {}
    error_message: str | None = None
    artifact_refs: list[str] = []
    duration_ms:   float = 0.0
```

### 10.2 Agent Card Schema

**File**: `cipher/core/schemas/agent_card.py`

```python
class SkillDescriptor(BaseModel):
    skill_id:    str
    name:        str
    description: str
    task_classes: list[TaskClass] = []

class AgentCard(BaseModel):
    agent_id:    str
    name:        str
    description: str
    version:     str
    skills:      list[SkillDescriptor] = []
    endpoint:    str = ""  # A2A endpoint URL
```

### 10.3 Artifact Relation Schema

**File**: `cipher/core/schemas/artifact_relation.py`

```python
class RelationType(str, Enum):
    DERIVES_FROM = "derives_from"
    IMPLEMENTS   = "implements"
    TESTS        = "tests"
    TRACES_TO    = "traces_to"
    REVIEWED_BY  = "reviewed_by"

class ArtifactRelation(BaseModel):
    id:          str = Field(default_factory=lambda: str(uuid4()))
    source_id:   str
    target_id:   str
    relation:    RelationType
    confidence:  float = 1.0
    metadata:    dict = {}
```

### 10.4 Database Adapters

#### Redis Client
**File**: `cipher/core/adapters/redis_client.py`

```python
class RedisClient:
    async def connect(self):
        self._pool = redis.asyncio.from_url(self._url)

    async def get(self, key: str) -> str | None
    async def set(self, key: str, value: str, ttl: int | None = None)
    async def delete(self, key: str)
    async def exists(self, key: str) -> bool
```

#### Memgraph Client
**File**: `cipher/core/adapters/memgraph_client.py`

```python
class MemgraphClient:
    def __init__(self, uri="bolt://127.0.0.1:7687"):
        self._driver = neo4j.AsyncGraphDatabase.driver(uri)

    async def health_check(self) -> bool
```

#### MinIO Store
**File**: `cipher/core/adapters/minio_client.py`

```python
class MinioStore:
    def __init__(self, endpoint="127.0.0.1:9000"):
        self._client = Minio(endpoint, access_key, secret_key, secure=False)

    def ensure_bucket(self, name="cipher-artifacts")
    def put_object(self, key: str, data: bytes, content_type: str)
    def get_object(self, key: str) -> bytes
```

#### SQLite Factory
**File**: `cipher/core/adapters/sqlite_factory.py`

```python
def create_cipher_db(path="~/.cipher/cipher.db") -> sqlite3.Connection
def create_audit_db(path="~/.cipher/audit.db") -> sqlite3.Connection
def create_checkpoints_db(path="~/.cipher/checkpoints.db") -> sqlite3.Connection
# All use WAL mode for concurrent safety
```

### 10.5 OpenTelemetry Tracing

**File**: `cipher/core/otel/tracing.py`

```python
def init_tracing(service_name="cipher", endpoint="http://127.0.0.1:4317"):
    # Sets up TracerProvider with OTLP gRPC exporter
    # Registers global tracer

def traced(name: str, attributes: dict = {}):
    # Decorator that wraps function in OTel span
    # Works with both sync and async functions
    # Example: @traced(name="skill.s1n1.execute", attributes={"layer": "aal"})
```

### 10.6 CipherOrchestrator (Mother Node)

**File**: `cipher/core/orchestrator.py`

```python
class CipherOrchestrator:
    def __init__(self):
        self._children: dict[str, Any] = {}
        self._llm_gateway_url = "http://127.0.0.1:8200"
        self._a2a_url = "http://127.0.0.1:8100"

    def register_child(self, name: str, orchestrator: Any)
    def get_child(self, name: str) -> Any | None

    @property
    def devnex(self) -> Any | None  # shortcut for get_child("devnex")

    async def start(self)   # Initialize all children
    async def stop(self)    # Graceful shutdown
```

---

## 11. GUI Layer — User Interface

**Module**: `cipher/gui/`
**Purpose**: PyQt6 desktop application with dual-mode interface.

### 11.1 Boot Sequence

```
python run_poc.py
  │
  ├── Register skills (S1N1Skill)
  ├── Create CipherOrchestrator
  ├── Start LLM Gateway thread (:8200)
  ├── Start A2A Server thread (:8100)
  │
  ├── create_app()
  │     └── QApplication + apply_theme()
  │
  ├── CipherMainWindow()  [constructed but hidden]
  │
  ├── SplashScreen.show()
  │     └── 6s animation → fade → finished signal
  │
  └── _on_splash_done()
        ├── window.show()
        ├── window.raise_() + activateWindow()
        └── app.setQuitOnLastWindowClosed(True)
```

### 11.2 Main Window Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Header Bar (48px)                                          │
│  [ArcReactor] C.I.P.H.E.R  [Mode: HUD]  [Status: Idle]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  QStackedWidget (mode_stack)                                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Index 0: CipherDashboardPanel (HUD Mode)             │  │
│  │  ┌──────────┬──────────────────┬──────────────────┐   │  │
│  │  │  Left    │     Center       │     Right        │   │  │
│  │  │  Nav     │   QStackedWidget │   System Status  │   │  │
│  │  │  List    │   (10 views)     │   Metrics        │   │  │
│  │  │          │                  │   Quick Actions   │   │  │
│  │  │ [DevNex] │                  │                  │   │  │
│  │  └──────────┴──────────────────┴──────────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Index 1: DevNex Workspace (DevNex Mode)              │  │
│  │  ┌────────┬───────────────────────────────────────┐   │  │
│  │  │Sidebar │  QStackedWidget (devnex_stack)        │   │  │
│  │  │(220px) │  ┌─────────────────────────────────┐  │   │  │
│  │  │        │  │ 0: WorkflowPanel (V-cycle)      │  │   │  │
│  │  │[Back]  │  │ 1: TracePanel (graph)           │  │   │  │
│  │  │        │  │ 2: ReviewPanel (findings)       │  │   │  │
│  │  │Workflow│  │ 3: OutputLogPanel (GCA log)     │  │   │  │
│  │  │Trace   │  │ 4: ConfigPanel (SWC config)     │  │   │  │
│  │  │Review  │  │ 5: VoicePanel (voice UI)        │  │   │  │
│  │  │Output  │  └─────────────────────────────────┘  │   │  │
│  │  │Config  │                                       │   │  │
│  │  │Voice   ├───────────────────────────────────────┤   │  │
│  │  │        │  Log Tail (140px) — colored log       │   │  │
│  │  └────────┴───────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Status Bar: C.I.P.H.E.R | ONLINE | A2A :8100 | LLM :8200 │
└─────────────────────────────────────────────────────────────┘
```

### 11.3 Signal Wiring Diagram

```
User clicks "Run S1N1" on WorkflowPanel
  │
  ▼
WorkflowPanel.node_run_requested("S1N1")  ─── PyQt Signal ───►
  │
  ▼
CipherMainWindow._on_node_run_requested("S1N1")
  │
  ├── _get_orchestrator()  [lazy init]
  │     ├── ConfigPanel.get_config() → dict
  │     ├── DevNexRunContext(swc_name, workspace_path)
  │     └── DevNexOrchestrator(run_context)
  │
  ├── NodeWorker(orchestrator, "S1N1")
  │
  ├── _wire_worker(worker)
  │     ├── worker.log_line      → append_log()
  │     ├── worker.node_started  → _on_node_started()
  │     ├── worker.node_complete → _on_node_complete()
  │     ├── worker.review_needed → _on_review_needed()
  │     └── worker.error_occurred → _on_worker_error()
  │
  └── worker.start()  ─── QThread begins ───►
        │
        ▼ (in background thread)
      NodeWorker._execute()
        │
        ├── orchestrator.on_log = lambda → log_line.emit()
        ├── orchestrator.on_node_started = lambda → node_started.emit()
        ├── orchestrator.on_node_complete = lambda → node_complete.emit()
        ├── orchestrator.on_human_review = _handle_human_review
        │
        └── orchestrator.run_node("S1N1")
              │
              ├── _enforce_critical_globs()
              ├── run_context.validate_workspace()
              └── _run_s1n1()
                    ├── Load SWC files from config
                    ├── Build prompt
                    ├── _invoke_with_retry(prompt, files)
                    │     └── gca_invoker.invoke_prompt() or fallback
                    ├── Write artifact to disk
                    └── Return NodeResult(status="complete")
```

### 11.4 Theme Colors Reference

```
Background:      #010a15   (near-black blue)
Panel:           #041624   (dark blue)
Accent:          #00c8ff   (bright cyan)
Cyan alt:        #00ffe5   (turquoise)
Success:         #00ff9d   (green)
Warning:         #ffb700   (amber)
Error:           #ff3a3a   (red)
Muted text:      #2d5f7a   (dim blue-grey)
Primary text:    #b8e8ff   (light blue)
Border:          rgba(0,200,255,0.18)
Active border:   rgba(0,200,255,0.55)
```

---

## 12. DevNex Agent — Full LLD

**Module**: `cipher/agents/devnex_assistant/`
**Purpose**: Complete V-Cycle verification engine with 13 nodes across 9 stages.

### 12.1 Package Structure

```
devnex_assistant/
├── core/                        # Business logic
│   ├── orchestrator.py          # DevNexOrchestrator (750 lines)
│   ├── run_context.py           # DevNexRunContext (Pydantic)
│   ├── errors.py                # Exception hierarchy
│   ├── console_logging.py       # ANSI logging
│   ├── context_manager.py       # Context management
│   ├── file_logger.py           # File-based logging
│   ├── intent_classifier.py     # Natural language intent
│   ├── skill_registry.py        # Skill plugin registry
│   ├── trace_loader.py          # CSV trace graph loader
│   ├── trace_model.py           # Trace graph data model
│   └── workflow_engine.py       # AF.json workflow bridge
│
├── interfaces/
│   ├── cli/
│   │   └── cli_commands.py      # CLI interface
│   └── gui/                     # PyQt6 GUI (23 files)
│       ├── app.py               # QApplication entry
│       ├── main_window.py       # Standalone DevNex window
│       ├── sidebar.py           # Navigation sidebar
│       ├── splash.py            # DevNex splash screen
│       ├── step_indicator.py    # V-cycle progress bar
│       ├── constants.py         # App constants
│       ├── icon.py              # Icon generation
│       ├── settings_dialog.py   # Settings UI
│       ├── settings_manager.py  # Settings persistence
│       ├── config_init_modal.py # First-run config dialog
│       ├── panels/
│       │   ├── workflow_panel.py    # V-cycle canvas + node list
│       │   ├── trace_panel.py       # Trace graph visualization
│       │   ├── review_panel.py      # Review orchestration UI
│       │   ├── output_log.py        # GCA output log
│       │   ├── config_panel.py      # SWC project config
│       │   ├── trace_filter_bar.py  # Trace type filter
│       │   ├── trace_graph_canvas.py # Bezier graph renderer
│       │   └── trace_node_card.py   # Individual trace node
│       ├── styles/
│       │   └── palette.py           # Color constants
│       └── workers/
│           ├── base_worker.py       # QThread abstract base
│           ├── node_worker.py       # Single-node executor
│           ├── full_run_worker.py   # All-nodes executor
│           └── review_worker.py     # Review executor
│
├── skills/                      # V-cycle skill implementations
│   ├── base_skill.py            # Abstract skill base
│   ├── lld_gen_skill.py         # S1N1/S1N4 — LLD generation
│   ├── code_link_skill.py       # S2N1 — Code linking
│   ├── trace_report_skill.py    # S3-S5 — Trace reports
│   ├── test_gen_skill.py        # S6-S8 — Test generation
│   ├── full_trace_skill.py      # S9 — Full trace matrix
│   ├── explain_skill.py         # Natural language explanations
│   ├── free_form_skill.py       # Ad-hoc queries
│   └── automotive/              # Automotive-specific skills
│       ├── asil_review_skill.py     # ASIL safety analysis
│       ├── linker_script_parser.py  # Linker file analysis
│       ├── map_analyzer.py          # Memory map analysis
│       ├── ram_overlap_detector.py  # RAM overlap detection
│       ├── standards_qa_skill.py    # Standards Q&A
│       └── uc4_4_skill.py           # UC4.4 semantic check
│
├── persistence/                 # State management
│   ├── state_store.py           # JSON workflow state
│   ├── config_store.py          # JSON SWC config
│   └── artifact_writer.py       # Artifact file output
│
├── review/                      # Review subsystem
│   ├── review_orchestrator.py   # Review pipeline
│   ├── review_models.py         # Finding data models
│   ├── review_reporter.py       # Report generation
│   ├── artifact_loader.py       # Artifact reading
│   └── prompts/                 # Review prompt templates
│
├── gca/                         # VS Code integration
│   ├── bridge.py                # WebSocket bridge
│   └── vscode_invoker.py        # VS Code command invoker
│
├── gcl/                         # Governance integration
│   └── asil_gate.py             # ASIL gate enforcement
│
├── configs/                     # Configuration files
│   └── ruleset.yaml             # Validation rules
│
└── prompts/                     # LLM prompt templates
    ├── categorize_reqs_v1.md
    ├── lld_code_trace_v1.md
    └── hld_lld_links_v1.md
```

### 12.2 V-Cycle Node Map

```
    S1N1                                              S9N1
   LLD Gen ──►S1N2──►S1N3──►S1N4                Full Trace
      │         HR      HR   Categorize    ┌──── Matrix
      │                        │           │
      ▼                        ▼           │
    S2N1                     S4N1          S8N1
  Code Link ──►S2N2        HLD→LLD ◄─── UTD→LLD
      │         HR          Trace          │
      │                      │             │
      ▼                      ▼             │
    S3N1                   S5N1          S7N1
  LLD→Code               Full DS ◄─── UTD Gen
    Trace                Trace            │
      │                   │               │
      └──────── BOT ──────┘             S6N1
               (code)                  Test Gen
                                      + HR Gate

HR = Human Review gate (requires user approval)
```

### 12.3 DevNexOrchestrator

**File**: `core/orchestrator.py`

```python
class DevNexOrchestrator:
    def __init__(self, run_context: DevNexRunContext,
                 on_log=None, on_node_started=None,
                 on_node_complete=None, on_human_review=None,
                 progress_callback=None):
        self.run_context    = run_context
        self.state_store    = StateStore()
        self.config_store   = ConfigStore()
        self.config         = self.config_store.load()
        self._artifacts_dir = run_context.get_artifacts_path()

    def run_node(self, node_id: str) -> NodeResult:
        # Route to _run_s1n1(), _run_s1n2(), etc.

    def run_all(self, progress_callback=None) -> list[NodeResult]:
        # Execute all 13 nodes in sequence (S1N1 → S9N1)
        # Progress callback: (percent, message)
```

**Node execution flow** (for each node):
1. `on_node_started(node_id)` — notify GUI
2. `_enforce_critical_globs()` — validate required workspace files
3. Load input files from config (e.g., DLT.c, DLT.h)
4. Build prompt from template + file contents
5. `_invoke_with_retry(prompt, files)` — call GCA with retry logic
6. Parse response, write artifacts to `_artifacts_dir`
7. `state_store.set_node_status(node_id, "complete")`
8. `on_node_complete(NodeResult(...))` — notify GUI
9. Return `NodeResult`

### 12.4 Worker Threads

**Human Review Gate Pattern**:

```python
# In NodeWorker (background thread):
def _handle_human_review(self, node_id, message):
    self._review_event.clear()          # Reset event
    self.review_needed.emit(node_id, message)  # Signal GUI
    self._review_event.wait()           # BLOCK until GUI responds
    return self._review_approved

# In CipherMainWindow (GUI thread):
def _on_review_needed(self, node_id, message):
    dlg = ReviewDialog(node_id, message)
    approved = dlg.exec() == Accepted
    self._active_worker.resume(approved)  # Unblock worker

# In NodeWorker:
def resume(self, approved):
    self._review_approved = approved
    self._review_event.set()            # Unblock _handle_human_review
```

### 12.5 Error Hierarchy

```
DevNexError (base)
├── GCABridgeError
│   └── GCANotAvailableError
├── WorkflowAbortedError      (user rejected review gate)
├── NodeExecutionError         (node failed during execution)
├── ArtifactMissingError       (required input file not found)
└── ConfigValidationError      (config.json missing required fields)
```

### 12.6 Persistence

#### StateStore (`~/.devnex/workflow_state.json`)
```json
{
  "node_statuses": {
    "S1N1": "complete",
    "S1N2": "complete",
    "S1N3": "pending",
    ...
  }
}
```

#### ConfigStore (`generated_artifacts/config.json`)
```json
{
  "SWC_name": "DLT",
  "G_SWDD_TEMP": "G_SWDD_TEMP.csv",
  "SWC_name_C": "DLT.c",
  "SWC_name_H": "DLT.h",
  "SWC_name_TEMP_LLD": "DLT_TEMP_LLD.csv",
  "SWC_name_FUNC_req": "DLT_FUNC_req.csv",
  "SWC_nameInspBaseLLD": "DLTInspBaseLLD.csv",
  "SWC_name_HLD": "DLT_HLD.csv",
  "lds_file": "Linkerscript",
  "map_file": "map File",
  "workspace_path": "."
}
```

### 12.7 Review Subsystem

**File**: `review/review_orchestrator.py`

The review subsystem runs 9 review nodes (R1N1-R9N1) that inspect artifacts generated by the V-cycle:

| Review Node | What It Reviews |
|-------------|----------------|
| R1N1 | Artifact completeness check |
| R2N1 | HLD document review |
| R3N1 | LLD document review |
| R4N1 | HLD→LLD traceability |
| R5N1 | LLD→Code traceability |
| R6N1 | Keyword gate (MISRA, coding standards) |
| R7N1 | Unit test document review |
| R8N1 | Unit test report gate |
| R9N1 | Final verdict (APPROVED / CONDITIONAL / REJECTED) |

### 12.8 GCA Integration

**File**: `gca/vscode_invoker.py`

```python
class DevNexGCAInvoker:
    def __init__(self, repo_path: Path):
        self._repo_path = repo_path

    def invoke_prompt(self, prompt: str, files: list) -> GCAResponse:
        # Sends prompt + file contents to VS Code GCA extension
        # via WebSocket bridge on :37778
        # Returns parsed response

    def disconnect(self):
        # Close WebSocket connection
```

---

## 13. Data Flow Diagrams

### 13.1 Task Execution (A2A Path)

```
GUI (CipherShell)
  │  submit_task(prompt, skill_id="vcycle_s1n1")
  ▼
A2A Client (httpx POST)
  │  POST /v1/tasks
  ▼
A2A Server (:8100)
  │  task_handler.handle_task()
  ▼
SkillLoader.resolve("vcycle_s1n1")
  │
  ▼
S1N1Skill.execute(task)
  │
  ├──► TaskClassRouter.route(prompt, CODE_GEN)
  │      │
  │      ├── GCAHttpDriver (:37778) [if available]
  │      └── OllamaDriver (:11434) [fallback]
  │
  ├──► MinioStore.put_object("lld/xxx.csv", content)
  │
  └──► TaskResult(status=COMPLETED, artifact_refs=[...])
         │
         ▼
A2A Server → SSE stream → GUI updates
```

### 13.2 DevNex Node Execution (GUI Path)

```
WorkflowPanel "Run S1N1" click
  │
  ▼
CipherMainWindow._on_node_run_requested("S1N1")
  │
  ├── ConfigPanel.get_config() → {SWC_name: "DLT", ...}
  ├── DevNexRunContext(swc_name="DLT", workspace_path=".")
  ├── DevNexOrchestrator(run_context)
  │
  ├── NodeWorker(orchestrator, "S1N1")
  │     ├── Wires: log_line, node_started, node_complete, review_needed
  │     └── worker.start() → QThread
  │
  └── [In QThread]
      orchestrator.run_node("S1N1")
        ├── Validate workspace
        ├── Load DLT.c, DLT.h, templates
        ├── Build prompt
        ├── GCA invoke (with retry)
        ├── Write LLD artifact
        └── Return NodeResult
              │
              ▼
        node_complete signal → GUI updates:
          ├── WorkflowPanel.set_node_status("S1N1", "done")
          ├── StepIndicator.update_step(0, COMPLETE)
          ├── TracePanel.update_from_state()
          └── Log tail: "Node S1N1 → complete."
```

### 13.3 Memory Query (RAG Path)

```
Agent needs context
  │  POST /v1/memory/query {query: "DLT requirements"}
  ▼
Memory Service (FastAPI)
  │
  ▼
HybridWeightedRetriever.retrieve()
  │
  ├── EmbeddingModel.encode_query() → vector
  │     └── sentence-transformers (all-MiniLM-L6-v2)
  │
  ├── QdrantIndex.search(vector) → [(id, score), ...]
  │     └── Qdrant (:6333) — COSINE similarity
  │
  ├── BM25Index.search(tokens) → [(id, score), ...]
  │     └── In-memory BM25Okapi
  │
  └── Fuse: final = 0.5 * vector_score + 0.5 * bm25_score
        │
        ▼
  Top-K results sorted by fused score
```

---

## 14. Deployment Architecture

### 14.1 Local Development

```
┌────────────────────────────────────────────────┐
│                Windows Desktop                  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  python run_poc.py                        │  │
│  │                                          │  │
│  │  ┌────────────────┐  ┌────────────────┐  │  │
│  │  │ LLM Gateway    │  │ A2A Server     │  │  │
│  │  │ Thread (:8200) │  │ Thread (:8100) │  │  │
│  │  └────────────────┘  └────────────────┘  │  │
│  │                                          │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │ PyQt6 GUI (Main Thread)            │  │  │
│  │  │                                    │  │  │
│  │  │  CipherMainWindow                  │  │  │
│  │  │  ├── Dashboard (Mode 0)            │  │  │
│  │  │  └── DevNex Workspace (Mode 1)     │  │  │
│  │  │       └── NodeWorker threads       │  │  │
│  │  └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  Docker Compose Stack                     │  │
│  │  Redis | Memgraph | Qdrant | MinIO       │  │
│  │  NATS | OPA | OTel Collector             │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  Ollama (:11434)                          │  │
│  │  Model: qwen2.5-coder:1.5b               │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  VS Code + GCA Extension (:37778)         │  │
│  │  (Optional — fallback to Ollama)          │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### 14.2 Thread Architecture

```
Main Thread (PyQt6 Event Loop)
  ├── GUI rendering, user events, signal/slot dispatch
  ├── QTimer callbacks (splash animation, clock, latency)
  └── Signal handlers (_on_node_complete, _on_review_needed, etc.)

Daemon Thread 1: LLM Gateway
  └── uvicorn serving FastAPI on :8200

Daemon Thread 2: A2A Server
  └── uvicorn serving FastAPI on :8100

Worker Thread N: NodeWorker / FullRunWorker (spawned on demand)
  └── DevNexOrchestrator.run_node() or run_all()
      └── May block on threading.Event for human review
```

### 14.3 Port Map

| Port | Service | Protocol |
|------|---------|----------|
| 4222 | NATS | NATS protocol |
| 6333 | Qdrant | HTTP REST |
| 6334 | Qdrant | gRPC |
| 6379 | Redis | Redis protocol |
| 7444 | Memgraph | HTTP |
| 7687 | Memgraph | Bolt (Neo4j) |
| 8100 | A2A Server | HTTP + SSE |
| 8181 | OPA | HTTP REST |
| 8200 | LLM Gateway | HTTP REST |
| 8222 | NATS | HTTP monitoring |
| 9000 | MinIO | S3 API |
| 9001 | MinIO | Web console |
| 11434 | Ollama | HTTP REST |
| 37778 | GCA Bridge | WebSocket |
| 4317 | OTel Collector | gRPC (OTLP) |
| 4318 | OTel Collector | HTTP (OTLP) |

---

## Glossary

| Term | Definition |
|------|-----------|
| **A2A** | Agent-to-Agent — communication protocol between CIPHER agents |
| **ASIL** | Automotive Safety Integrity Level (ISO 26262) |
| **BM25** | Best Matching 25 — probabilistic keyword search algorithm |
| **CloudEvent** | CNCF standard envelope format for event data |
| **GCA** | GitHub Copilot Agent — VS Code extension for code generation |
| **HLD** | High-Level Design document |
| **HITL** | Human-In-The-Loop — review gates requiring user approval |
| **HUD** | Heads-Up Display — the CIPHER dashboard mode |
| **LLD** | Low-Level Design document |
| **MCP** | Model Context Protocol — tool abstraction standard |
| **OPA** | Open Policy Agent — policy-as-code engine |
| **OTel** | OpenTelemetry — observability framework |
| **RAG** | Retrieval-Augmented Generation — combining search with LLM |
| **SSE** | Server-Sent Events — HTTP streaming protocol |
| **SWC** | Software Component — the unit of work in V-cycle |
| **V-Cycle** | V-Model development lifecycle (requirements → design → code → test) |
| **WAL** | Write-Ahead Logging — SQLite concurrent write mode |

---

## Documentation Index

> Added 2026-05-17. The per-layer LLDs decompose the implementation; this master document remains the canonical platform-level LLD. The linked files provide layer-by-layer and agent-by-agent depth.

### Per-Layer LLDs

| Layer | Doc | Coverage |
|-------|-----|----------|
| DRS | [DRS_LLD](layers/DRS_LLD.md) | Compose service inventory, volume layout, env vars |
| GCL | [GCL_LLD](layers/GCL_LLD.md) | OpaClient code, AuditJournal sqlite schema |
| PKL | [PKL_LLD](layers/PKL_LLD.md) | NATS subjects, WorkflowState, CloudEvent schemas |
| MKF | [MKF_LLD](layers/MKF_LLD.md) | Embedder, Qdrant collection, BM25 index, hybrid fusion |
| TRF | [TRF_LLD](layers/TRF_LLD.md) | Router rules, Ollama + GCA drivers, MCP layout |
| ARE | [ARE_LLD](layers/ARE_LLD.md) | A2A endpoints, SkillLoader mechanism, AgentCard schema |
| AAL | [AAL_LLD](layers/AAL_LLD.md) | Agent registration, common patterns |
| GUI | [GUI_LLD](layers/GUI_LLD.md) | Mode-switching, splash lifecycle, QThread workers |
| Core | [Core_LLD](layers/Core_LLD.md) | Schemas, adapters, CipherOrchestrator, OTel |

### Per-Agent Docs

| Agent | Status | Doc |
|-------|--------|-----|
| devnex_assistant | Implemented | [devnex_assistant](agents/devnex_assistant.md) |
| devnex (adapter) | Implemented | [devnex](agents/devnex.md) |
| asil_reviewer | Stub | [asil_reviewer](agents/asil_reviewer.md) |
| compliance | Stub | [compliance](agents/compliance.md) |
| memory_agent | Stub | [memory_agent](agents/memory_agent.md) |
| planner | Stub | [planner](agents/planner.md) |
| research | Stub | [research](agents/research.md) |
| test_agent | Stub | [test_agent](agents/test_agent.md) |
| tool_agent | Stub | [tool_agent](agents/tool_agent.md) |
| traceability | Stub | [traceability](agents/traceability.md) |

### Demo Trial Artifacts

| Artifact | Doc |
|----------|-----|
| AUTOSAR Dio SWS extract | [CAR-004](car/CAR-004-autosar-dio-sws.md) |
| AUTOSAR Port SWS extract | [CAR-005](car/CAR-005-autosar-port-sws.md) |
| AUTOSAR DET SWS extract | [CAR-006](car/CAR-006-autosar-det-sws.md) |
| IoHwAb references (no SWS) | [CAR-007](car/CAR-007-autosar-iohwab-reference.md) |
| SWC Template references (no SWS) | [CAR-008](car/CAR-008-autosar-swc-template-reference.md) |
| Dio-only demo plan | [WBS-0002](wbs/WBS-0002-dio-demo-trial.md) |
| Full Demo (5-component) plan | [WBS-0003](wbs/WBS-0003-full-demo-trial.md) |
| Presenter runbook | [DEMO_RUNBOOK_DIO](DEMO_RUNBOOK_DIO.md) |

