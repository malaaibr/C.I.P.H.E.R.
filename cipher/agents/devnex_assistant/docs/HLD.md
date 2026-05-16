# DevNex Assistant — High-Level Design

> **Document revision:** Sprint 0 complete (2026-05-16)
> Incorporates Sprint 0 gap fixes F-001…F-010, UC 3.1, UC 4.1, UC 4.4,
> ASDLC process integration, and the three-LLM backend architecture.

---

## 1. System Overview

DevNex Assistant is the AI-powered V-cycle workflow engine inside the CIPHER platform.
It automates embedded SWC development from LLD generation through final traceability,
with ISO 26262 safety gates and MISRA-C:2012 compliance review built in.

The system runs as:
- A **PyQt6 desktop application** (`main_gui.py` → `interfaces/gui/`)
- A **Click CLI** (`devnex.py` → `interfaces/cli/`)
- A **library** importable by orchestration harnesses, CI pipelines, and test fixtures

---

## 2. Architectural Style

Six logical layers, strict downward dependency:

```
┌─────────────────────────────────────────────────┐
│  Interface Layer      CLI · PyQt6 GUI            │
├─────────────────────────────────────────────────┤
│  Orchestration Layer  DevNexOrchestrator          │
├─────────────────────────────────────────────────┤
│  Skill Layer          Intent → UC dispatcher     │
├─────────────────────────────────────────────────┤
│  LLM Backend Layer    Ollama · Gemini · GCA      │  ← Sprint 0 new
├─────────────────────────────────────────────────┤
│  Integration Layer    GCA/VS Code WebSocket       │
├─────────────────────────────────────────────────┤
│  Persistence Layer    Config · State · Artifacts │
└─────────────────────────────────────────────────┘
```

---

## 3. Layer Map (Sprint 0 updated)

| Layer | Files | Responsibility |
|---|---|---|
| Entrypoints | `devnex.py`, `main_gui.py` | CLI/GUI bootstrap |
| CLI | `interfaces/cli/cli_commands.py` | `run-stage`, `run-all`, `status`, `config` |
| GUI | `interfaces/gui/**/*.py` | Workflow canvas, config, trace, log, settings, review dialogs |
| Orchestration | `core/orchestrator.py` | V-cycle node dispatch, config validation, artifact naming, GCA retry, ruleset enforcement |
| Workflow engine | `core/workflow_engine.py` | AF.json graph executor (topological sort + serviceId dispatch) |
| Intent/Context | `core/intent_classifier.py`, `core/context_manager.py` | Rule-based input classification |
| Skill registry | `core/skill_registry.py`, `skills/**` | UC-to-handler routing |
| UC 3.1 | `skills/automotive/asil_review_skill.py` | Three-phase ASIL code review pipeline |
| UC 4.1 | `skills/automotive/standards_qa_skill.py` | Hybrid RAG standards Q&A |
| UC 4.4 | `skills/uc4_4/` | RAM overlap detection + ASIL-D gate |
| LLM backends | `gca/vscode_invoker.py`, Ollama REST, Gemini CLI | Three-backend triangle |
| Persistence | `persistence/*.py`, `configs/ruleset.yaml` | Config, state, artifacts, ruleset |
| Errors | `core/errors.py` | Typed exception hierarchy |
| Logging | `core/console_logging.py` | ANSI-coloured structured logs |
| Tests | `tests/*.py` | 169 pytest tests, 100% passing |

---

## 4. Three-LLM Backend Architecture ★ Sprint 0

Each UC uses the backend best suited to its latency/capability profile:

```
User Input
    │
    ├─► TRIAGE (Ollama :11434, local)
    │     Fast classification, violation detection, initial scoring
    │     Model: llama3.2 / mistral (configurable)
    │
    ├─► PLAN (Gemini CLI subprocess)
    │     Structured planning, fix strategy, standards lookup
    │     Invoked as: gemini --model gemini-2.0-flash -p "<prompt>"
    │
    └─► CODE_GEN (GCA via VS Code WebSocket ws://localhost:37778)
          Final code generation, diff production, full context
          Retries: configurable via max_gca_retries (default 3)
```

