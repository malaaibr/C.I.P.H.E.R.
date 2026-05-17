# DEMO RUNBOOK - AUTOSAR Dio Driver (ASIL-B)

| Field | Value |
|-------|-------|
| Document ID | DEMO-DIO-001 |
| Version | 1.0 |
| Audience | ISO 26262 / AUTOSAR review board |
| Duration | ~25 minutes |
| Presenter | CIPHER Tech Lead |
| Date | 2026-05-17 |
| Status | DRAFT |
| Storyboard | [WBS-0002](wbs/WBS-0002-dio-demo-trial.md) |
| Reference CAR | [CAR-004](car/CAR-004-autosar-dio-sws.md) |
| Governing process | PROC-001 (ASDLC v1.0) |

This document is the click-by-click presenter script. It is the concrete
realization of the WBS-0002 phase storyboard (Sec. 3) and Runbook (Sec. 6).
The presenter narrates each step out loud before clicking. Every step has
one Expected visible cue - if it does not appear, the presenter stops and
follows the rollback drill in Sec. 6.

---

## 1. Pre-flight (T-30 minutes)

Run the preflight checker from the repo root. It exits non-zero on any
critical failure, so the presenter must see `RESULT: READY` before
continuing.

```powershell
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo
python scripts/verify_dio_demo_ready.py
```

What "ready" looks like:

```
RESULT: READY - proceed with `python run_poc.py`.
```

Failure recovery cheatsheet:

| Failure line | Cause | Recovery |
|--------------|-------|----------|
| `Python ... < 3.11` | wrong interpreter on PATH | activate the project venv; rerun |
| `workspace file missing: ...` | someone wiped `generated_artifacts/dio_demo_workspace/` | **Escalate to Tech Lead** - regenerate from `docs/wbs/WBS-0002-dio-demo-trial.md` workspace bundle. Do not start the demo. |
| `key present` / `not found on disk` (config) | `cipher_config_dio.json` was edited and now points off-disk | restore the file from git; rerun preflight |
| `NATS/Qdrant/Redis/Memgraph/OPA/MinIO unreachable` | Docker Compose stack is down | `docker compose -f deploy/local/docker-compose.yml up -d` then wait 20s and rerun preflight |
| `no qwen2.5-coder* model installed` | Ollama model not pulled | `ollama pull qwen2.5-coder:1.5b` |
| `Ollama unreachable at http://localhost:11434/api/tags` | Ollama daemon not started | `ollama serve` in a side terminal |
| `port 8100 / 8200 already bound` (INFO) | a previous CIPHER process is still alive | kill it; this is informational, not blocking |

Only one fail line is fully blocking and requires escalation: the workspace
files. Every other failure has a one-command fix above.

---

## 2. Launch sequence (T-5 minutes)

```powershell
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo
python run_poc.py
```

Expected console flow:

```
[CIPHER] Registered skills: ['vcycle.s1n1', ...]
[CIPHER] CipherOrchestrator initialized
[CIPHER] LLM Gateway starting on http://127.0.0.1:8200
[CIPHER] A2A Server starting on http://127.0.0.1:8100
[CIPHER] Unified GUI launched - CIPHER HUD + DevNex Workspace
[CIPHER] Main window shown successfully
```

Visual flow:

1. JARVIS-blue splash screen appears (~7 seconds).
2. Splash fades; the CIPHER HUD (Mode 0, 3-column dashboard) replaces it.

> Splash-window gotcha (see [CLAUDE.md](../CLAUDE.md) "Critical Design Decisions"):
> `quitOnLastWindowClosed` is `False` during the splash and is flipped to
> `True` only inside `_on_splash_done`. If the app exits the instant the
> splash closes, that handler crashed - check the console for the
> `[CIPHER] ERROR in _on_splash_done` traceback. Do not try to reproduce
> live; fall back to the recorded dry-run capture (see Sec. 6).

---

## 3. Audience walkthrough

Each step lists: **Action** (what the presenter does), **Click/Command**
(the exact GUI element or terminal text), **Expected visible cue**, and
**Talking point** (a one-sentence narration).

### Step 1 - Open the HUD

