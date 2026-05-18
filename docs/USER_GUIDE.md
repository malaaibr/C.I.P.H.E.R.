---
doc_version: 1.1.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CIPHER — User Guide (First Run)

Step-by-step walkthrough from a clean machine to running your first V-cycle node through the VSCode extension. For deeper reference, see `docs/USER_MANUAL.md`.

Estimated time: **20 minutes** (first time), 30 seconds (subsequent launches).

---

## Step 1 — Install prerequisites

Install once:

1. **Python 3.11+** — https://python.org/downloads
2. **Node.js 20 LTS** — https://nodejs.org/en/download
3. **VSCode** — https://code.visualstudio.com/
4. *(Optional)* **Docker Desktop** if you want the full infra stack.
5. *(Optional)* **Ollama** + `ollama pull qwen2.5-coder:1.5b` if you want a local LLM.

Verify in PowerShell:

```powershell
python --version
node --version
code --version
```

---

## Step 2 — Get CIPHER

Clone (or use the existing folder at `C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo`).

```powershell
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
pip install pytest pydantic fastapi uvicorn httpx pyyaml PyQt6
```

Verify:

```powershell
python -m pytest tests/unit tests/integration -q
# expected: 162 passed (as of Sprint 8 close, 2026-05-18)
```

---

## Step 3 — Build the extension

```powershell
cd extension
npm install
npm run build
```

---

## Step 4 — Package and install the `.vsix`

```powershell
npx @vscode/vsce package -o cipher-vscode-0.1.0.vsix
code --install-extension cipher-vscode-0.1.0.vsix
```

Reload VSCode.

---

## Step 5 — Configure

Open VSCode settings (`Ctrl+,`), search `cipher`, set:

```json
"cipher.pythonPath": "C:\\AI_Agents\\CIPHER_Local_repo\\CIPHER\\CIPHER_Repo\\.venv\\Scripts\\python.exe",
"cipher.repoPath":   "C:\\AI_Agents\\CIPHER_Local_repo\\CIPHER\\CIPHER_Repo"
```

---

## Step 6 — *(Optional)* Start infra

If you want Redis / Memgraph / Qdrant / etc. lit up in the **Infra Status** grid:

```powershell
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo\deploy\local
docker compose up -d
```

Without this step, the dashboard simply shows them as DOWN — CIPHER still runs.

---

## Step 7 — Open the panel

1. Click the **CIPHER** icon in the VSCode activity bar (left rail).
2. The Webview opens on the right side. Status dot starts **yellow** while the Python host spawns.
3. Within ~10 seconds you should see:
   - Status dot turns **green** with text `online — http://127.0.0.1:8100`
   - Output Log view shows `SSE stream open`.
   - The dashboard arc reactor begins spinning.
   - The infra grid populates (UP / DOWN per service).

If status stays yellow >30s, see **USER_MANUAL.md §7 — Troubleshooting**.

---

## Step 8 — Configure the SWC

Click **Config** in the sidebar. Fill in:

| Field | Example |
|---|---|
| SWC name | `Dio` |
| Workspace path | `C:/path/to/your/SWC` |
| Target ASIL | `ASIL-B` |
| Domain pack | `iso26262-asil-b` |

Click **Save**. Output Log will confirm: `Config saved — keys: SWC_name, workspace_path, target_asil, domain_pack`.

---

## Step 9 — Run a single node

1. Click **Workflow** in the sidebar.
2. Click the **S1N1** card (LLD Generation).
3. Watch:
   - Card border turns **yellow** (running) → **green** (done) or **red** (error).
   - Output Log streams progress.
   - Arc reactor changes state on the Dashboard.

What S1N1 does: invokes the LLM (Ollama or GCA) with a citation-aware prompt; runs WF₁–WF₅ validation through the DVF loop; produces an LLD CSV in your workspace.

---

## Step 10 — Run the full V-cycle

Click **Run Full V-Cycle** at the top of the Workflow view. CIPHER walks all 13 nodes in order. If a node needs human approval, a **Review** modal appears — read the prompt, click **Approve** or **Reject**.

---

## Step 11 — Reading the trace

Click **Trace** in the sidebar. The graph shows artifact-flow edges discovered from your run. Click **Refresh** after each run to update.

---

## Step 12 — Stop / restart

| What you want | How |
|---|---|
| Close the panel | Click the X on the Webview, or use **View → Close Editor**. The Python host keeps running. |
| Stop the host | **Command Palette → CIPHER: Restart Python Host**, or kill the `python.exe` in Task Manager. |
| Wipe workflow state | Click **Reset** in the Workflow view. |
| Reload after settings change | **Command Palette → Developer: Reload Window**. |

---

## What to try next

- **Enable DVF (citation-aware mode)** — add `"enable_dvf": true` to Config (POST /cipher/config with the extra key). Now S1N1 runs through Draft-Verify-Finalize: LLM produces a CRC JSON, the validator checks WF₁–WF₆, revisions auto-retry up to `max_revisions`, and the LLD CSV is rendered deterministically from the validated CRC instead of pasted raw from the LLM. Disable the flag (or omit it) to fall back to the legacy direct-LLM path.
- **Voice (real, local)** — install `pyttsx3` for TTS (`pip install pyttsx3`) and/or `faster-whisper` for STT (`pip install faster-whisper`). With both installed: Voice tab → Start → speak → Stop. Audio is transcribed locally (no network), and `/cipher/voice/speak` synthesizes through the host's speakers.
- **Switch domain packs** — change the Config → Domain pack to `iso26262-asil-d` and re-run S1N1. Watch the DVF loop escalate to HITL if citations don't meet the strict criteria.
- **Inspect the events** — `curl -N http://127.0.0.1:8100/events/sse` in a terminal to see the raw stream.
- **Author a SKILL.md** — drop a new file under `cipher/agents/devnex_assistant/skills/definitions/` and the SkillLoader will pick it up at next host start.

---

## Where things live (cheat sheet)

```
extension/                        ← VSCode extension source
  src/extension.ts                ← entry; commands; activation
  src/cipherViewProvider.ts       ← webview lifecycle
  src/pythonHost.ts               ← spawn/probe/restart Python
  webview/index.html              ← the UI you see
cipher/are/a2a_server/
  server.py                       ← FastAPI app
  cipher_routes.py                ← /cipher/* + /events/sse  ← VSIX bridge
cipher/interfaces/web/
  event_bridge.py                 ← non-Qt pub/sub bus
cipher/agents/devnex_assistant/
  core/orchestrator.py            ← 13 V-cycle nodes
  core/dvf_loop.py                ← Draft-Verify-Finalize
docs/
  SPRINT_PLAN.md                  ← current backlog
  VSIX_DESIGN.md                  ← extension design
  BUILD.md                        ← build/package
  USER_MANUAL.md                  ← runtime reference
  USER_GUIDE.md                   ← this file
```

---

## Getting help

1. Read **USER_MANUAL.md §7** — the troubleshooting matrix covers ~90% of issues.
2. Check **VSCode → Output → CIPHER Host** — that's where Python stderr surfaces.
3. Run `pytest tests/unit -q` — if tests fail, the build is broken; don't expect the UI to work.
4. File an issue with: OS version, Python version, Node version, the contents of the **CIPHER Host** output channel, and the last 50 log lines from the Output Log view.

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.1.0 | 2026-05-18 | CIPHER team | Added DVF opt-in + voice install notes under 'What to try next'. |