**Backend selection by UC:**

| UC | TRIAGE (Ollama) | PLAN (Gemini) | CODE_GEN (GCA) |
|---|---|---|---|
| UC 3.1 ASIL Review | Phase 1 — violation detection | Phase 2 — fix plan | Phase 3 — fix diffs |
| UC 4.1 Standards QA | Embedding generation (nomic-embed-text) | — | Answer generation |
| UC 4.4 RAM Overlap | — | — | Report generation (optional) |
| V-cycle S1N1…S9N1 | — | — | Primary LLM for all nodes |

---

## 5. V-Cycle Pipeline (13 nodes)

```
S1N1 ──► S1N2 ──► S1N3 ──► S1N4
  │                           │
  │    LLD Generation         │ Requirement Categorisation
  │    + Workspace Validate   │ + categorize_reqs_v1.md
  │                           ▼
S2N1 ──► S2N2              S2N1
  │                           │
  │    Code Linking            │
  ▼                           ▼
S3N1 ──────────────────────────► LLD_Code_Trace_Matrix.csv
S4N1 ──────────────────────────► HLD_LLD_Trace_Matrix.csv
S5N1 ──────────────────────────► Full_Downstream_Trace.csv
  │
  ▼
S6N1 ──► S7N1 ──► S8N1 ──► S9N1
  │         │        │        │
Test Gen  UTD Gen  UTD Link  Full Trace
```

**Node-to-artifact canonical names (F-001):**

| Node | Output File |
|---|---|
| S1N1 | `{SWC}_TEMP_LLD_updated.csv` |
| S1N4 | `{SWC}_FUNC_req.csv` |
| S2N1 | `updated_{SWC}.c` |
| **S3N1** ★ | **`LLD_Code_Trace_Matrix.csv`** |
| **S4N1** ★ | **`HLD_LLD_Trace_Matrix.csv`** |
| **S5N1** ★ | **`Full_Downstream_Trace.csv`** |
| S7N1 | `{SWC}_UTD.md` |
| S8N1 | `UTD_LLD_Links.json` |
| S9N1 | `Full_Traceability_Matrix.csv` |

---

## 6. Safety and Quality Gates (ASDLC)

Gate model aligned to ISO 26262 ASIL levels:

```
G0 — Workspace valid (F-010) + ruleset loaded (F-009)
G1 — Sprint complete: 100% tests passing
G2 — Artifact filenames match trace_loader contract (F-001)
G3 — ASIL-A/B/QM: WARN allowed, HOLD on violations
G4 — ASIL-B/C: HOLD — manual Safety Engineer sign-off
G5 — ASIL-D: HARD_BLOCK — raises SemanticConflictError, blocks pipeline
```

**Gated nodes:** S1N1, S6N1, S9N1, UC4_4 (from `configs/ruleset.yaml`)

**Review gates (human-in-the-loop):** S1N2, S1N3, S2N2, S6N1

---

## 7. Skill Dispatch Flow

```
User utterance / CLI stage ID
    │
    ▼
IntentClassifier.classify(input)  →  ParsedIntent(intent_type, vcycle_stage, skill_id)
    │
    ▼
SkillRegistry.resolve(skill_id)   →  ISkill instance
    │
    ▼
skill.run(...)                    →  TaskResult
    │
    └── internally calls DevNexOrchestrator.run_node() or UC pipeline
```

**Registered skills (Sprint 0):**

| Skill ID | Class | Intent Type | Sprint |
|---|---|---|---|
| `lld_gen` | `LLDGenSkill` | `RUN_STAGE` | Original |
| `code_link` | `CodeLinkSkill` | `RUN_STAGE` | Original |
| `trace_report` | `TraceReportSkill` | `RUN_STAGE` | Original |
| `test_gen` | `TestGenSkill` | `RUN_STAGE` | Original |
| `full_trace` | `FullTraceSkill` | `RUN_STAGE` | Original |
| `explain` | `ExplainSkill` | `EXPLAIN` | Sprint 0 ★ |
| `free_form` | `FreeFormSkill` | `FREE_FORM` | Sprint 0 ★ |
| `asil_review` | `AsilReviewSkill` | `RUN_STAGE` | Sprint 0 ★ |
| `standards_qa` | `StandardsQASkill` | `QA` | Sprint 0 ★ |
| `uc4_4` | UC4.4 pipeline | `RUN_STAGE` | Sprint 0 ★ |