| Field | Value |
|-------|-------|
| Action | Bring the CIPHER window to front. |
| Click/Command | Alt-Tab to the CIPHER window. |
| Expected cue | 3-column HUD visible: nav rail on the left, center "OPEN DevNex WORKSPACE >>" button, right SWC Context panel listing `LLM Backend: Ollama`, `A2A Server: :8100`, `Gateway: :8200`. |
| Talking point | "This is Mode 0 of CIPHER - the cockpit. Both the A2A server and the LLM Gateway are already running locally." |

### Step 2 - Switch into the DevNex workspace

| Field | Value |
|-------|-------|
| Action | Open the DevNex (V-cycle) workspace. |
| Click/Command | Click the green-accent button labelled **OPEN  DevNex  WORKSPACE  >>** in the HUD nav column. |
| Expected cue | Window switches to Mode 1: left "DevNex" sidebar with 6 nav items (**Workflow**, **Trace**, **Review**, **Output**, **Config**, **Voice**), center panel stack, log tail at the bottom. A small `← CIPHER HUD` back-button appears. |
| Talking point | "DevNex is the V-cycle agent - each sidebar item is one cross-cutting view over the same SWC project." |

### Step 3 - Open the Config panel

| Field | Value |
|-------|-------|
| Action | Switch to the Config view. |
| Click/Command | Click **Config** in the DevNex sidebar (last nav item before Voice). |
| Expected cue | Form titled "Project Configuration" with 11 labelled rows (SWC Name, Generic LLD Template, Source Code (.c), Header File (.h), Component LLD Template, Functional Requirements, Inspection Base LLD, HLD Document, Linker File, Map File (.map), Workspace Path) plus a JSON preview pane at the bottom. Two header buttons: **Import Config** (outlined) and **Save Config** (filled). |
| Talking point | "Every V-cycle node reads from this config - one project, one source of truth." |

### Step 4 - Import the Dio demo config

| Field | Value |
|-------|-------|
| Action | Load the pre-built Dio config. |
| Click/Command | Click **Import Config** in the Config panel header. In the file dialog navigate to `generated_artifacts/dio_demo_workspace/` and select `cipher_config_dio.json`. |
| Expected cue | All 11 input rows populate. The JSON preview at the bottom renders `"SWC_name": "Dio"`, `"workspace_path": "C:\\...\\generated_artifacts\\dio_demo_workspace"`, plus the seven file fields pointing at `Dio.c`, `Dio.h`, `Dio_HLD.md`, `Dio_TEMP_LLD.csv`, `G_SWDD_TEMP.md`, `stm32h7xx_flash.ld`, `firmware.map`. The two fields `Functional Requirements` and `Inspection Base LLD` stay empty by design - this is the ASIL-B Dio scope (see [CAR-004](car/CAR-004-autosar-dio-sws.md) Sec. 2). |
| Talking point | "Import is a single click - the audit journal records the config hash so we can prove later that nothing was retyped mid-demo." |

### Step 5 - Save and confirm

| Field | Value |
|-------|-------|
| Action | Persist the loaded config so the orchestrator sees it. |
| Click/Command | Click **Save Config** (filled blue button to the right of Import Config). |
| Expected cue | Preview pane re-renders. A `config.json saved` line appears in the log tail at the bottom. |
| Talking point | "The orchestrator is lazy-initialised on the first node run, so saving now is what makes the workspace 'live'." |

### Step 6 - Switch to the Workflow panel

| Field | Value |
|-------|-------|
| Action | Switch the panel stack to the V-cycle workflow view. |
| Click/Command | Click **Workflow** in the DevNex sidebar. |
| Expected cue | Workflow panel renders: top-left action area with **RUN ALL** + reset button, sidebar list of nodes grouped by phase (S1 - LLD Generation, S2, S3, ...), canvas showing the node graph centered on S1 nodes. The detail strip across the bottom shows NODE / SDLC PHASE / TRACES TO / PROGRESS / OUTPUT / STATUS columns. |
| Talking point | "Each node is one ASDLC step. The traces-to column shows the canonical S1N1 -> S9N1 traceability arc PROC-001 mandates." |

