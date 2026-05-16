# CIPHER DevNex — Sprint 0 Detailed Changelog

**Sprint dates:** 2026-05-14 → 2026-05-16
**Gate:** G1 — 169 / 169 pytest tests passing
**Authors:** Tech Lead (ARCH), Senior Developer (DEV), Tester (TEST), QA Engineer (QA)

---

## Summary

Sprint 0 closed 10 infrastructure gap fixes (F-001…F-010), delivered two new
automotive UC modules (UC 3.1 ASIL Code Review, UC 4.1 Standards Q&A),
completed UC 4.4 RAM Overlap Detection, authored the ASDLC process document,
and repaired all post-merge test failures. Every change targets the live codebase
at `cipher/agents/devnex_assistant/` — no files were rewritten from scratch
without prior WRAP/REFACTOR analysis.

---

## Part 1 — Infrastructure Gap Fixes (F-001 … F-010)

### F-001 — Canonical Artifact Filenames

**Problem:** Nodes S3N1, S4N1, and S5N1 wrote artifacts under names that did not
match the keys in `trace_loader._CSV_MAP`, so the trace loader could never find them.

**Files changed:**
- `core/orchestrator.py` — `_run_s3n1()`, `_run_s4n1()`, `_run_s5n1()`

**Before → After:**

| Node | Old filename | Canonical filename |
|---|---|---|
| S3N1 | `LLD_Code_Trace_Report.csv` | `LLD_Code_Trace_Matrix.csv` |
| S4N1 | `HLD_LLD_Links.json` | `HLD_LLD_Trace_Matrix.csv` |
| S5N1 | `HLD_LLD_Code_Trace_Matrix.csv` | `Full_Downstream_Trace.csv` |

**Verification:** `TestF001ArtifactFilenames` — 2 tests

---

### F-002 — GCA Retry Loop

**Problem:** Any single GCA failure immediately raised an unhandled exception.
No retry behaviour existed.

**Files changed:**
- `core/orchestrator.py` — added `_invoke_with_retry(prompt, files, node_id)`

**Implementation:**
```python
def _invoke_with_retry(self, prompt, files, node_id=""):
    max_retries = int(self.config.get("max_gca_retries", 3))
    for attempt in range(1, max_retries + 1):
        try:
            result = self.gca_invoker.invoke_prompt(prompt, files)
            if result.is_response_valid:
                return result
        except Exception as exc:
            self._trace(f"{node_id}: attempt {attempt}/{max_retries} raised {exc}.", level="WARN")
        if attempt < max_retries:
            time.sleep(1)
    raise NodeExecutionError(f"{node_id}: GCA failed after {max_retries} attempt(s).")
```

All GCA-calling nodes updated to use `_invoke_with_retry` instead of direct `gca_invoker.invoke_prompt`.
`configs/ruleset.yaml` sets `max_gca_retries: 3`.

**Verification:** `TestF002RetryLoop` — 2 tests

---

### F-003 — IntentClassifier S1N2 / S1N3 Split

**Problem:** A single regex `r"^S1N[23]$"` mapped both S1N2 and S1N3 to `vcycle_stage="S1N2"`.
Calling `run_node("S1N3")` would execute the S1N2 review handler.

**Files changed:**
- `core/intent_classifier.py` — `_RULES` list

**Before:**
```python
(r"^S1N[23]$", "RUN_STAGE", "S1N2", "lld_gen"),
```

**After:**
```python
(r"^S1N2$", "RUN_STAGE", "S1N2", "lld_gen"),
(r"^S1N3$", "RUN_STAGE", "S1N3", "lld_gen"),
```

**Verification:** `TestF003IntentClassifier` — 8 tests (includes S1N2 ≠ S1N3 distinctness assertion)

---

### F-004 — SkillRegistry: explain, free_form, asil_review, standards_qa

**Problem:** `SkillRegistry.build_default()` did not register the `explain` or `free_form`
skills, causing a `None` return for those intent types. UC 3.1 and UC 4.1 skills
also needed registration.

