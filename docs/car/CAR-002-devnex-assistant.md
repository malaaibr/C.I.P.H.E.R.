# CAR-002: DevNex Assistant — Agent-001 Codebase Analysis Report

- **Status:** Accepted
- **Codebase path:** reference/devnex_assistant/
- **Analysed:** 2026-05-16
- **Reference tier:** PRIMARY
- **Architectural role:** Agent-001 backend + standalone agent GUI (docks into MainCipher shell)

---

## 0. In-Scope Subdirectories (Mandatory — Anti-Conflation Statement)

This CAR analyses the standalone DevNex Assistant agent codebase — both its backend (V-cycle orchestration, GCA bridge, skills, persistence) and its standalone GUI (which must dock into the MainCipher platform shell as the DevNex panel).

- **In scope:**
  - `core/` — orchestrator, workflow engine, intent classifier, types, tracing
  - `gca/` — GCA bridge (HTTP relay to Bridge VSIX), VS Code invoker
  - `skills/` — V-cycle skill implementations (lld_gen, code_link, trace_report, test_gen, full_trace)
  - `persistence/` — state store, config store, artifact writer
  - `interfaces/gui/` — standalone DevNex GUI (main window, sidebar, panels, workers, styles)
  - `interfaces/cli/` — CLI entry point and commands
  - `review/` — artifact review orchestrator, models, reporter
  - `prompts/` — LLD gen, code link, full trace prompt templates
  - `configs/` — ruleset configuration
  - `tests/` — existing test suite

- **Out of scope (covered by CAR-001):**
  - The MainCipher platform shell GUI at `reference/MainCipherdevnex-assistant/` — that is the shell, not this agent.

---

## 1. Module Inventory

### 1.1 Agent Backend

| File / Module | Role | Lines (approx.) |
|---|---|---|
| `core/orchestrator.py` | `DevNexOrchestrator`: coordinates V-cycle node execution, validates config, dispatches skills | ~220 |
| `core/workflow_engine.py` | `WorkflowEngine`: loads AF.json graphs, topological sort, dispatches by serviceId | ~200 |
| `core/intent_classifier.py` | Regex-based intent→skill classification | ~150 |
| `core/skill_registry.py` | `SkillRegistry.resolve(skill_id)` → skill instance | ~60 |
| `core/run_context.py` | `DevNexRunContext`: dataclass holding SWC context, file paths, stage state | ~80 |
| `core/context_manager.py` | Builds `DevNexRunContext` from config store | ~90 |
| `core/trace_model.py` | `TraceNode`, `TraceEdge`, `TraceGraph` — traceability data model | ~120 |
| `core/trace_loader.py` | Loads trace CSVs into TraceGraph | ~100 |
| `core/errors.py` | `WorkflowAbortedError`, `GCABridgeError`, `GCANotAvailableError`, `NodeExecutionError`, `ConfigValidationError` | ~40 |
| `core/console_logging.py` | Structured console logging with timestamps and caller tracking | ~50 |
| `core/file_logger.py` | File-based run logging | ~60 |
| `gca/bridge.py` | `DevNexBridge`: HTTP POST to Bridge VSIX at `:37778/sendPrompt` | ~80 |
| `gca/vscode_invoker.py` | VS Code workspace launch and instance management | ~120 |
| `skills/base_skill.py` | `BaseSkill` abstract class (execute protocol) | ~30 |
| `skills/lld_gen_skill.py` | LLD generation (S1N1 primary skill) | ~250 |
| `skills/code_link_skill.py` | Code annotation with requirement IDs (S2) | ~150 |
| `skills/trace_report_skill.py` | Traceability report generation (S3-S5) | ~130 |
| `skills/test_gen_skill.py` | VectorCAST .tst file generation (S6) | ~140 |
| `skills/full_trace_skill.py` | Full trace matrix generation (S9) | ~110 |
| `persistence/state_store.py` | JSON-backed workflow state at `~/.devnex/workflow_state.json` | ~70 |
| `persistence/config_store.py` | Project configuration persistence | ~90 |
| `persistence/artifact_writer.py` | Writes generated artifacts to `generated_artifacts/` | ~80 |
| `review/review_orchestrator.py` | Coordinates artifact review workflow | ~120 |
| `review/review_models.py` | Review data models (verdict, issue, checklist) | ~80 |
| `review/review_reporter.py` | Generates review reports | ~90 |
| `review/artifact_loader.py` | Loads artifacts for review | ~60 |
| `prompts/lld_gen_v1.md` | LLD generation prompt template | ~200 |
| `prompts/code_link_v1.md` | Code linking prompt template | ~150 |
| `prompts/full_trace_v1.md` | Full trace prompt template | ~120 |
| `configs/ruleset.yaml` | MISRA/coding standard rule configuration | ~50 |