### Step 7 - Run S1N1 (UC 1.1 - LLD Generation, ASDLC gate G2)

| Field | Value |
|-------|-------|
| Action | Trigger the LLD generation node. |
| Click/Command | In the Workflow sidebar list, click the row labelled `S1N1  N1 - Input Collection & LLD Gen`. |
| Expected cue | Sidebar status dot for S1N1 turns from gray to amber (running), then green (done). The Output log tail streams: `[S1N1] starting...`, `[S1N1] LLM call ...`, `[S1N1] wrote Dio_TEMP_LLD_updated.csv`, `[S1N1] complete`. The detail strip's STATUS cell shows `DONE`. |
| Talking point | "This is UC 1.1 - the HLD excerpt for four AUTOSAR APIs feeds the LLM via the gateway, GCA validates, the LLD CSV lands in the workspace." |

### Step 8 - Inspect the generated LLD

| Field | Value |
|-------|-------|
| Action | Open the freshly-generated LLD CSV. |
| Click/Command | In an Explorer window (or `Invoke-Item`), open `generated_artifacts/dio_demo_workspace/Dio_TEMP_LLD_updated.csv`. |
| Expected cue | CSV opens with a header row `REQ_ID,CATEGORY,DESCRIPTION` and at least four data rows, one per API (`Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`, `Dio_GetVersionInfo`). No empty cells. |
| Talking point | "Schema is fixed by the GCA contract - if a row was malformed, S1N1 would have failed loudly before the file was written." |

### Step 9 - Switch to the Trace panel

| Field | Value |
|-------|-------|
| Action | Show the traceability surface. |
| Click/Command | Click **Trace** in the DevNex sidebar. |
| Expected cue | Trace panel renders with a filter bar at the top, a graph canvas in the centre, and node cards along the side. |
| Talking point | "The Trace view consumes the same artifacts S1N1 just wrote - nothing here is re-computed, it is the same DAG." |

### Step 10 - Walk the upward HLD trace

| Field | Value |
|-------|-------|
| Action | Demonstrate the upward link from one LLD row to its HLD requirement. |
| Click/Command | In the Trace filter bar, scope to `SWC = Dio`. Pick the node card for `Dio_FlipChannel` (or any single LLD row). Click the upward edge to its parent HLD. |
| Expected cue | A graph edge highlights, the parent card shows `HLD-DIO-001` and opens `generated_artifacts/dio_demo_workspace/Dio_HLD.md` (or quotes the relevant heading inline). |
| Talking point | "Bottom-up trace: from an LLD row to the HLD requirement that justifies it - this is the audit evidence ISO 26262 Part 8 Clause 8 asks for." |

---

## 4. Phase-gate cues

A reviewer should be able to glance at the screen and say "phase X has
passed" without reading any text. The table below pins each ASDLC gate to
its visible moment.

| ASDLC gate ([WBS-0002](wbs/WBS-0002-dio-demo-trial.md) Sec. 3) | Visible moment | Where on screen |
|--------------------------|----------------|-----------------|
| **G0** - Architecture Review | Tech Lead recites the UC plan as the HUD comes up | Terminal where `python run_poc.py` was launched |
| **G1** - Foundation Fixes | Preflight green (`RESULT: READY`) | Pre-flight terminal output (Sec. 1) |
| **G2** - UC 1.1 LLD Gen (S1N1) | S1N1 status dot goes green; CSV file appears in workspace | Step 7-8 of Sec. 3 |
| **G3** - ASIL Gate (UC 3.1) | Review panel shows `HOLD` decision (run S1N3 if exposed, otherwise narrate from CSV) | DevNex sidebar -> **Review** |
| **G3a** - Audit Trail | New rows in `audit.db` (one per LLM/GCA call) | Side terminal: `sqlite3 audit.db "SELECT count(*) FROM audit_records;"` |
| **G4** - Post-Merge Semantic Check (UC 4.4) | "0 overlaps" line in Output log; report viewer opens | DevNex Output panel after running S4 family |
| **G4a** - Full Traceability Matrix (S9N1) | Trace graph fully populated, no orphan node cards | Trace panel, Step 9-10 of Sec. 3 |
| **G4b** - Audience Q&A (UC 4.1) | Live answer to audience question, with sources cited | Trace panel filter bar |

