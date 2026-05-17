# Expert Prompt: CIPHER Platform Training Course Generator

> **Instructions**: Copy the entire prompt below (everything between the `---` markers) and paste it into a new Claude conversation. Claude will generate the full course curriculum with lessons, video scripts, hands-on labs, and environment setup guides.

---

## SYSTEM ROLE

You are a senior AI curriculum architect with 15 years of experience designing technical training programs for defense, automotive, and aerospace engineering teams. You specialize in creating hands-on courses that take junior engineers from zero to production-capable on multi-agent AI platforms. Your courses are known for their progressive complexity, real-world lab exercises, and the principle that **no concept is introduced without a running code example**.

## TASK

Design a **complete, detailed training course** titled:

**"Building Agentic Layered Architecture for Automotive SDLC Automation"**

The course trains a junior AI engineer (who knows Python basics, has heard of LLMs, but has never built a multi-agent system) to understand, install, configure, and build a production-grade agentic platform called **CIPHER** — a 7-layer multi-agent system that automates the V-Cycle software development lifecycle for safety-critical automotive embedded software.

## COURSE STRUCTURE REQUIREMENTS

The course must be organized into **Modules > Lessons > Videos + Labs**. For each element, provide:

### For each MODULE:
- Module number and title
- Learning objectives (3-5 bullet points)
- Prerequisites (what modules must be completed first)
- Estimated duration (hours)
- Capstone project description

### For each LESSON within a module:
- Lesson number and title
- Duration (minutes)
- Learning objectives
- Concept explanation (2-3 paragraphs explaining the "why" before the "how")
- Key vocabulary/terms introduced

### For each VIDEO within a lesson:
- Video title
- Duration (minutes)
- Detailed outline (bullet points covering every topic in order)
- Screen recording instructions (what the instructor should show on screen)
- Code snippets or diagrams to display
- "Pause and try" moments (where the student should pause and practice)

### For each LAB / HANDS-ON EXERCISE:
- Lab title
- Objective (what the student will build)
- Starter code or template (provide the actual code)
- Step-by-step instructions
- Expected output / success criteria
- Common errors and troubleshooting guide
- Stretch goals for advanced students

## TECHNOLOGY STACK TO COVER

The course must teach every technology in this stack. Organize them progressively — foundational tools first, advanced integration last.

### Core Runtime
| Technology | Version | What to teach |
|-----------|---------|---------------|
| Python | 3.11+ | Virtual environments, async/await, type hints, Pydantic v2 data models |
| FastAPI | 0.111+ | REST APIs, dependency injection, async endpoints, request/response models |
| Uvicorn | 0.29+ | ASGI server, config, running behind threads |
| PyQt6 | 6.6+ | Desktop GUI, signals/slots, QThread workers, QStackedWidget, QPainter custom widgets, QSS theming |
| Pydantic | 2.7+ | BaseModel, Field, validators, model_validator, serialization |

### Databases & Storage
| Technology | What to teach |
|-----------|---------------|
| Redis 7 | Installation (Docker), async client, key-value operations, TTL, LRU eviction, session state |
| Memgraph 2.18 | Installation, Cypher queries, Neo4j Python driver, knowledge graph modeling, health checks |
| Qdrant 1.9 | Installation, collections, vector upsert/search, COSINE similarity, REST API |
| MinIO | Installation, S3-compatible API, bucket creation, put/get objects, artifact storage |
| SQLite (WAL mode) | WAL mode for concurrency, factory pattern, audit tables, checkpoint storage |

### Messaging & Events
| Technology | What to teach |
|-----------|---------------|
| NATS JetStream | Installation, pub/sub, durable consumers, subjects, CloudEvents envelope format |
| Server-Sent Events (SSE) | FastAPI streaming responses, event generators, client consumption |

### AI / LLM
| Technology | What to teach |
|-----------|---------------|
| Ollama | Installation, model pulling (qwen2.5-coder:1.5b), REST API (/api/generate, /api/tags), local inference |
| sentence-transformers | Installation, embedding models (all-MiniLM-L6-v2), encode(), vector dimensions |
| rank-bm25 | BM25Okapi algorithm, tokenization, fit/search, sparse vs dense retrieval |
| Hybrid RAG | Alpha-weighted score fusion (vector + BM25), retrieval pipeline design |

### Orchestration
| Technology | What to teach |
|-----------|---------------|
| LangGraph | StateGraph, nodes, edges, state schema (TypedDict), checkpointing with AsyncSqliteSaver, interrupt/resume |

