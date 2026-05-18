---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# Wrap/Rewrite Decision Matrix — CAR-002: DevNex Assistant (Agent-001)

- **Reference:** CAR-002 (DevNex Assistant — Agent-001)
- **Codebase path:** reference/devnex_assistant/
- **Date:** 2026-05-16
- **ADRs referenced:** ADR-0001, ADR-0002, ADR-0005

---

## Decision Matrix — Agent Backend

| Module | Disposition | Integration Risk | Effort | Adapter Shape | Reasoning |
|--------|-------------|-----------------|--------|---------------|-----------|
| `core/orchestrator.py` | WRAP | Medium | M | Wrap `run_node()` in A2A TaskHandler; emit OTel span per node; preserve internal logic | Core orchestration logic is correct; only needs A2A skin |
| `core/workflow_engine.py` | REFACTOR | High | L | Extract topological sort → `workflow_utils.py`; replace AF.json dispatch with LangGraph StateGraph | §1.9 mandates LangGraph; but AF.json logic is functionally correct |
| `core/intent_classifier.py` | WRAP | Low | S | Adapter exposes `classify()` via ARE SkillLoader interface | Regex rules preserved; Ollama fallback added as new path |
| `core/skill_registry.py` | WRAP | Low | S | Adapter adds SKILL.md loading alongside existing resolve() | Existing API is clean |
| `core/run_context.py` | REFACTOR | Low | S | Convert `DevNexRunContext` dataclass → pydantic v2 `BaseModel` | Field-for-field migration |
| `core/trace_model.py` | REFACTOR | Low | M | Convert `TraceNode`/`TraceEdge`/`TraceGraph` → pydantic v2; add `to_cypher()` serializer | Need Memgraph compatibility |
| `core/trace_loader.py` | WRAP | Low | S | Preserve CSV loading; output pydantic TraceGraph | Input logic unchanged |
| `core/context_manager.py` | WRAP | Low | S | Inject SecretFabric for config values | Minimal change |
| `core/errors.py` | WRAP | Low | S | Copy to `agents/devnex/errors.py` | Pure definitions |
| `core/console_logging.py` | WRAP | Low | S | Preserve; add OTel log bridge | Used by all modules |
| `gca/bridge.py` | WRAP | Medium | M | Expose as `GCAHttpDriver` implementing `LLMBackend` Protocol; parameterize URL from env | ADR-0001 integration |
| `gca/vscode_invoker.py` | WRAP | Low | S | Copy to TRF; parameterize paths | Preserve VS Code launch logic |
| `skills/lld_gen_skill.py` | WRAP | Low | M | Add pydantic input/output schemas; add OTel span; route LLM calls through gateway | POC critical path |
| `skills/code_link_skill.py` | WRAP | Low | S | Same pattern as lld_gen | MVP scope |
| `skills/trace_report_skill.py` | WRAP | Low | S | Same pattern | MVP scope |
| `skills/test_gen_skill.py` | WRAP | Low | S | Same pattern | MVP scope |
| `skills/full_trace_skill.py` | WRAP | Low | S | Same pattern | MVP scope |
| `skills/base_skill.py` | WRAP | Low | S | Preserve as `ISkill` Protocol | Clean interface |
| `persistence/state_store.py` | REFACTOR | Medium | M | Preserve `load()`/`save()` API; swap JSON backend for Redis 7 client | §1.3 mandate |
| `persistence/config_store.py` | REFACTOR | Low | S | Rewrite as SecretFabric consumer (env vars + .env) | Config source changes |
| `persistence/artifact_writer.py` | REFACTOR | Medium | M | Write to MinIO via StorageFabric; emit ArtifactRelation to KG | §1.3 + observability |
| `review/` (all 4 files) | WRAP | Low | M | Preserve review logic; add OTel; wire to A2A | Correct logic, needs instrumentation |
| `prompts/*.md` (3 files) | WRAP | Low | S | Copy as SKILL.md content sections | Direct mapping |
| `configs/ruleset.yaml` | WRAP | Low | S | Move to `gcl/domain_packs/` | Configuration relocation |

## Decision Matrix — Agent GUI (Docking into Shell)

| Module | Disposition | Integration Risk | Effort | Adapter Shape | Reasoning |
|--------|-------------|-----------------|--------|---------------|-----------|
| `interfaces/gui/main_window.py` | REFACTOR | High | M | Strip QMainWindow chrome; keep only the panel content widget; implement `PanelDescriptor` | ADR-0005 docking |
| `interfaces/gui/sidebar.py` | REFACTOR | Medium | S | Becomes panel-internal navigation (not shell sidebar) | Panel owns its own sub-nav |
| `interfaces/gui/step_indicator.py` | WRAP | Low | S | Move into panel package unchanged | Already a self-contained widget |
| `interfaces/gui/panels/workflow_panel.py` | REFACTOR | Medium | M | Replace direct orchestrator calls with `client.submit_task()` | A2A submission |
| `interfaces/gui/panels/trace_panel.py` | WRAP | Low | S | Move into panel package | Presentation only |
| `interfaces/gui/panels/trace_graph_canvas.py` | WRAP | Low | S | Move into panel package | Pure visual |
| `interfaces/gui/panels/review_panel.py` | WRAP | Low | S | Move into panel package | Presentation |
| `interfaces/gui/panels/output_log.py` | WRAP | Low | S | Move into panel package | Shared with shell version |
| `interfaces/gui/panels/config_panel.py` | WRAP | Low | S | Move into panel package | Panel-level config |
| `interfaces/gui/workers/*.py` (4 files) | REFACTOR | Medium | M | Replace direct orchestrator calls with `CipherShellClient` async methods | Bridge Qt threads → A2A |
| `interfaces/gui/styles/palette.py` | WRAP | Low | S | Merge with shell theme tokens | Panel respects shell theme |
| `interfaces/gui/settings_*.py` (2 files) | WRAP | Low | S | Move into panel package | Panel-level settings |
| `interfaces/gui/splash.py` | DROP | — | — | Not needed — shell has its own boot panel | Redundant |
| `interfaces/gui/config_init_modal.py` | WRAP | Low | S | First-run modal stays in panel | Panel-level initialization |

---

## Summary

| Disposition | Count (Backend) | Count (GUI) | Total Effort |
|-------------|----------------|-------------|--------------|
| WRAP | 17 | 9 | ~17h |
| REFACTOR | 7 | 5 | ~5d |
| REWRITE | 0 | 0 | — |
| DROP | 0 | 1 | — |

**Primary risks:**
1. WorkflowEngine→LangGraph migration (REFACTOR, High risk, L effort) — this is the hardest single task.
2. GUI docking (strip QMainWindow → PanelDescriptor) — medium risk but many files touched.
3. StateStore Redis migration — API-preserving but needs Redis container in dev.