**Files changed:**
- `core/skill_registry.py` — `build_default()`
- `core/intent_classifier.py` — added trigger rules for EXPLAIN, FREE_FORM, asil_review, standards_qa
- `skills/explain_skill.py` — new file
- `skills/free_form_skill.py` — new file

**New skills:**

`ExplainSkill` — builds a one-shot GCA prompt:
```
"Explain {target} in the context of SWC '{swc}'."
```

`FreeFormSkill` — prepends CIPHER DevNex system header and forwards prompt to GCA.

`build_default()` additions:
```python
reg.register("explain",      ExplainSkill(orchestrator))
reg.register("free_form",    FreeFormSkill(orchestrator))
reg.register("asil_review",  AsilReviewSkill(orchestrator))
reg.register("standards_qa", StandardsQASkill(orchestrator))
```

**Verification:** `TestF004SkillRegistry` — 5 tests

---

### F-005 — ArtifactMissingError in S1N1 and S1N4

**Problem:** S1N1 and S1N4 would silently embed `[FILE NOT FOUND]` for missing inputs and
continue, producing invalid GCA prompts and garbage artifacts.

**Files changed:**
- `core/orchestrator.py` — `_run_s1n1()`, `_run_s1n4()`
- `core/errors.py` — `ArtifactMissingError` class (confirmed present)

**Implementation:**
- S1N1: raises `ArtifactMissingError(f"S1N1: required file '{path}' not found")` when
  `G_SWDD_TEMP`, `SWC_name_C`, `SWC_name_H`, or `SWC_name_TEMP_LLD` cannot be resolved.
- S1N4: raises `ArtifactMissingError("S1N4: ...")` when `SWC_nameInspBaseLLD` path does not exist.

**Verification:** `TestF005ArtifactMissingError` — 2 tests

---

### F-006 — S1N4 Prompt Template

**Problem:** S1N4 (requirement categorisation) was constructing its GCA prompt inline
with hardcoded text, making it impossible to tune without code changes.

**Files changed:**
- `core/orchestrator.py` — `_run_s1n4()`
- `prompts/categorize_reqs_v1.md` — new file

**Implementation:** `_run_s1n4()` now calls `_load_prompt("categorize_reqs_v1.md")` and
`_render_prompt(template, context)` before invoking GCA.

`categorize_reqs_v1.md` structure:
```markdown
# LLD Requirement Categorisation Prompt
Categorise each row in the following LLD CSV as FUNCTIONAL or NON_FUNCTIONAL ...
SWC: {{SWC_name}}
...
```

**Verification:** covered by `TestF005ArtifactMissingError::test_s1n4_raises_when_insp_file_missing`

---

### F-007 — S3N1 and S4N1 Prompt Templates

**Problem:** S3N1 (LLD-to-code traceability) and S4N1 (HLD-to-LLD links) had no
prompt templates — prompts were fully inline in the orchestrator.

**Files changed:**
- `core/orchestrator.py` — `_run_s3n1()`, `_run_s4n1()`
- `prompts/lld_code_trace_v1.md` — new file
- `prompts/hld_lld_links_v1.md` — new file

`lld_code_trace_v1.md` guides GCA to produce a CSV with columns
`LLD_ID,LLD_TITLE,CODE_ID,CODE_TITLE,LINK_TYPE,CONFIDENCE`.

`hld_lld_links_v1.md` guides GCA to produce a CSV with columns
`HLD_ID,HLD_TITLE,LLD_ID,LLD_TITLE,LINK_TYPE,CONFIDENCE`.

**Verification:** `TestF001ArtifactFilenames` checks output file names produced by these nodes.

---

### F-008 — WorkflowEngine Bridge (`run_workflow`)

**Problem:** `WorkflowEngine` (AF.json graph executor) existed but was not callable
through the orchestrator API, so AF.json-based agentic graphs could not be triggered
from skills or the GUI.

**Files changed:**
- `core/orchestrator.py` — added `run_workflow(workflow_path, inputs)`