### 1.2 Agent GUI (Standalone — Must Dock Into Shell)

| File / Module | Role | Lines (approx.) |
|---|---|---|
| `interfaces/gui/app.py` | QApplication setup + launch | ~40 |
| `interfaces/gui/main_window.py` | `MainWindow`: sidebar + step indicator + stacked panels + log tail | ~300 |
| `interfaces/gui/sidebar.py` | Navigation sidebar with agent navigation items | ~80 |
| `interfaces/gui/step_indicator.py` | `StepIndicator`: 9-step V-cycle progress widget (IDLE/RUNNING/DONE/ERROR states) | ~120 |
| `interfaces/gui/splash.py` | Splash screen on startup | ~50 |
| `interfaces/gui/constants.py` | App name, version, dimensions, nav indices, node IDs | ~40 |
| `interfaces/gui/config_init_modal.py` | First-run SWC configuration modal | ~100 |
| `interfaces/gui/settings_dialog.py` | Settings dialog (bridge URL, model selection) | ~80 |
| `interfaces/gui/settings_manager.py` | QSettings-backed persistent settings | ~60 |
| `interfaces/gui/icon.py` | Icon generation/loading | ~30 |
| `interfaces/gui/panels/workflow_panel.py` | V-cycle workflow controls + `ReviewDialog` | ~200 |
| `interfaces/gui/panels/trace_panel.py` | Traceability viewer with graph canvas | ~150 |
| `interfaces/gui/panels/trace_graph_canvas.py` | QPainter-based directed graph visualization | ~180 |
| `interfaces/gui/panels/trace_filter_bar.py` | Filter bar for trace relationships | ~60 |
| `interfaces/gui/panels/trace_node_card.py` | Individual trace node display card | ~70 |
| `interfaces/gui/panels/review_panel.py` | Artifact review panel | ~120 |
| `interfaces/gui/panels/output_log.py` | Output log with color-coded levels | ~80 |
| `interfaces/gui/panels/config_panel.py` | Project configuration panel | ~100 |
| `interfaces/gui/styles/palette.py` | Color palette constants | ~40 |
| `interfaces/gui/workers/base_worker.py` | QThread base with signals | ~50 |
| `interfaces/gui/workers/node_worker.py` | Single-node execution worker | ~70 |
| `interfaces/gui/workers/full_run_worker.py` | Full V-cycle run worker | ~80 |
| `interfaces/gui/workers/review_worker.py` | Review execution worker | ~60 |

### 1.3 Tests

| File | Coverage |
|---|---|
| `tests/test_orchestrator.py` | Orchestrator dispatch, node sequencing |
| `tests/test_gca_bridge.py` | Bridge HTTP mock, error handling |
| `tests/test_state_store.py` | StateStore CRUD, empty/corrupt file handling |
| `tests/test_config_store.py` | ConfigStore load/save |
| `tests/test_trace_model.py` | TraceGraph construction and queries |

---

## 2. Public API Surface

### 2.1 DevNexOrchestrator

```python
@dataclass
class NodeResult:
    node_id: str
    status: str        # "success" | "error" | "review_pending"
    output: str
    artifacts: list[str]
    errors: list[str]

class DevNexOrchestrator:
    def run_node(self, node_id: str, context: DevNexRunContext) -> NodeResult: ...
    def run_all(self, context: DevNexRunContext) -> list[NodeResult]: ...
    def get_node_ids(self) -> list[str]: ...
```

### 2.2 DevNexBridge (GCA)

```python
class DevNexBridge:
    BRIDGE_URL = "http://127.0.0.1:37778"

    @staticmethod
    def send_prompt(prompt: str, attached_files: list[str] | None = None) -> str:
        """POST /sendPrompt → llmResponse string."""
```

### 2.3 WorkflowEngine

```python
class WorkflowEngine:
    def __init__(self, gca_bridge, on_node_start, on_node_complete, on_human_review): ...
    def execute(self, workflow_path: str, inputs: dict[str, str]) -> str: ...
```

### 2.4 StateStore

```python
class StateStore:
    def __init__(self, path: Path | None = None): ...
    def load(self) -> WorkflowState: ...
    def save(self, state: WorkflowState) -> None: ...
```

---

## 3. Internal Dependencies