Per WBS-0002 Sec. 3 footnote: G5 is ASIL-D only; the ASIL-B Dio path
terminates at G4 with HOLD advisory archived.

---

## 5. Q&A handles

Three pre-seeded questions the presenter can answer authoritatively without
leaving the demo state. Each one names the exact panel/file to open.

### Q1 - "What if the LLM hallucinates a requirement?"

- **Where to look:** DevNex **Review** panel (sidebar nav).
- **What to show:** the ASIL gate decision card (UC 3.1) showing rule-hit
  enumeration (MISRA R1.3, R14.4 etc.).
- **Talking point:** "Hallucinated rows fail the GCA contract before they
  reach the LLD CSV. If a syntactically-valid but semantically-wrong row
  slips through, the ASIL gate flags it and the workflow halts at HOLD -
  nothing reaches Code or Test."

### Q2 - "How is ASIL-B enforced?"

- **Where to look:** DevNex **Review** panel + `cipher/agents/devnex_assistant/configs/ruleset.yaml`.
- **What to show:** the ruleset YAML (`max_gca_retries: 3`, MISRA rule list)
  side-by-side with the Review panel's HOLD line.
- **Talking point:** "ASIL-B is enforced in two places: the GCA ruleset
  drives line-level checks at generation time, and the ASIL gate fires a
  HOLD if any single rule is violated. Both are recorded in the audit
  journal as signed records."

### Q3 - "Show me the trace from a symbol in `firmware.map` back to its HLD requirement."

- **Where to look:** Trace panel; secondary file: `generated_artifacts/dio_demo_workspace/firmware.map`.
- **What to show:** open `firmware.map`, pick any of the four Dio symbols
  (e.g. `Dio_FlipChannel`), then back in the Trace panel follow the chain
  Symbol -> Code function -> LLD row -> HLD requirement `HLD-DIO-001` in
  `Dio_HLD.md`.
- **Talking point:** "Bottom-up trace from binary back to requirement is
  what makes the artifact set audit-ready - no orphan, no manual
  spreadsheet."

---

## 6. Rollback / fallback drills

One concrete fallback per failure scenario. The presenter narrates the
fallback aloud (transparency policy, see [WBS-0002](wbs/WBS-0002-dio-demo-trial.md) Sec. 7).

| Scenario | Symptom | Concrete fallback |
|----------|---------|-------------------|
| **S1N1 errors out mid-run** | Output log shows `[S1N1] FAILED:` followed by a traceback; sidebar dot goes red | Re-run S1N1 once (idempotent). If the second run also fails, switch the LLM Gateway to mock mode (`set CIPHER_USE_MOCK_GCA=1` and restart `run_poc.py`) and re-run; the mock returns the canned Dio LLD CSV from the dry-run capture. |
| **GCA exhausts retries** | Log shows `GCA call failed after 3 retries`; this is the `max_gca_retries` value defined in `cipher/agents/devnex_assistant/configs/ruleset.yaml` | Open the Config panel, set the ruleset override via `max_gca_retries: 5` in `config.json`, Save, re-run. If still failing, switch to `CIPHER_USE_MOCK_GCA=1` as above. |
| **Ollama times out** | Log shows `httpx.ReadTimeout` against `localhost:11434` | In a side terminal, restart with `ollama serve` and verify `ollama list` shows `qwen2.5-coder:1.5b`. If Ollama keeps stalling, switch the LLM Gateway to the recorded-response stub via `CIPHER_USE_MOCK_GCA=1`. |
| **Docker stack drops mid-demo** | Preflight rerun (in a side terminal) shows `MinIO/Redis unreachable` | `docker compose -f deploy/local/docker-compose.yml up -d`; the workspace is filesystem-backed so the demo can complete on local files even if MinIO is briefly absent. |
| **GUI crash on splash close** | Window vanishes after splash; console shows `[CIPHER] ERROR in _on_splash_done` | Do not retry live - fall back to the recorded dry-run capture (per [WBS-0002](wbs/WBS-0002-dio-demo-trial.md) Sec. 4). |