**Implementation:**
```python
def run_workflow(self, workflow_path: str, inputs: dict | None = None) -> str:
    from core.workflow_engine import WorkflowEngine
    engine = WorkflowEngine(
        gca_bridge=self.gca_invoker,
        on_node_start=lambda nid, label: self.on_node_started(nid),
        on_node_complete=lambda nid, resp: self._trace(f"WF node '{nid}' complete."),
        on_human_review=lambda nid, data: self.on_human_review(nid, data.get("message", "")),
    )
    return engine.execute(workflow_path, inputs or {})
```

**Test fix:** `WorkflowEngine` is imported lazily inside `run_workflow`, so the patch
target is `"core.workflow_engine.WorkflowEngine"` (not `"core.orchestrator.WorkflowEngine"`).
Tests must pre-seed `orch._gca_invoker = MagicMock()` to prevent the lazy `gca_invoker`
property from importing the `websocket` module.

**Verification:** `TestF008WorkflowBridge` — 1 test

---

### F-009 — Critical-Glob Enforcement (`_enforce_critical_globs`)

**Problem:** No mechanism existed to warn when a workspace was missing expected
file types (`.c`, `.h`, `.ld`, `.map`), allowing misconfigured workspaces to silently
produce empty GCA prompts.

**Files changed:**
- `core/orchestrator.py` — added `_load_ruleset()`, `_enforce_critical_globs()`
- `configs/ruleset.yaml` — new file

**Bug discovered and fixed during Sprint 0:**
The original implementation used `workspace.rglob(pattern.lstrip("**/"))`.
`str.lstrip("**/")` strips the characters `*` and `/` from the left,
so `"**/*.c".lstrip("**/")` → `".c"` (not `"*.c"`), meaning no files ever matched.

**Fix:** `pattern.removeprefix("**/")` removes the two-character prefix as a string:
```python
glob_suffix = pattern.removeprefix("**/")   # "**/*.c" → "*.c"
matches = list(workspace.rglob(glob_suffix))
```

`_enforce_critical_globs` logs `WARN` for missing patterns but does not raise,
so CI is not blocked for legitimate projects without certain file types.

**Verification:** `TestF009CriticalGlobs` — 2 tests

---

### F-010 — Workspace Path Validation (`validate_workspace`)

**Problem:** The orchestrator would silently proceed even when `workspace_path`
pointed to a non-existent directory or a file, causing confusing downstream failures.

**Files changed:**
- `core/run_context.py` — added `validate_workspace()`
- `core/orchestrator.py` — `_run_s1n1()` calls `self.run_context.validate_workspace()`

**Implementation:**
```python
def validate_workspace(self) -> None:
    wp = Path(self.workspace_path)
    if not wp.exists():
        raise ConfigValidationError(
            f"workspace_path does not exist: '{wp}'. "
            "Check config.json or the --workspace argument."
        )
    if not wp.is_dir():
        raise ConfigValidationError(
            f"workspace_path is not a directory: '{wp}'."
        )
```

**Verification:** `TestF010WorkspaceValidation` — 3 tests

---

## Part 2 — New UC Modules

### UC 3.1 — ASIL Code Review Assistant

**File:** `skills/automotive/asil_review_skill.py`

**Purpose:** Three-phase MISRA-C:2012 compliance and ASIL violation detection pipeline
for ASIL-B/C/D automotive source files.

**Architecture:**
```
Phase 1 — Ollama TRIAGE
  Input:  source file content + ASIL level
  Output: JSON list of AsilViolation {file, line, rule, severity, description, fix_hint}
  Model:  local Ollama (llama3.2 or mistral)

Phase 2 — Gemini CLI PLAN
  Input:  violation list from Phase 1
  Output: fix strategy per violation (skipped if no violations)

Phase 3 — GCA CODE_GEN
  Input:  source file + violation list + fix plan
  Output: fix diffs (split on "---DIFF---" separator)
  Retry:  up to max_gca_retries (default 3)
```

**MISRA-C:2012 mandatory rules enforced:**