| Dependency | Version | Used By | Notes |
|---|---|---|---|
| PyQt6 | ≥6.4 | interfaces/gui/ | Agent GUI uses PyQt6 (unlike MainCipher shell which uses PyQt5) |
| requests | ≥2.31 | gca/bridge.py | HTTP POST to Bridge VSIX |
| pyyaml | ≥6.0 | configs/ruleset.yaml | Rule configuration loading |
| pytest | ≥7.4 | tests/ | Test framework |

**Missing dependencies (debt):**
- `pydantic` v2 not imported (raw dataclasses/dicts)
- `opentelemetry-sdk` not imported (no OTel)
- `redis` not imported (JSON file state store)
- `websockets` not imported (bridge uses HTTP, not WebSocket — see §3 note)

**Critical architecture note:** This `DevNexBridge` uses **HTTP POST** to a Bridge VSIX at `:37778`, NOT direct WebSocket to GCA. The Bridge VSIX running inside VS Code internally relays to GCA. This is architecturally different from the MainCipher version (CAR-001's backend) which uses direct WebSocket. CIPHER must reconcile these two bridge patterns in ADR-0002.

---

## 4. State & Side Effects

| What | Where | Violation? |
|---|---|---|
| Workflow state | `~/.devnex/workflow_state.json` | Yes — §1.3 mandates Redis for working memory |
| Generated artifacts | `generated_artifacts/` directory | Partially — must move to MinIO in CIPHER |
| Config | `~/.devnex/config.json` (via ConfigStore) | Partially — must use SecretFabric for secrets |
| Run logs | `generated_artifacts/logs/` | OK — but should also emit to Langfuse |
| Network | HTTP POST to `127.0.0.1:37778` | OK — legitimate GCA bridge call |

---

## 5. Mapping to CIPHER Layers

| Source Module | CIPHER Layer | CIPHER Target Path | Disposition | Reasoning |
|---|---|---|---|---|
| `core/orchestrator.py` | AAL / agents / devnex | `agents/devnex/orchestrator.py` | WRAP | Wrap `run_node()` and `run_all()` with A2A skill interface; add OTel spans |
| `core/workflow_engine.py` | PKL / workflow | `pkl/workflow/workflow_engine.py` | REFACTOR | Replace AF.json dispatch with LangGraph StateGraph; preserve topological sort as utility |
| `core/intent_classifier.py` | ARE / skill_loader | `are/skill_loader/intent_classifier.py` | WRAP | Preserve regex rules; add Ollama fallback |
| `core/skill_registry.py` | ARE / skill_loader | `are/skill_loader/skill_registry.py` | WRAP | Add SKILL.md loading |
| `core/run_context.py` | AAL / agents / devnex | `agents/devnex/schemas.py` | REFACTOR | Convert to pydantic v2 BaseModel |
| `core/trace_model.py` | core / schemas | `core/schemas/trace_model.py` | REFACTOR | Convert to pydantic v2; add Memgraph serialization |
| `core/trace_loader.py` | AAL / agents / devnex | `agents/devnex/trace_loader.py` | WRAP | Preserve CSV loading logic |
| `gca/bridge.py` | TRF / llm_gateway | `trf/mcp_servers/llm_gateway/gca_http_driver.py` | WRAP | Expose via `LLMBackend` Protocol; parameterize URL |
| `gca/vscode_invoker.py` | TRF / llm_gateway | `trf/mcp_servers/llm_gateway/vscode_invoker.py` | WRAP | VS Code launch logic |
| `skills/lld_gen_skill.py` | AAL / agents / devnex | `agents/devnex/skills/vcycle_s1n1/skill.py` | WRAP | Add OTel spans; pydantic schemas |
| `skills/code_link_skill.py` | AAL / agents / devnex | `agents/devnex/skills/vcycle_s2n1/skill.py` | WRAP | Add OTel spans |
| `skills/trace_report_skill.py` | AAL / agents / devnex | `agents/devnex/skills/vcycle_s3n1/skill.py` | WRAP | Add OTel spans |
| `skills/test_gen_skill.py` | AAL / agents / devnex | `agents/devnex/skills/vcycle_s6n1/skill.py` | WRAP | Add OTel spans |
| `skills/full_trace_skill.py` | AAL / agents / devnex | `agents/devnex/skills/vcycle_s9n1/skill.py` | WRAP | Add OTel spans |
| `persistence/state_store.py` | core / adapters | `core/adapters/state_store.py` | REFACTOR | Swap JSON backend for Redis 7 |
| `persistence/config_store.py` | core / substrate | `core/substrate/secret_fabric.py` | REFACTOR | Read from env vars + .env |
| `persistence/artifact_writer.py` | core / adapters | `core/adapters/artifact_writer.py` | REFACTOR | Write to MinIO instead of local filesystem |
| `review/` (all) | AAL / agents / devnex | `agents/devnex/review/` | WRAP | Preserve review logic; add OTel |
| `interfaces/gui/` (all) | GUI / panels / devnex | `gui/panels/devnex/` | REFACTOR | Dock into MainCipher shell as a panel; add A2A submission |
| `interfaces/cli/` | AAL / agents / devnex | `agents/devnex/cli.py` | WRAP | Preserve CLI; add A2A submission path |
| `prompts/*.md` | skills / devnex | `skills/devnex/vcycle_s*n*/SKILL.md` | WRAP | Each prompt becomes SKILL.md content section |
| `configs/ruleset.yaml` | GCL / domain_packs | `gcl/domain_packs/iso26262-asil-b/ruleset.yaml` | WRAP | Move to domain pack |
| `tests/` | tests | `tests/unit/agents/devnex/` | WRAP | Reuse as regression base |

---

## 6. Reusable Assets

### Prompt Templates
- `prompts/lld_gen_v1.md` — mature LLD generation prompt → `skills/devnex/vcycle_s1n1/SKILL.md`
- `prompts/code_link_v1.md` → `skills/devnex/vcycle_s2n1/SKILL.md`
- `prompts/full_trace_v1.md` → `skills/devnex/vcycle_s9n1/SKILL.md`

### GUI Widgets (for DevNex panel in shell)
- `StepIndicator` — 9-step V-cycle progress, states IDLE/RUNNING/DONE/ERROR
- `TraceGraphCanvas` — QPainter-based directed graph visualization
- `TraceFilterBar` — relationship filtering
- `TraceNodeCard` — individual node display
- `ReviewDialog` — HITL review modal
- `Sidebar` — navigation within the DevNex panel

### Test Fixtures
- `tests/test_gca_bridge.py` — GCA bridge mock patterns (basis for MockGCABridge)
- `tests/test_state_store.py` — StateStore behavior expectations
- `tests/test_trace_model.py` — TraceGraph golden data

### Configuration
- `configs/ruleset.yaml` — MISRA/coding standard rules (seed for domain pack)

---

## 7. Architectural Debt

### DEBT-001: Hardcoded Bridge URL
- **Location:** `gca/bridge.py:14` — `BRIDGE_URL = "http://127.0.0.1:37778"`
- **Description:** Bridge URL is a module-level constant with no env var override.
- **Impact:** Cannot configure for different environments or test with mock servers.
- **Resolution:** Read from `GCA_BRIDGE_URL` env var via SecretFabric. Target: ADR-0002.

### DEBT-002: JSON File StateStore
- **Location:** `persistence/state_store.py` — `STATE_FILE = Path.home() / ".devnex" / "workflow_state.json"`
- **Description:** Workflow state persisted to JSON file. Violates §1.3 (Redis for working memory).
- **Impact:** No TTL, no pub/sub, no concurrent access safety.
- **Resolution:** REFACTOR to Redis 7 backend preserving `load()`/`save()` API. Target: T-007.

### DEBT-003: Missing OTel Instrumentation
- **Location:** All modules
- **Description:** No OpenTelemetry SDK. Zero spans emitted.
- **Impact:** No observability in CIPHER.
- **Resolution:** Add `@traced` decorator to bridge, orchestrator, skills. Target: ADR-0008.

### DEBT-004: Missing Pydantic v2 Schemas
- **Location:** `core/run_context.py`, `core/orchestrator.py` (NodeResult), `core/trace_model.py`
- **Description:** All data structures are Python dataclasses or raw dicts.
- **Impact:** No runtime validation; incompatible with FastAPI/A2A schemas.
- **Resolution:** Convert to pydantic v2 BaseModel. Target: T-025.

### DEBT-005: HTTP Bridge vs WebSocket Bridge Divergence
- **Location:** `gca/bridge.py` vs `reference/MainCipherdevnex-assistant/.../bridge/gca_bridge.py`
- **Description:** This codebase uses HTTP POST to a Bridge VSIX. The MainCipher version uses direct WebSocket. These are two different approaches to the same problem.
- **Impact:** CIPHER must choose one canonical bridge pattern (ADR-0002 decides).
- **Resolution:** ADR-0002 defines `GCAWebSocketDriver` as canonical. The HTTP bridge pattern is preserved as an alternative driver (`GCAHttpDriver`) for environments where the Bridge VSIX is available. Target: ADR-0002.

### DEBT-006: Artifacts Written to Local Filesystem
- **Location:** `persistence/artifact_writer.py`
- **Description:** Generated CSVs, annotated source, trace matrices all written to `generated_artifacts/` on local disk.
- **Impact:** No object store; no artifact versioning; no knowledge graph integration.
- **Resolution:** REFACTOR to write to MinIO via StorageFabric + emit ArtifactRelation edges to Memgraph. Target: T-014.

### DEBT-007: Incomplete V-Cycle Stages (11 of 13)
- **Location:** `core/orchestrator.py` node dispatch table
- **Description:** Legacy code has nodes S1–S9 but collapses sub-stages. Only 5 skill files exist (lld_gen, code_link, trace_report, test_gen, full_trace). CIPHER requires 13 distinct stages per §1.8.
- **Impact:** Missing granularity for ISO 26262 audit trail at sub-stage level.
- **Resolution:** Expand to 13 stages during MVP. POC only needs S1N1. Target: MVP milestone.

---

## 8. Open Questions for Other Roles

- **For [ARCHITECT]:** ADR-0002 must reconcile the HTTP bridge (this codebase) and the WebSocket bridge (MainCipher codebase). Which is canonical for CIPHER? Can both coexist as alternative LLMBackend drivers?
- **For [LEAD]:** The standalone DevNex GUI uses PyQt6 while the MainCipher shell uses PyQt5. Docking requires the same Qt version. Which upgrades/downgrades are needed?
- **For [DEV]:** The `StepIndicator` widget (9 steps) must be updated to show 13 steps for CIPHER V-cycle. Is this a REFACTOR or a new widget?
- **For [QA-TEST]:** Existing tests mock the bridge at the HTTP level. Can these be adapted for the MockGCABridge pattern?

---

## 9. CIPHER Contracts Affected (Forward Brief)

| ADR / Task | Trigger from this CAR |
|---|---|
| **ADR-0001** (LLM Gateway) | `DevNexBridge.send_prompt()` → `GCAHttpDriver` or `GCAWebSocketDriver`; need unified `LLMBackend` Protocol |
| **ADR-0002** (GCA Bridge Protocol) | HTTP bridge (DEBT-001, DEBT-005) vs WebSocket bridge — must reconcile |
| **ADR-0005** (Shell-Panel Docking) | Standalone DevNex GUI must dock into MainCipher shell; `StepIndicator`, trace panels become docked widgets |
| **ADR-0006** (HITL Gate) | `WorkflowEngine.on_human_review` callback → LangGraph interrupt() node |
| **ADR-0007** (Skill Loader) | `SkillRegistry` + `BaseSkill` → CIPHER ARE skill loader |
| **T-024** (DevNex Orchestrator Adapter) | WRAP orchestrator with A2A task handler |
| **T-025** (Pydantic Schema Migration) | DEBT-004; convert all dataclasses |
| **T-026** (S1N1 Skill) | WRAP lld_gen_skill with CIPHER skill contract |
| **T-GUI-DOCK** (DevNex Panel Docking) | Dock standalone GUI into shell as per ADR-0005 |

---

## 10. Summary Assessment

**Fitness for CIPHER integration: HIGH**

The standalone DevNex Assistant is a well-structured, working V-cycle agent with clean separation between orchestration, skills, persistence, and GUI. The `DevNexOrchestrator → SkillRegistry → BaseSkill` pattern maps directly to CIPHER's ARE skill dispatch. The GCA bridge, while using HTTP instead of WebSocket, demonstrates the correct separation of concerns.

The primary integration costs are: (a) reconciling the HTTP vs WebSocket bridge patterns (~1 day, decided by ADR-0002), (b) converting dataclasses to pydantic v2 (~2 days, mechanical), (c) swapping JSON StateStore for Redis (~1 day, API-preserving), (d) docking the standalone GUI into the MainCipher shell (~2 days, requires ADR-0005 contract), and (e) adding OTel spans (~1 day, decorator-based).

The existing test suite (5 test files) provides a solid regression base. The prompt templates are production-ready and become SKILL.md files directly.

**Recommended action:** WRAP all skills and orchestration logic; REFACTOR persistence (Redis), bridge (parameterize URL), and schemas (pydantic v2); REFACTOR GUI for docking into shell. The standalone GUI is preserved as the DevNex panel inside the CIPHER shell.