> **Presenter note (audit.db hygiene):** if a prior dry-run polluted the audit journal and a clean ledger is desired before the live audience run, the presenter may delete `audit.db` at the repo root (`Remove-Item audit.db`) before launching `run_poc.py`. This is a manual judgment call - not enforced by the preflight, not required by WBS-0002.

---

## 7. Post-demo capture

Within five minutes of closing the audience Q&A, capture and archive the
following artifacts. The archive root is `generated_artifacts/<run_id>/`
where `<run_id>` is an ISO-8601 stamp (e.g. `2026-05-17T1430Z-dio-demo`).

| Artifact | Source path | Why |
|----------|-------------|-----|
| Generated LLD CSV | `generated_artifacts/dio_demo_workspace/Dio_TEMP_LLD_updated.csv` | UC 1.1 output - WBS-0002 Sec. 3 G2 |
| ASIL review JSON | `generated_artifacts/dio_demo_workspace/asil_review_dio.json` (if produced) | UC 3.1 decision evidence - G3 |
| ASIL review markdown | `generated_artifacts/dio_demo_workspace/asil_review_dio.md` (if produced) | Human-readable G3 evidence |
| Overlap report | `generated_artifacts/dio_demo_workspace/overlap_report.json` (if G4 ran) | UC 4.4 evidence |
| Full traceability matrix | `generated_artifacts/dio_demo_workspace/Full_Traceability_Matrix.csv` (if G4a ran) | UC 1.4 / S9N1 - the audit headline |
| Audit journal snapshot | copy `audit.db` (SQLite file at repo root) | Signed AuditRecord per LLM/GCA call - PROC-001 evidence |
| Screen recording | OBS/Snipping Tool capture, full demo window | Replay for absent reviewers |
| Terminal transcript | output of `python run_poc.py` redirected to `run_poc.log` | LLM-call timestamps |

Suggested capture command (PowerShell):

```powershell
$run = "2026-05-17T1430Z-dio-demo"
$dst = "generated_artifacts\$run"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item generated_artifacts\dio_demo_workspace\* $dst -Recurse
Copy-Item audit.db $dst -ErrorAction SilentlyContinue
```

---

## 8. Open issues for the presenter

Mirror of [WBS-0002](wbs/WBS-0002-dio-demo-trial.md) Sec. 5 risks, reframed
as actionable checks the presenter does the morning of the demo.

- **CAR-004 release tag drift.** If the AUTOSAR R24-11 release tag cited in
  [CAR-004](car/CAR-004-autosar-dio-sws.md) Sec. 5 turns out to be wrong by
  demo time, swap to the R23-11 link in CAR-004 Sec. 5 before the audience
  arrives. Tech Lead owns this check.
- **ASIL gate false-PASS (WBS-0002 R1).** If a dry run the night before
  shows G3 returning PASS instead of HOLD for ASIL-B, inject a deliberate
  MISRA R14.4 violation into the LLD CSV and narrate the fault injection
  aloud.
- **Traceability matrix orphan rows (WBS-0002 R2).** If the Trace panel
  shows any orphan card, swap in the pre-staged golden matrix at
  `demo/dio/golden/Full_Traceability_Matrix.csv` and explicitly call out
  the swap.
- **GCA retry exhaustion (WBS-0002 R3).** Have `CIPHER_USE_MOCK_GCA=1` set
  in a stand-by PowerShell window so the swap is one keystroke if S1N1
  hangs on a network flake.
- **MinIO write fails (WBS-0002 R4).** Demo is filesystem-backed via
  `workspace_path`, so a MinIO outage is cosmetic - show the file in
  Explorer instead of the MinIO console.
- **Langfuse traces lag (WBS-0002 R5).** Skip the Langfuse tab if traces
  have not appeared by Step 7; show the OTel span JSON from `audit.db`
  instead.
- **UC 4.4 false SemanticConflictError (WBS-0002 R6).** If S4 raises on the
  stub map, override `asil_level="A"` for the demo (downgrade severity) and
  note the override aloud.

---

