# CIPHER — Unified Sprint Plan (Backlog + VSIX Extension)

**Date**: 2026-05-18
**Owner**: CIPHER core team
**Source of truth**: this document supersedes the "Suggested Next Steps" sections of `docs/SESSION_HANDOFF.md`.

---

## 0. Audit Snapshot (state at 2026-05-18)

| # | Backlog item                                                                 | State        |
|---|------------------------------------------------------------------------------|--------------|
| 1 | Real node execution through GCA/Ollama                                       | Partial      |
| 2 | CipherOrchestrator wired as parent of DevNex in `CipherMainWindow`           | Not started  |
| 3 | Voice pipeline TTS/STT connected                                             | Not started  |
| 4 | HUD dashboard center views populated (not placeholders)                      | Partial      |
| 5 | System status live polling (right column)                                    | Partial (random latency) |
| 6 | E-012 SkillLoader 3-stage progressive disclosure                             | Not started  |
| 7 | E-013 Runtime Prompt Contract Assembly                                       | Not started  |
| 8 | E-014 Context Gap Detection (Memory + Research)                              | Not started  |
| 9 | WF₆ structured-field consistency (full check)                                | Stub         |
| 10| Additional domain packs (ASIL-C/D, ASPICE L3, MISRA-C:2012)                  | Not started  |
| 11| DVF loop wired into DevNex orchestrator nodes                                | Partial      |
| 12| CAP metrics in CI                                                            | Not started  |

**New top-level workstream**: VSCode `.vsix` extension that embeds CIPHER as an in-editor sub-window. See `docs/VSIX_DESIGN.md` (companion doc) for the design pass; the merged sprint plan below subsumes it.

---

## 1. Architectural Decision Captured

VSCode integration uses **Option A — Webview + headless Python host**.

- VSCode extension (TypeScript) ships only TS/JS; spawns the user's existing CIPHER Python install as a child process via `run_poc.py --headless` (new flag, this sprint).
- Headless mode skips PyQt6 entirely, runs only the two FastAPI servers (A2A :8100, LLM Gateway :8200), and exposes `/cipher/*` REST + `/events/sse` for the webview.
- The PyQt6 GUI is retained as a legacy launcher (`run_poc.py` without `--headless`).
- Webview talks loopback HTTP/SSE to the Python host — no QtWebEngine embedding (not technically possible inside VSCode).

Rationale: only path that delivers the user's requested experience ("sub-window inside VSCode, like the Agents widget"). Native window embedding (Option B) was rejected.

---

## 2. Sprint Plan

Each sprint is ~1 week. DoD = "deliverable demoable + tests pass + plan doc updated".

### Sprint 1 — Headless server, event bridge, parent wiring  ◀ ACTIVE
Foundations. The VSIX cannot exist until the Python side can run without Qt and stream events.