| Rule | Requirement |
|---|---|
| R1.3 | Undefined behaviour shall not occur |
| R11.3 | A cast shall not be performed between a pointer to object and a pointer to different object |
| R11.8 | A cast shall not remove any const or volatile qualification |
| R14.4 | The controlling expression of an iteration/selection shall be essentially Boolean |
| R15.5 | A function shall have a single point of exit |
| R17.7 | The value returned by a function having non-void return type shall be used |
| R21.3 | The memory allocation and deallocation functions shall not be used |

**ASIL gate decisions:**

| ASIL | Has Criticals | Decision | Action |
|---|---|---|---|
| D | Yes | HARD_BLOCK | raises `SemanticConflictError` |
| C | Yes | HOLD | returns report; pipeline pauses |
| B | Yes | HOLD | returns report; pipeline pauses |
| A/QM | Any | WARN | returns report; pipeline continues |
| Any | No | PASS | clean badge |

**Artifacts written:**
- `asil_review_{stem}.json` — machine-readable violation + gate result
- `asil_review_{stem}.md` — human-readable compliance report with badge

**New exception:** `SemanticConflictError` — subclass of `DevNexError`; raised on ASIL-D hard block.

**Test coverage:** `tests/test_asil_review.py` — 20 tests across 4 classes:
- `TestAsilViolationParsing` (7 tests)
- `TestAsilReviewPhases` (5 tests)
- `TestAsilGateIntegration` (4 tests)
- `TestAsilReportGeneration` (4 tests)

---

### UC 4.1 — ISO 26262 / AUTOSAR / MISRA-C Standards Q&A

**File:** `skills/automotive/standards_qa_skill.py`

**Purpose:** Hybrid retrieval-augmented generation (RAG) over standards corpora.
Answers engineering questions with cited sources and relevance scores.

**Architecture:**
```
Question + scope_filter
    │
    ▼
HybridRetriever.retrieve(query, index_key, top_k=5)
    │
    ├─► _embed_query()        → Ollama /api/embeddings (nomic-embed-text)
    ├─► _dense_search()       → Qdrant REST (if available)
    └─► _bm25_search()        → rank_bm25.BM25Okapi (always available)
    │
    merge by doc_id:
    hybrid_score = 0.7 × dense_score + 0.3 × bm25_score
    │
    ▼
_generate_answer(question, top_chunks)
    → Ollama /api/generate → answer string
    │
    ▼
QAAnswer(question, answer, sources, index_used, top_k)
```

**Key design decisions:**
- `DEFAULT_ALPHA = 0.7` — weighted towards dense (semantic) retrieval
- `_qdrant_ok: bool | None` — set on first call; sticks to avoid repeated failed requests
- BM25 fallback always available — no Qdrant required for basic operation
- `load_index(docs)` — in-memory seeding for unit tests and offline use

**Supported index keys:** `"iso26262"`, `"misra_c"`, `"autosar"`, `"codebase"`

**Test coverage:** `tests/test_standards_qa.py` — 23 tests across 5 classes:
- `TestHybridRetriever` (8 tests)
- `TestSourceChunk` (2 tests)
- `TestStandardsQASkill` (7 tests)
- `TestIndexLoading` (3 tests)
- `TestCitationFormat` (3 tests)

---

### UC 4.4 — RAM / Memory Overlap Detection

**Files:** `skills/uc4_4/map_analyzer.py`, `ram_overlap_detector.py`,
`linker_script_parser.py`, `asil_gate.py`

**Purpose:** Parse GNU linker `.map` and `.ld` files to detect overlapping RAM sections,
classify by ASIL level, and hard-block for ASIL-D violations.

**Pipeline:**
```
MapAnalyzer.parse(map_path)         → list[SectionLayout]
MapAnalyzer.get_ram_sections()      → filter to RAM VMAs only
RamOverlapDetector.detect(sections) → list[OverlapResult]
AsilGate.enforce(asil, overlaps)    → GateDecision or raises SemanticConflictError
```

**Artifacts written:**
- `layout.json` — full section list with hex addresses
- `overlap_report.json` — detected overlaps with ASIL action
- `gate_decision.json` — gate level, decision, safety engineer requirement