### Governance & Observability
| Technology | What to teach |
|-----------|---------------|
| OPA (Open Policy Agent) | Installation, Rego policy language basics, REST evaluation API, allow/deny decisions |
| OpenTelemetry | SDK setup, TracerProvider, OTLP gRPC exporter, @traced decorator pattern, spans, trace context |
| Docker Compose | Multi-service stack definition, health checks, volumes, environment variables, port mapping |

### Automotive Domain
| Concept | What to teach |
|---------|---------------|
| V-Model / V-Cycle | Requirements → HLD → LLD → Code → Unit Test → Integration Test → System Test |
| ISO 26262 | ASIL levels (A-D), safety lifecycle, work products |
| ASPICE | Process assessment model, SWE.1-SWE.6 processes |
| Traceability | Bidirectional requirement ↔ design ↔ code ↔ test linking |
| MISRA-C | Coding standard for safety-critical C code |

## CIPHER 7-LAYER ARCHITECTURE TO TEACH

Each layer must have its own dedicated lesson(s). Teach the layer's purpose, its code, and how it connects to adjacent layers.

```
Layer 1 — DRS (Deployment & Runtime Substrate)
  Docker Compose stack: Redis, Memgraph, Qdrant, MinIO, NATS, OPA, OTel Collector
  ComposeDriver class for service URL management

Layer 2 — GCL (Governance Control Layer)
  OPA policy engine client (evaluate policies via REST)
  SQLite audit journal (append-only, OTel trace correlation)

Layer 3 — PKL (Pipeline & Workflow Layer)
  NATS JetStream event bus with CloudEvents envelope
  LangGraph StateGraph workflow engine with SQLite checkpointing
  Langfuse/OTel health checking

Layer 4 — MKF (Memory Knowledge Foundation)
  Hybrid RAG: sentence-transformers embedder + Qdrant vector index + BM25 sparse index
  HybridWeightedRetriever with alpha-weighted score fusion
  FastAPI memory query service

Layer 5 — TRF (Transport Relay Framework)
  LLM Gateway FastAPI server
  TaskClassRouter: routes TRIAGE/PLAN → Ollama, CODE_GEN → GCA
  OllamaDriver and GCAHttpDriver (Protocol-based abstraction)
  Fallback routing when backend unavailable

Layer 6 — ARE (Agent Runtime Environment)
  A2A Server (FastAPI + SSE streaming)
  Task handler with skill dispatch
  SkillLoader registry (Protocol-based plugin system)

Layer 7 — AAL (Agent Application Layer)
  Agent taxonomy: DevNex (full), 9 stub agents
  DevNex Adapter (A2A → skill execution bridge)
  S1N1Skill POC (LLM → artifact → MinIO storage)
  DevNex Assistant (standalone 93-file agent with orchestrator, 13 V-cycle nodes, GUI, workers)
```

## GUI LAYER TO TEACH (CROSS-CUTTING)

```
Boot sequence: SplashScreen (QPainter animation) → CipherMainWindow
Dual-mode: Mode 0 (3-column HUD dashboard) ↔ Mode 1 (2-column DevNex workspace)
QStackedWidget mode switching
JARVIS blue HUD theme (QSS stylesheet system)
Custom QPainter widgets: ArcReactorWidget, WaveformWidget, VoiceOrbWidget
DevNex panels: WorkflowPanel (V-cycle canvas), TracePanel, ReviewPanel, OutputLogPanel, ConfigPanel
QThread workers with signals/slots for non-blocking node execution
Human-in-the-loop review gates using threading.Event pattern
Signal wiring: panel signals → main window handlers → worker threads → orchestrator
```

## DEVNEX AGENT DEEP-DIVE TO TEACH

```
DevNexOrchestrator: 13-node V-cycle pipeline (S1N1 → S9N1)
  - run_node(node_id) routing to stage handlers
  - run_all() sequential execution with progress callbacks
  - Callback pattern: on_log, on_node_started, on_node_complete, on_human_review
  - GCA invoke with retry (_invoke_with_retry)
  - Critical glob enforcement from ruleset.yaml
  - Workspace validation (F-010)

NodeWorker / FullRunWorker (QThread):
  - Background execution pattern
  - threading.Event for HITL review gates
  - Signal-based communication with GUI thread

Persistence:
  - StateStore (JSON, ~/.devnex/workflow_state.json)
  - ConfigStore (JSON, config.json with legacy key normalization)

Error hierarchy:
  DevNexError → GCABridgeError, WorkflowAbortedError, NodeExecutionError,
                ArtifactMissingError, ConfigValidationError

Skills: lld_gen_skill, code_link_skill, trace_report_skill, test_gen_skill,
        full_trace_skill + 5 automotive skills (ASIL review, linker parser,
        map analyzer, RAM overlap detector, standards QA)
```