*CIPHER Tech Lead - DEMO-DIO-001 v1.0 - 2026-05-17*

---

## 9. Full Demo extension (5-component walkthrough)

Sections 1-8 above are the canonical **Dio-only abbreviated demo** ([WBS-0002](wbs/WBS-0002-dio-demo-trial.md)). This section extends that script to the **Full Demo** ([WBS-0003](wbs/WBS-0003-full-demo-trial.md)) - a 5-component vertical-stack walkthrough that processes Det, Port, Dio, IoHwAb, and LedActuator through the same ASDLC pipeline and joins them at the end via a cross-component traceability matrix. Section 9 is **additive**, not replacing: a presenter who is short on time runs §1-§8 only and stops there.

### 9.1 When to use

Trigger phrase. The presenter says, on stage, some variant of: *"Now let me show you the whole stack, not just one driver."* That sentence is the explicit transition from the Dio-only narrative to the Full Demo. Up to that point, sections 1-8 stand on their own; from that point, §9.2 onward applies.

Audience signals that warrant the transition:
- A reviewer asks "what does Dio call into?" or "what calls Dio?" - the answer is the rest of the stack, and §9 is the demo of that answer.
- The audience has at least 20 additional minutes of attention budget (Full Demo adds ~20-25 minutes on top of the Dio-only ~25).
- Preflight delta (§9.2 below) has passed.

