---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CIPHER — VSCode Extension

In-editor surface for the **CIPHER** multi-agent platform (Cognitive Intelligent Platform for Holistic Embedded R&D Automation). Opens a sub-panel inside VSCode that mirrors the CIPHER HUD and DevNex workspace, and drives the Python host over loopback HTTP/SSE.

## Architecture

```
VSCode Webview  ──postMessage/HTTP──►  Extension Host (TS)
                                            │
                                            │ spawn
                                            ▼
                                  run_poc.py --headless
                                            │
                                            ▼
                            FastAPI :8100 (A2A + /cipher/* + SSE)
                            FastAPI :8200 (LLM Gateway)
                                            │
                                            ▼
                            CipherOrchestrator → DevNexOrchestrator
```

See `docs/VSIX_DESIGN.md` in the repo root for the full design pass.

## Sprint 1 status

- ✅ `package.json` scaffolded with activity-bar view + commands + config
- ✅ Extension entry (`src/extension.ts`) registers commands
- ✅ `CipherViewProvider` hosts the webview, wires postMessage
- ✅ `PythonHost` spawns `run_poc.py --headless` and watches health
- ✅ Empty webview UI (`webview/index.html`) renders JARVIS theme and shows host status
- ⏭ Sprint 2: full Workflow/Output/Config panels in webview

## Develop

```powershell
cd extension
npm install
npm run build
# Then F5 in VSCode with this folder open to launch an Extension Development Host.
```

## Package

```powershell
npm run package   # produces cipher-vscode-0.1.0.vsix
code --install-extension cipher-vscode-0.1.0.vsix
```

## Settings

- `cipher.pythonPath` — interpreter to run `run_poc.py --headless`
- `cipher.repoPath`   — absolute path to CIPHER repo (defaults to workspace)
- `cipher.ports.a2a` / `cipher.ports.gateway`
- `cipher.showEditorButton`

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added (see docs/DOC_VERSIONING.md). |