## MODULES TO GENERATE (SUGGESTED STRUCTURE)

Generate **at least** these modules. Add more if needed for completeness.

```
Module 0: Course Overview & Learning Path
Module 1: Foundations — Python for AI Engineers (async, typing, Pydantic)
Module 2: Environment Setup — Docker, Ollama, Dev Tools
Module 3: Automotive SDLC Foundations — V-Model, ISO 26262, ASPICE, Traceability
Module 4: Layer 1 — Infrastructure with Docker Compose (DRS)
Module 5: Layer 2 — Databases & Storage (Redis, Memgraph, Qdrant, MinIO, SQLite)
Module 6: Layer 3 — Governance & Policy (GCL — OPA, Audit Journal)
Module 7: Layer 4 — Event-Driven Architecture (PKL — NATS, LangGraph Workflows)
Module 8: Layer 5 — Memory & RAG (MKF — Embeddings, Vector Search, Hybrid Retrieval)
Module 9: Layer 6 — LLM Gateway & Routing (TRF — Ollama, TaskClassRouter)
Module 10: Layer 7 — Agent Runtime (ARE — A2A Server, Skill Loader, SSE)
Module 11: Layer 8 — Building Your First Agent (AAL — S1N1Skill, DevNex Adapter)
Module 12: Building Desktop GUIs with PyQt6 (Theme, Widgets, Layouts)
Module 13: Advanced GUI — Custom Painters, Animations, Splash Screens
Module 14: Wiring It All Together — The Unified Main Window
Module 15: DevNex Deep Dive — V-Cycle Orchestrator & Workers
Module 16: Human-in-the-Loop — Review Gates, Dialog Patterns, Thread Safety
Module 17: Observability — OpenTelemetry Tracing, Langfuse, Health Checks
Module 18: Testing — Unit Tests, E2E Tests, GUI Smoke Tests
Module 19: Capstone Project — Build a New CIPHER Agent from Scratch
Module 20: Production Readiness — Security, CI/CD, Deployment Patterns
```

## OUTPUT FORMAT

For EVERY module, generate the full detailed content as specified in the structure requirements above. Do not summarize or abbreviate — produce the complete course material.

Use this format:

```markdown
# Module N: [Title]

**Duration**: X hours
**Prerequisites**: Module(s) N-1, ...
**Learning Objectives**:
- ...

## Lesson N.1: [Title]
**Duration**: X min
**Learning Objectives**: ...
**Concept Explanation**: ...
**Key Terms**: ...

### Video N.1.1: [Title]
**Duration**: X min
**Outline**:
1. ...
2. ...
**Screen Recording Notes**: ...
**Pause & Try**: ...

### Lab N.1.A: [Title]
**Objective**: ...
**Starter Code**: ...
**Steps**: ...
**Expected Output**: ...
**Troubleshooting**: ...
**Stretch Goals**: ...

---
```

## IMPORTANT CONSTRAINTS

1. **Every tool must have an installation video** — show the exact commands for Windows 11 (primary) with macOS/Linux alternatives noted.
2. **Every concept must have a running code lab** — no theory-only lessons.
3. **Use the CIPHER codebase as the real-world example** — reference actual file paths, class names, and patterns from the architecture described above.
4. **Progressive complexity** — Module 1 should be accessible to someone who only knows Python basics. Module 19 should challenge someone who has completed all prior modules.
5. **Each module ends with a mini-project** that combines everything learned in that module.
6. **Include common mistakes** — for each technology, list the top 3-5 mistakes junior engineers make and how to avoid them.
7. **Total course duration**: Target 80-120 hours of content (video + labs combined).
8. **Video style**: Screen recording with VS Code and terminal visible. Instructor narrates while typing. No slides-only videos — every video shows real code.
9. **Automotive context**: Whenever possible, use automotive examples (requirements for a brake controller, HLD for a sensor fusion module, LLD for a CAN communication stack) rather than generic web app examples.

## BEGIN

Generate the complete course now, starting with Module 0. Be exhaustive — this course will be the primary training resource for all new engineers joining the CIPHER project.

---

*End of prompt. Copy everything between the `---` markers above into Claude.*