- [S1-1] Add `--headless` flag to `run_poc.py`. When set: register skills, start both FastAPI servers, block on `signal.pause()` / asyncio loop. No QApplication.
- [S1-2] Wire CipherOrchestrator as parent of DevNex (backlog item #2). `run_poc.py` constructs `CipherOrchestrator`, passes it into `CipherMainWindow(parent_orchestrator=...)`, which registers the DevNex orchestrator on first lazy init via `parent_orchestrator.register_child("devnex", ...)`.
- [S1-3] New module `cipher/interfaces/web/event_bridge.py` — non-Qt event bus with publish/subscribe semantics. Workers and orchestrator callbacks publish JSON envelopes; the FastAPI SSE endpoint subscribes.
- [S1-4] New module `cipher/are/a2a_server/cipher_routes.py` — REST endpoints:
  - `GET  /cipher/healthz`
  - `GET  /cipher/config` / `PUT /cipher/config`
  - `POST /cipher/nodes/{node_id}/run` → `{ runId }`
  - `POST /cipher/runs/full`
  - `POST /cipher/runs/{runId}/review` (body: `{ approved: bool }`)
  - `GET  /events/sse` (Server-Sent Events stream)
- [S1-5] Mount cipher_routes in `cipher/are/a2a_server/server.py`.
- [S1-6] Scaffold `extension/` directory: `package.json`, `tsconfig.json`, `src/extension.ts`, `src/cipherViewProvider.ts`, `src/pythonHost.ts`, `webview/index.html`, `webview/main.ts`, `README.md`. No publishable build yet — just compilable skeleton that opens an empty themed webview and reports host status.

**Demo**: `python run_poc.py --headless` + `curl http://127.0.0.1:8100/cipher/healthz` returns `{"ok": true}`. VSCode extension's activity-bar icon opens an empty CIPHER panel showing "● READY :8100/:8200".

### Sprint 2 — Webview shell + DevNex Workflow/Output/Config panels
- Port `WorkflowPanel`, `OutputLogPanel`, `ConfigPanel` to TS/HTML in `extension/webview/`.
- Worker refactor: split signal emission from Qt — `SignalAdapter` so the same `NodeWorker`/`FullRunWorker` works headless and Qt.
- Backlog #1 closes here: smoke a real node run end-to-end through `/cipher/nodes/S1N1/run`.

### Sprint 3 — Trace, Review, HUD Mode 0
- Port `TracePanel` (Canvas graph), `ReviewPanel` modal, Mode 0 HUD (`ArcReactor` SVG + waveform).
- Backlog #4 closes here: HUD center views become real components, not placeholders.
- Backlog #5 closes here: status bar polls `/cipher/healthz` of all infra services (Redis, Memgraph, etc.) and renders the live grid.

### Sprint 4 — CAP integration sweep
- [Backlog #11] Wire `DVFLoop` into DevNex orchestrator's LLM-touching nodes (replace direct LLM calls).
- [Backlog #9] Implement WF₆ structured field consistency once MKF Knowledge Graph runtime is reachable from the validator.
- [Backlog #12] Add `.github/workflows/ci.yml` + `pytest.ini`. Run `pytest tests/` + `compute_metrics()` on a fixture CRC.

### Sprint 5 — Skills, Context, Domain packs
- [Backlog #6] E-012 Enhanced SkillLoader 3-stage progressive disclosure.
- [Backlog #7] E-013 Runtime Prompt Contract Assembly.
- [Backlog #8] E-014 Context Gap Detection (Memory Agent + Research Agent — flesh out the stubs under `cipher/agents/memory_agent/` and `cipher/agents/research/`).
- [Backlog #10] Add ASIL-C, ASIL-D, ASPICE L3, MISRA-C:2012 domain packs under `cipher/gcl/domain_packs/`.

### Sprint 6 — Voice + packaging
- [Backlog #3] Voice pipeline: Web Audio capture in the webview → POST to LLM Gateway → TTS playback. The existing `VoicePanel`/`ArcReactor`/`Waveform` Qt widgets are retired.
- `vsce package` produces `cipher-vscode-1.0.0.vsix`; document sideload + (optional) Marketplace publish.
- Cleanup pass: remove the legacy Qt panels that the webview has replaced (kept available behind `run_poc.py` without `--headless` until Sprint 6 closes).

---

### Sprint 7 — MVP wiring (LOCAL-FIRST)  ◀ ACTIVE

Audit (2026-05-18) showed the platform is ~80% MVP-ready. All 13 V-cycle nodes have real LLM bodies, A2A handler dispatches correctly, LLM Gateway routes Ollama+GCA, adapters are real. Two true blockers remain:

- [S7-1] **DVF wiring into S1N1** — opt-in via config `enable_dvf=true`. Uses `lld_gen_v2.md` (citation-aware prompt) → `run_with_dvf()` → `render_csv_from_crc()`. Backwards-compatible: omit flag and existing `lld_gen_v1.md` path runs unchanged.
- [S7-2] **Config workspace validation on PUT** — `/cipher/config` now rejects bodies whose `workspace_path` doesn't exist as a directory. Users fail fast in the Config panel, not mid-S1N1.
- [S7-3] **Voice TTS** via **pyttsx3** (Windows-native SAPI5; no model download). Lazy import; returns clear error if package missing.
- [S7-4] **Voice STT** via **faster-whisper** (lazy import, `tiny.en` model auto-downloads on first call). Returns 503 with `pip install faster-whisper` instructions if missing — but actually transcribes when installed.
- [S7-5] **End-to-end test**: `POST /cipher/nodes/S1N1/run` with a mocked GCA invoker against a fixture SWC workspace. Confirms REST → CipherOrchestrator → DevNexOrchestrator → artifact write path is healthy.

**Out of MVP scope (deferred — not blockers)**:
- MemoryAgent / ResearchAgent backed by real Memgraph+Qdrant (in-memory MKF fine for MVP demo).
- DVF wired into S2N1..S9N1 (only S1N1 needs it for the LLD-CSV demo).
- 6 empty agent folders (`planner`, `asil_reviewer`, `test_agent`, `compliance`, `tool_agent`, `traceability`) — out of MVP scope.

---

### Sprint 8 — Post-MVP hardening (closed)

- [S8-1] **`.vsix` packaged + installed**. `cipher-vscode-0.1.0.vsix` (15.24 KB, 9 files) built via `npx @vscode/vsce package` and installed with `code --install-extension`. Live headless host bring-up verified (`/cipher/healthz`, `/cipher/infra/status`, config validation all green). Dogfood finding: **Ollama `/api/generate` hung 120s in this environment** — environment-side issue (Ollama daemon needs restart), not a CIPHER bug. LLM Gateway + router code is correct.
- [S8-2] **Generic DVF helper across all nodes**. Refactored S1N1's DVF block into [`DevNexOrchestrator._maybe_invoke_via_dvf`](../cipher/agents/devnex_assistant/core/orchestrator.py) — any LLM-touching node opts in with 3 lines + a v2 prompt file. See [docs/DVF_OPTIN_GUIDE.md](DVF_OPTIN_GUIDE.md) for the per-node recipe and the status table. S1N1 stays green via the new helper; S2N1..S9N1 wiring is ready, prompt content is the next step.
- [S8-3] **MemoryAgent backed by real Memgraph**. New [`MemgraphMkf`](../cipher/agents/memory_agent/memgraph_mkf.py) implements the same `MkfClient` Protocol as `InMemoryMkf`. `build_default_mkf()` probes Memgraph reachability and falls back to in-memory when Memgraph is down — keeps unit tests + offline dev functional. Memgraph queries that fail return `[]` instead of raising, so MemoryAgent degrades gracefully.

---

**MVP Demo path** (after Sprint 7 close):
1. `docker compose up -d` (deploy/local)
2. `ollama pull qwen2.5-coder:1.5b && ollama serve`
3. VSCode → click CIPHER icon → Python host spawns
4. Config tab → fill in SWC + workspace + `enable_dvf=true` → Save
5. Workflow → click S1N1 → DVF runs Draft→Verify→Finalize → validated LLD CSV in `~/.devnex/runs/{run_id}/`
6. (Optional) Voice tab → speak a query → Whisper transcribes → arc reactor reflects state

---

## 3. Definition of Done (project-wide)

- All unit tests in `tests/unit/` pass (`pytest tests/`).
- New endpoints have at least one happy-path test.
- `docs/SPRINT_PLAN.md` updated at sprint close.
- No new uncommitted secrets; `.gitignore` covers `.env`, `__pycache__/`, `*.pyc`, `extension/node_modules/`, `extension/media/` (built artefact, allowed in `.vsix` but not in git).

---

## 4. Risks tracked

1. Python process lifecycle inside VSCode (orphan processes).
2. Port conflicts on 8100/8200 across multiple VSCode windows.
3. Webview CSP — must whitelist `connect-src 127.0.0.1:8100 127.0.0.1:8200` only.
4. User's Python env discovery (`cipher.pythonPath` setting + autodetect `.venv`).
5. `.vsix` signing for distribution.

See `docs/VSIX_DESIGN.md` §7 for mitigations.