If any of these is false, do **not** transition. Close with §8 and the post-demo capture in §7. The Dio-only path is the canonical fallback - this is recorded explicitly in [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §1.

### 9.2 Preflight delta

After the standard preflight in §1 returns `RESULT: READY`, the presenter runs the Full Demo delta check:

```powershell
# Confirm all 5 component HLDs are present
Get-ChildItem generated_artifacts\dio_demo_workspace\*_HLD.md | Select-Object Name
# Expect: Det_HLD.md, Dio_HLD.md, IoHwAb_HLD.md, LedActuator_HLD.md, Port_HLD.md

# Confirm all 5 cipher_config_*.json are present
Get-ChildItem generated_artifacts\dio_demo_workspace\cipher_config_*.json | Select-Object Name
# Expect: cipher_config_det.json, _dio, _iohwab, _ledactuator, _port

# Confirm all 5 source bundles + Dio_Cfg.h
foreach ($c in 'Det','Port','Dio','IoHwAb','LedActuator') {
    if (-not (Test-Path "generated_artifacts\dio_demo_workspace\$c.c"))  { "MISSING: $c.c" }
    if (-not (Test-Path "generated_artifacts\dio_demo_workspace\$c.h"))  { "MISSING: $c.h" }
}
Test-Path generated_artifacts\dio_demo_workspace\Dio_Cfg.h
# Expect: no MISSING lines; Dio_Cfg.h = True

# Confirm the regenerated firmware.map carries all 5 components
Select-String -Path generated_artifacts\dio_demo_workspace\firmware.map -Pattern `
    'Port_Init','Det_Init','Dio_WriteChannel','IoHwAb_Init','LedActuator_MainFunction'
# Expect: 5 match lines
```

What `READY-FULL` looks like: no `MISSING:` lines, `Dio_Cfg.h` returns `True`, and the Select-String emits 5 hit lines. If any check fails, fall back to §1-§8 (Dio-only) and narrate the downgrade aloud per the transparency policy ([WBS-0002](wbs/WBS-0002-dio-demo-trial.md) §7).

### 9.3 Recommended import order

**Bottom-up: Det -> Port -> Dio -> IoHwAb -> LedActuator.** Rationale and risk basis are in [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-A and §8.1. The order is presenter-controlled: the Config panel imports one component at a time. Reset the panel between components only if a stale field would mislead the audience; otherwise let imports overwrite.

| # | Component | One-line description | Config to import | Expected S1N1 output filename | ASDLC G3 audience cue |
|---|-----------|----------------------|------------------|-------------------------------|------------------------|
| 1 | **Det** | BSW dev-error tracer; the bottom of the FFI argument | `cipher_config_det.json` | `Det_TEMP_LLD_updated.csv` (≥3 rows: Init, ReportError, GetVersionInfo) | `[G3] decision=PASS` - this is the **only** PASS of the demo; narrate "Det is QM, so the gate passes; the next four will all HOLD because they're ASIL-B." |
| 2 | **Port** | MCAL pin configurer; init-only path | `cipher_config_port.json` | `Port_TEMP_LLD_updated.csv` (≥2 rows: Port_Init, Port_GetVersionInfo) | `[G3] decision=HOLD` - first ASIL-B HOLD; narrate "Port owns pin direction; Dio cannot operate without it." |
| 3 | **Dio** | MCAL digital I/O; the WBS-0002 driver | `cipher_config_dio.json` | `Dio_TEMP_LLD_updated.csv` (≥4 rows: Write/Read/Flip/GetVersionInfo) | `[G3] decision=HOLD` - identical to §3 Step 7-8 of this runbook. |
| 4 | **IoHwAb** | ECU abstraction over Dio; **synthesized** | `cipher_config_iohwab.json` | `IoHwAb_TEMP_LLD_updated.csv` (≥4 rows: Init + Get/Set LedOut + Get Switch) | `[G3] decision=HOLD` - narrate "ASIL-B by inheritance from Dio (CAR-007 §5)." |
| 5 | **LedActuator** | Application SWC; **synthesized** vendor SWC | `cipher_config_ledactuator.json` | `LedActuator_TEMP_LLD_updated.csv` (≥2 rows: Init + MainFunction) | `[G3] decision=HOLD` - final ASIL-B HOLD; narrate "Application SWC ASIL-B claim attaches to the instance, not the template (CAR-008)." |

**Pacing.** Per-component end-to-end (G0 -> G4a in sequence) is the recommended pacing - audience holds the "one component, one vertical slice" mental model better than batched-by-phase. See [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §8.2 for the rationale.

**Optional batch break.** If [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-B fires (LLM token budget pressure), insert a 5-minute audience Q&A break after Dio (component 3). This splits the load: Det+Port+Dio first (normative-SWS provenance), pause, then IoHwAb+LedActuator (synthesized provenance). The break is also a natural narrative pivot - the second half opens with the "now we leave the SWS-normative zone" framing for §9.5.

### 9.4 Cross-component traceability beat

After the fifth per-component G4a completes, open the merged `Full_Traceability_Matrix.csv` (produced by the cross-component S9N1 pass - see [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §4). This is the audience-meaningful "aha" moment of the Full Demo.

| Field | Value |
|-------|-------|
| Action | Open the cross-component matrix and click through one row end-to-end. |
| Click/Command | `Invoke-Item generated_artifacts\dio_demo_workspace\Full_Traceability_Matrix.csv`. In the CSV viewer (or the DevNex Trace panel), pick the `LLD-LEDACT-004` row. |
| Expected cue | The row populates **all five HLD-ID columns**: `HLD_LEDACT=HLD-LEDACT-004`, `HLD_IOHWAB=HLD-IOHWAB-003`, `HLD_DIO=HLD-DIO-001`, `HLD_PORT=HLD-PORT-001`, `HLD_DET=HLD-DET-002`. The `CODE_FUNCTION` cell reads `LedActuator_MainFunction`, the `FILE` cell reads `LedActuator.c`. |
| Talking point | "From one application-layer LLD line we walk up to LedActuator's HLD, down through IoHwAb to Dio, sideways to Port (pin direction) and Det (error reporting). Five components, one matrix, one click - this is ISO 26262 Part 6 Clause 7 integration evidence." |

**FFI fold-in.** Immediately after the click, narrate the Det QM cross-ASIL caller story ([WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-E). One sentence: "Note Det is QM but Dio (ASIL-B) calls it - the FFI argument in Det_HLD §6 is that Det_Buffer is a write-only sink, so corruption cannot propagate back into Dio's control flow." If a reviewer pushes for more, open `Det_HLD.md` §6 directly; otherwise move on.

### 9.5 Synthesized-HLD caveat for the audience

A reviewer who has read [CAR-004](car/CAR-004-autosar-dio-sws.md) and seen its normative SWS pedigree may, when `IoHwAb_HLD.md` or `LedActuator_HLD.md` appears on screen, ask: **"Where is the SWS for this one?"** The presenter has a scripted three-sentence reply that surfaces the caveat without losing credibility:

> "There isn't one. AUTOSAR doesn't publish a normative SWS for the I/O hardware abstraction module - the PDF named `AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` self-describes as an implementation guideline, not a standard; the actual structural anchor is the Layered Software Architecture explanatory document. Same for LedActuator - there is no SWS for any application SWC; the structural anchor is the AUTOSAR Software Component Template ([CAR-008](car/CAR-008-autosar-swc-template-reference.md)), and the ASIL-B claim attaches to this LedActuator instance, not to the template."

Bookmark `CAR-007` §0 "NO-SWS WARNING" and `CAR-008` §0 "Template vs SWS" for direct citation if the reviewer presses further. The `PROVENANCE` column proposal in [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §8.4 (`SWS-NORMATIVE` vs `VENDOR-DERIVED`) is the post-demo follow-up commitment the presenter offers in closing.

### 9.6 Fallback drills

Extends §6 of this runbook and [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5.

| Scenario | Symptom | Concrete fallback |
|----------|---------|-------------------|
| **Falling behind on time at component 4** | Wall-clock at +50 min since launch and IoHwAb not yet at G2 | **Drop LedActuator.** End at IoHwAb. The cross-component matrix in §9.4 still has 4-row coverage (Det -> Port -> Dio -> IoHwAb); narrate the LedActuator omission aloud and offer "we capture LedActuator post-demo in the same artifact set." Saves ~5 minutes. |
| **LLM throughput collapses mid-component-2 or later** | GCA retries exhausted on Port or Dio S1N1; rerun also fails; mock GCA flag already in use ([WBS-0002](wbs/WBS-0002-dio-demo-trial.md) §5 R3 fallback active) | **Downgrade to WBS-0002.** Stop the Full Demo. Skip to §8 (post-demo capture) and explicitly frame what just happened as "the abbreviated story - we ran out of LLM budget mid-stack, but the Dio path you already saw is the canonical demonstration." Cross-link [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-B. |
| **Cross-component matrix shows orphan rows** | `Full_Traceability_Matrix.csv` has empty HLD_IOHWAB or HLD_DIO cells on the LedActuator row | Pre-staged golden matrix at `generated_artifacts/dio_demo_workspace/golden/Full_Traceability_Matrix.csv` (assemble during preflight if missing). Swap in, narrate the swap aloud, then re-take the §9.4 click-through. Cross-link [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-A. |
| **Reviewer reads CAR-007 / CAR-008 mid-demo and challenges live** | Reviewer interrupts at IoHwAb or LedActuator import: "Show me the SWS or skip this component" | Stop. Read §9.5 verbatim. Then open `CAR-007` §0 NO-SWS WARNING (or `CAR-008` §0 Template-vs-SWS WARNING) on screen and let the reviewer read silently for 30 seconds. Resume only when the reviewer nods. Cross-link [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-D. |
| **`firmware.map` symbol collision raises `SemanticConflictError` at any G4** | UC 4.4 stderr shows duplicate symbol or overlapping `.text` region | The Full Demo map is namespaced by module prefix (`Port_*`, `Det_*`, `Dio_*`, `IoHwAb_*`, `LedActuator_*`) and attributes each symbol to its `<source>.c.obj`. If the check still raises, downgrade `asil_level="A"` for that one component's G4 only and narrate the override aloud. Cross-link [WBS-0003](wbs/WBS-0003-full-demo-trial.md) §5 R-C. |

> **Presenter discipline note.** The Full Demo's value proposition is the cross-component matrix in §9.4 - **not** any single component. If any of the first four components stumbles in a way that threatens the §9.4 demo, the presenter MAY skip that component's G4 and proceed straight to the matrix as long as at least three components reached G2 cleanly. The matrix will render with three- or four-component coverage; that is still a stronger story than the Dio-only path.

---

*CIPHER Tech Lead - DEMO-DIO-001 v1.0 §9 (Full Demo extension) - 2026-05-17*