---

## 8. System Data Flows

### 8.1 Standard V-Cycle Node
```
CLI/GUI trigger
  → DevNexOrchestrator.run_node(node_id)
    → validate_workspace() [F-010]
    → _enforce_critical_globs() [F-009]
    → _run_s*N*()
      → _validate_config(required_keys)
      → _load_prompt(template) + _render_prompt(context)
      → _invoke_with_retry(prompt, files, node_id) [F-002]
        → gca_invoker.invoke_prompt()
          → DevNexGCAInvoker → VS Code WebSocket → GCA
      → write artifact to _artifacts_dir
    → StateStore.set_node_status(node_id, "complete")
```

### 8.2 AF.json Workflow Graph (F-008)
```
DevNexOrchestrator.run_workflow(path, inputs)
  → WorkflowEngine(gca_bridge=gca_invoker, ...)
  → WorkflowEngine.execute()
    → _topological_sort() [Kahn's algorithm]
    → for each node: _resolve_templates() → serviceId dispatch
```

### 8.3 GCA Invocation with Retry (F-002)
```
_invoke_with_retry(prompt, files, node_id, max_retries=3)
  for attempt in 1..max_retries:
    result = gca_invoker.invoke_prompt(prompt, files)
    if result.is_response_valid: return result
    sleep(1)
  raise NodeExecutionError("{node_id}: GCA failed after N attempts")
```

---

## 9. External Boundaries

| Boundary | Endpoint | Used By |
|---|---|---|
| GCA/VS Code WebSocket | `ws://localhost:37778` | All V-cycle nodes, UC 3.1 Phase 3 |
| DevNex HTTP Bridge | `http://127.0.0.1:37778` | WebSocket fallback |
| Ollama REST | `http://localhost:11434` | UC 3.1 Phase 1, UC 4.1 embedding + answer |
| Gemini CLI | subprocess `gemini --model ...` | UC 3.1 Phase 2 |
| Qdrant REST | `http://localhost:6333` | UC 4.1 dense search (optional) |
| GNU linker `.map` | local file | UC 4.4 RAM analysis |
| GNU linker `.ld` | local file | UC 4.4 region parsing |
| Config JSON | `generated_artifacts/config.json` | All nodes |
| Workflow state JSON | `~/.devnex/workflow_state.json` | StateStore |
| Ruleset YAML | `configs/ruleset.yaml` | F-009 critical-glob enforcement |
| GCA registry | `~/.gca_instances.json` | DevNexGCAInvoker |
| GUI settings | `~/.devnex/gui_settings.json` | SettingsManager |

---

## 10. Architectural Risks (Sprint 0 status)

| Risk | Status | Notes |
|---|---|---|
| Orchestrator too large (validation + prompts + GCA + artifact + state) | Open | Modularization planned Sprint 2 |
| Node IDs duplicated across orchestrator, GUI constants, workflow metadata | Open | Single source of truth planned |
| `StateStore` read-modify-write without file lock | Open | Single-process acceptable; lock planned Sprint 2 |
| Invalid config/state JSON silently replaced with defaults | Open | Add validation schema Sprint 1 |
| `gca_invoker` lazy property imports `websocket` — fails in test envs without package | **Mitigated** | Pre-seed `orch._gca_invoker = MagicMock()` in tests |
| `rglob` on FUSE-mounted paths may miss files if pyc mtime stale | **Mitigated** | `touch` + `removeprefix` fix applied |
| Qdrant not available in base install | **Mitigated** | BM25-only fallback; `_qdrant_ok` guards |
| `lstrip("**/")` treated argument as char set, not prefix | **Fixed** | `removeprefix("**/")` in `_enforce_critical_globs` |