**Test coverage:** `tests/test_uc4_4.py` — 64 tests across 5 classes:
- `TestMapAnalyzer` (9 tests)
- `TestRamOverlapDetector` (14 tests)
- `TestLinkerScriptParser` (7 tests)
- `TestAsilGate` (18 tests)
- `TestUC44Integration` (4 tests — end-to-end pipeline)

---

## Part 3 — ASDLC Process Document

**File:** `docs/ASDLC.md`

Authored by QA Engineer role. Defines the AI Software Development Lifecycle for CIPHER:

- 5 gate levels G0–G5 with entry/exit criteria
- Artifact contracts table (filename → producing node → consuming node)
- F-001 canonical filename table
- CI/CD integration section with UC 4.4 post-merge hook command
- ASIL-aligned review checkpoints table
- MISRA-C:2012 mandatory rules reference
- Sprint lifecycle summary table

---

## Part 4 — Bug Fixes and Stability

### BUG-001 — `lstrip("**/")` treated argument as character set

**File:** `core/orchestrator.py` — `_enforce_critical_globs()`
**Symptom:** `rglob(".c")` called instead of `rglob("*.c")` — no files ever matched.
**Root cause:** `str.lstrip("**/")` strips individual chars `*` and `/`, leaving `.c`.
**Fix:** `pattern.removeprefix("**/")` — Python 3.9+ string prefix removal.
**Test:** `TestF009CriticalGlobs::test_with_c_file_no_warning`

---

### BUG-002 — `datetime.UTC` ImportError on Python 3.10

**Files:** `core/console_logging.py`, `core/run_context.py`
**Symptom:** `ImportError: cannot import name 'UTC' from 'datetime'` on Python 3.10.
**Root cause:** `datetime.UTC` was introduced in Python 3.11.
**Fix:**
```python
try:
    from datetime import UTC          # Python 3.11+
except ImportError:
    UTC = timezone.utc                # Python 3.10 compat
```

---

### BUG-003 — `TestF008WorkflowBridge` — websocket import in test

**File:** `tests/test_sprint0_fixes.py`
**Symptom:** `ModuleNotFoundError: No module named 'websocket'` when test calls `run_workflow()`.
**Root cause:** `run_workflow()` accesses `self.gca_invoker` which lazily imports
`gca.vscode_invoker.DevNexGCAInvoker` → `import websocket as _ws`.
**Fix:** Tests pre-seed `orch._gca_invoker = MagicMock()` before calling `run_workflow`.

---

### BUG-004 — FUSE filesystem stale `.pyc` caching

**Symptom:** Edits to `.py` files on the FUSE-mounted Windows filesystem were not
picked up by the Python interpreter — old bytecode ran instead of new source.
**Root cause:** FUSE kernel cache did not immediately reflect new mtime after writes
via the Edit tool; `find -delete` on pyc files also failed silently on FUSE.
**Fix:** `touch` all modified `.py` files after edits to force mtime ahead of `.pyc`.
Write critical fixes via Python `path.write_text()` for atomic mtime update.

---

### BUG-005 — `shutil.rmtree` PermissionError in test tearDown on FUSE

**File:** `tests/test_orchestrator.py`
**Symptom:** 9 tests failed with `PermissionError: [Errno 1] Operation not permitted`
in `tearDown` when `rmtree` tried to remove the FUSE-mounted test directory.
**Fix:**
```python
try:
    shutil.rmtree(self.run_dir)
except (PermissionError, OSError):
    pass  # FUSE-mounted filesystems may disallow rmdir
```

---

### BUG-006 — `orchestrator.py` and test files truncated mid-write by FUSE

**Symptom:** Syntax errors on Windows compile step (`IndentationError` at unexpected lines);
truncated function bodies (`unittest.m`, `MockEngine.as`).
**Root cause:** FUSE write of large files via Edit tool occasionally truncated tail bytes.
**Fix:** Detected via `py_compile.compile()`; repaired by `head -n N > clean.py && cp back`
and bash appends for missing lines. Final normalisation via Python `write_text()` with
explicit `
` → `
` normalisation to eliminate mixed line endings.

---

## Part 5 — Test Suite Summary

| Category | Test File | Tests | Result |
|---|---|---|---|
| Persistence | `test_config_store.py` | 4 | ✅ Pass |
| Persistence | `test_state_store.py` | 5 | ✅ Pass |
| GCA Bridge | `test_gca_bridge.py` | 6 | ✅ Pass |
| Orchestrator | `test_orchestrator.py` | 9 | ✅ Pass |
| Trace model | `test_trace_model.py` | 17 | ✅ Pass |
| Sprint 0 regressions | `test_sprint0_fixes.py` | 21 | ✅ Pass |
| UC 3.1 ASIL Review | `test_asil_review.py` | 20 | ✅ Pass |
| UC 4.1 Standards QA | `test_standards_qa.py` | 23 | ✅ Pass |
| UC 4.4 RAM Overlap | `test_uc4_4.py` | 64 | ✅ Pass |
| **TOTAL** | | **169** | ✅ **100%** |

**Sprint 0 Gate G1: CLOSED** — 2026-05-16

---

## Part 6 — Files Changed / Created

### Modified
| File | Changes |
|---|---|
| `core/orchestrator.py` | F-001 artifact names, F-002 retry, F-005 ArtifactMissingError, F-006/F-007 templates, F-008 run_workflow, F-009 ruleset/globs, F-010 workspace validate; lstrip bug fix |
| `core/run_context.py` | F-010 validate_workspace(); Python 3.10 UTC compat |
| `core/intent_classifier.py` | F-003 split S1N2/S1N3; F-004 explain/free_form/asil_review/standards_qa triggers |
| `core/skill_registry.py` | F-004 register explain, free_form, asil_review, standards_qa |
| `core/console_logging.py` | Python 3.10 UTC compat |
| `tests/test_orchestrator.py` | tearDown FUSE PermissionError guard |
| `tests/test_sprint0_fixes.py` | F-008 pre-seed `_gca_invoker`; line ending normalisation |

### Created
| File | Purpose |
|---|---|
| `skills/explain_skill.py` | F-004 EXPLAIN skill |
| `skills/free_form_skill.py` | F-004 FREE_FORM fallback skill |
| `skills/automotive/__init__.py` | Package init |
| `skills/automotive/asil_review_skill.py` | UC 3.1 three-phase ASIL review |
| `skills/automotive/standards_qa_skill.py` | UC 4.1 hybrid RAG standards QA |
| `skills/uc4_4/map_analyzer.py` | UC 4.4 GNU map parser |
| `skills/uc4_4/ram_overlap_detector.py` | UC 4.4 interval-intersection detector |
| `skills/uc4_4/linker_script_parser.py` | UC 4.4 `.ld` parser |
| `skills/uc4_4/asil_gate.py` | UC 4.4 ASIL decision table |
| `configs/ruleset.yaml` | F-009 critical-glob + gate config |
| `prompts/categorize_reqs_v1.md` | F-006 S1N4 template |
| `prompts/lld_code_trace_v1.md` | F-007 S3N1 template |
| `prompts/hld_lld_links_v1.md` | F-007 S4N1 template |
| `tests/test_sprint0_fixes.py` | F-001…F-010 regression suite |
| `tests/test_asil_review.py` | UC 3.1 test suite |
| `tests/test_standards_qa.py` | UC 4.1 test suite |
| `docs/ASDLC.md` | AI Software Development Lifecycle process |
| `docs/CHANGELOG_SPRINT0.md` | This document |
| `docs/CIPHER_Platform_HLD.md` | CIPHER platform architecture |

### Updated (documentation)
| File | Changes |
|---|---|
| `docs/LLD.md` | Full Sprint 0 revision — new classes, artifact table, call graphs, test map |
| `docs/HLD.md` | Sprint 0 revision — three-LLM layer, skill table, safety gates, risk register |
