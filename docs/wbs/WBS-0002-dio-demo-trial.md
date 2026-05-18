---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# WBS-0002: AUTOSAR Dio Driver — CIPHER ASDLC Demo Trial

| Field | Value |
|-------|-------|
| Document ID | WBS-0002 |
| Version | 1.0 |
| ASPICE | MAN.3 — Project Management; SWE.1–SWE.6 — Software Engineering |
| ASIL Applicability | B |
| Author | CIPHER Tech Lead |
| Date | 2026-05-17 |
| Status | DRAFT |

- **Driver under demo:** AUTOSAR Classic Dio Driver (Digital I/O) — ASIL-B per SWS
- **Reference CAR:** [CAR-004](../car/CAR-004-autosar-dio-sws.md)
- **Reference ADR:** ADR-0003 POC Scope Lock
- **Governing process:** PROC-001 (ASDLC v1.0)

---

## 1. Demo Goal

Demonstrate the full CIPHER ASDLC pipeline driving an ISO 26262 ASIL-B AUTOSAR Dio Driver from a raw SWS excerpt to a code-linked, traced, ASIL-gated, and audit-journaled artifact set within a single live session. The audience watches the same four-API surface (`Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`, `Dio_GetVersionInfo`) move phase-by-phase through gates G0–G4 with every CIPHER role producing a visible, named artifact. Success is shown when the Full Traceability Matrix renders with no orphan HLD/LLD/Code/Test rows and the ASIL gate returns a documented HOLD decision.

---

## 2. Scope

### 2.1 In Scope

| Item | Notes |
|------|-------|
| `Dio_WriteChannel` | Channel-level write, scalar-only |
| `Dio_ReadChannel` | Channel-level read, scalar-only |
| `Dio_FlipChannel` | Toggle, derived behavior |
| `Dio_GetVersionInfo` | Version surface — trivial, demonstrates infra path even when logic is minimal |
| HLD → LLD generation via UC 1.1 | One pass, S1N1 only |
| ASIL-B gate via UC 3.1 | HOLD decision expected, archived |
| Post-merge UC 4.4 semantic / overlap check | Stubbed map + LD file for the four APIs |
| Q&A demo via UC 4.1 | One audience-driven question against the matrix |
| Full traceability via UC 1.4 / S9N1 | `Full_Traceability_Matrix.csv` rendered |

### 2.2 Out of Scope

- MCAL hardware register access — port registers are stubbed (no Dio_Port* family, no Dio_MaskedWritePort).
- Port direction configuration — owned by the Port Driver, not Dio.
- ASIL-C / ASIL-D paths — gate G5 not exercised; demo is ASIL-B only.
- Multi-port/grouped APIs (`Dio_WriteChannelGroup`, `Dio_ReadChannelGroup`) — deferred.
- AUTOSAR ARXML parsing (per ADR-0003 §3.2) — CAR-004 provides the API table directly.
- Any V-cycle stage beyond S1N1 + the ASIL/trace overlays — POC scope lock applies.
- Voice interface, GUI HUD theming work — demo runs against the CLI/A2A surface.

---

## 3. Phase-by-Phase Storyboard

The following table maps each ASDLC gate (PROC-001 §3) to its CIPHER role, the use case invoked, the artifact flow, and the cue the audience will see on screen.

| ASDLC Phase | Owner | CIPHER UC invoked | Input artifact | Output artifact | Visible cue for audience | Pass gate |
|-------------|-------|------------------|----------------|-----------------|-------------------------|-----------|
| **G0 — Architecture Review** | Tech Lead | UC catalog read-through (PROC-001 §4.1) | CAR-004 SWS API table; this WBS | UC plan acknowledgement (terminal echo of selected UC IDs) | Terminal banner `[G0] UC plan approved: 1.1, 3.1, 4.4, 4.1, 1.4` | UC plan printed, QA-PROC verbal ack |
| **G1 — Foundation Fixes** | DEV + QA-TEST | n/a (pre-flight) | `cipher/` working tree at HEAD | `pytest tests/ -v` green report | Pytest progress bar reaches 100% green; no red lines | `pytest` exits 0 |
| **G2 — UC 1.1 LLD Generation (S1N1)** | DEV | UC 1.1 (LLD Generation) via `agents/devnex/skills/vcycle_s1n1/skill.py` | `Dio_HLD_excerpt.md` (4 APIs from CAR-004) | `Dio_TEMP_LLD_updated.csv` written to MinIO bucket `cipher-artifacts/dio/`; `section_layout.json` | New CSV row count ≥ 4 printed to terminal; MinIO console refresh shows the object | CSV present, ≥ 4 rows, schema `REQ_ID, CATEGORY, DESCRIPTION` |
| **G3 — ASIL Gate (UC 3.1)** | QA-TEST (executing) / QA-PROC (witnessing) | UC 3.1 (ASIL Review) via `AsilGate.evaluate()` | `Dio_TEMP_LLD_updated.csv`; ASIL level `B` | `asil_review_dio.json` + `asil_review_dio.md` (decision: HOLD) | Color-banded `HOLD` line in terminal; markdown opens in viewer | `decision == HOLD`, MISRA rule hits listed (R1.3, R14.4 at minimum) |
| **G3a — Audit Trail** | QA-PROC | UC 5.x (Audit Journal append) via `gcl/audit_journal/journal.py` | LLM + GCA call records from G2/G3 | New rows in `audit.db` table `audit_records` | `sqlite3 audit.db "SELECT count(*) ..."` displayed; count increments live | At least one signed AuditRecord per LLM/GCA call |
| **G4 — Post-Merge Semantic Check (UC 4.4)** | DEV | UC 4.4 (Post-Merge Semantic Check) via `DevNexOrchestrator.run_uc4_4_semantic_check` | Stub `build/dio_firmware.map` + `src/dio_stub.ld` | `overlap_report.json` + `semantic_conflict_report.md` | "No overlap" banner; report opens in viewer | Exit code 0; no `SemanticConflictError`; `overlap_report.json` validates |
| **G4a — Traceability Matrix (UC 1.4 / S9N1)** | QA-PROC | UC 1.4 (Full Trace) | LLD CSV + stub code/test links | `Full_Traceability_Matrix.csv` (S9N1 canonical name per PROC-001 §4.2) | Matrix opens in CSV viewer; row count = 4 APIs × link types; no empty cells | Zero orphan rows (every HLD_ID has LLD_ID, CODE_FUNCTION, FILE, LINE) |
| **G4b — Audience Q&A (UC 4.1)** | Tech Lead (driver) | UC 4.1 (Trace Q&A) | Audience question (live) | `QAAnswer` object printed with `sources[]` | Answer + cited rows printed to terminal; sources point to matrix rows | `QAAnswer.sources` non-empty, cites Full_Traceability_Matrix.csv |

**Note on G5:** Per PROC-001 §3 Phase 5, G5 is ASIL-D only. ASIL-B demo path terminates at G4 with HOLD advisory archived. No Safety Engineer sign-off is exercised live.

---

## 4. Demo Prerequisites

The following must be true at demo start. The Tech Lead runs the pre-flight checklist 30 minutes before the audience arrives.

| # | Prereq | Verification command | Pass condition |
|---|--------|---------------------|----------------|
| P1 | CAR-004 present and readable | `Get-Content docs/car/CAR-004-autosar-dio-sws.md \| Select-Object -First 5` | File exists, frontmatter renders |
| P2 | `pytest` green on `tests/` | `python -m pytest tests/ -v --tb=short` | Exit 0, all pass |
| P3 | Docker Compose DRS up | `docker compose -f deploy/local/docker-compose.yml ps` | All services `healthy` |
| P4 | MinIO bucket `cipher-artifacts` exists | `mc ls cipher/cipher-artifacts` | Bucket listed |
| P5 | Redis reachable | `redis-cli ping` | `PONG` |
| P6 | Langfuse UI reachable | open `http://localhost:3000` | Login page renders |
| P7 | OPA sidecar healthy | `curl -s http://localhost:8181/health` | HTTP 200 |
| P8 | Stub HLD excerpt staged | `Test-Path demo/dio/Dio_HLD_excerpt.md` | `True` |
| P9 | Stub map + LD for UC 4.4 staged | `Test-Path build/dio_firmware.map; Test-Path src/dio_stub.ld` | Both `True` |
| P10 | Audit journal DB empty (clean slate) | `sqlite3 audit.db "SELECT count(*) FROM audit_records;"` | `0` |
| P11 | GCA HTTP driver reachable (or MockGCABridge swapped in) | `curl -s $env:GCA_URL/health` or env var `CIPHER_USE_MOCK_GCA=1` | HTTP 200 or mock flag set |

If any prereq fails the demo does not start — fall back to the recorded dry-run capture (see §5).

---

## 5. Risks and Fallbacks

| # | Risk | Likelihood | Impact | Fallback |
|---|------|------------|--------|----------|
| R1 | **ASIL gate misfires** — `AsilGate.evaluate()` returns `PASS` instead of `HOLD` for ASIL-B Dio LLD (false negative) | Medium | High — undermines the safety story | Tech Lead force-injects a `R14.4` violation into the LLD CSV before G3 to guarantee a HOLD; show the diff to the audience as "intentional fault injection to prove the gate fires" |
| R2 | **Traceability matrix renders empty / orphan rows** — `_CSV_MAP` filename mismatch (F-001 class bug) or stub code paths missing | Medium | High — G4a fails visibly | Pre-stage a known-good `Full_Traceability_Matrix.csv` in `demo/dio/golden/`; on failure, swap it in and explicitly call out the swap to maintain transparency |
| R3 | **GCA retry exhausted** during UC 1.1 — network flake or rate limit, all 3 retries fail (PROC-001 §5.3) | Medium | Critical — demo dead at G2 | Set `CIPHER_USE_MOCK_GCA=1` to force `MockGCABridge`; the mock returns a canned Dio LLD CSV recorded from a clean run the night before |
| R4 | **MinIO write fails** (bucket missing or auth) | Low | Medium — artifact not visible | Demo driver falls back to local filesystem path `demo/dio/out/`; show file via Explorer instead of MinIO console |
| R5 | **Langfuse traces don't appear** (OTel collector lag) | Low | Low — cosmetic, doesn't block gates | Skip the Langfuse tab; show OTel span JSON from `audit.db` instead |
| R6 | **UC 4.4 semantic check raises false `SemanticConflictError` on stub map** | Low | Medium — G4 fails | Stub map is pre-validated in prereq P9; on failure, demo driver overrides `asil_level="A"` to downgrade severity and notes the override aloud |

---

## 6. Runbook

Numbered exact-command sequence. Each step lists the expected output. The demo driver narrates each step before pressing Enter.

1. **Open terminal at repo root.**
   ```powershell
   Set-Location C:\AI_Agents\CIPHER_Local_repo\CIPHER
   ```
   Expected: prompt at repo root.

2. **Pre-flight banner (G0).**
   ```powershell
   python -m cipher.tools.demo_banner --gate G0 --ucs "1.1,3.1,4.4,4.1,1.4"
   ```
   Expected: ASCII banner `[G0] UC plan approved: 1.1, 3.1, 4.4, 4.1, 1.4`.

3. **Run pytest (G1).**
   ```powershell
   python -m pytest tests/ -v --tb=short
   ```
   Expected: green summary line `=== passed in <N>s ===`, exit 0.

4. **Invoke UC 1.1 — S1N1 LLD generation for Dio (G2).**
   ```powershell
   python -m cipher.agents.devnex.skills.vcycle_s1n1 --swc Dio --hld demo/dio/Dio_HLD_excerpt.md --asil B --out s3://cipher-artifacts/dio/
   ```
   Expected: `Wrote Dio_TEMP_LLD_updated.csv (rows=4)` and a MinIO object URI.

5. **Open the LLD CSV in the viewer.**
   ```powershell
   mc cat cipher/cipher-artifacts/dio/Dio_TEMP_LLD_updated.csv | Select-Object -First 6
   ```
   Expected: header row `REQ_ID,CATEGORY,DESCRIPTION` plus 4 data rows for the 4 APIs.

6. **Invoke UC 3.1 — ASIL gate evaluation (G3).**
   ```powershell
   python -m cipher.agents.devnex.tools.asil_review --input s3://cipher-artifacts/dio/Dio_TEMP_LLD_updated.csv --asil B --out demo/dio/asil/
   ```
   Expected: terminal prints `[ASIL-B] decision=HOLD` with rule hits enumerated; writes `asil_review_dio.json` + `.md`.

7. **Show the ASIL review markdown.**
   ```powershell
   code demo/dio/asil/asil_review_dio.md
   ```
   Expected: report opens in editor, sections "Triage", "Findings", "Decision" populated.

8. **Confirm audit trail (G3a).**
   ```powershell
   sqlite3 audit.db "SELECT count(*), max(timestamp) FROM audit_records;"
   ```
   Expected: count ≥ 2 (one for UC 1.1 LLM call, one for UC 3.1 gate decision), recent timestamp.

9. **Invoke UC 4.4 — post-merge semantic check (G4).**
   ```powershell
   python -c "from cipher.agents.devnex.adapter import run_uc4_4; run_uc4_4(map_file='build/dio_firmware.map', lds_file='src/dio_stub.ld', asil_level='B')"
   ```
   Expected: prints `overlap_report.json: 0 overlaps`; exit 0 (no `SemanticConflictError`).

10. **Generate Full Traceability Matrix (G4a).**
    ```powershell
    python -m cipher.agents.devnex.tools.full_trace --swc Dio --stage S9N1 --out demo/dio/trace/
    ```
    Expected: writes `Full_Traceability_Matrix.csv` per PROC-001 §4.2 canonical name; row count = 4.

11. **Open matrix in CSV viewer.**
    ```powershell
    Invoke-Item demo/dio/trace/Full_Traceability_Matrix.csv
    ```
    Expected: 4 rows, columns `HLD_ID, LLD_ID, CODE_FUNCTION, FILE, LINE` all populated.

12. **Audience Q&A — invoke UC 4.1 (G4b).** Take one audience question, e.g. "Where is `Dio_FlipChannel` traced?".
    ```powershell
    python -m cipher.agents.devnex.tools.qa --question "Where is Dio_FlipChannel traced?" --matrix demo/dio/trace/Full_Traceability_Matrix.csv
    ```
    Expected: `QAAnswer` printed with `answer:` text and `sources: [Full_Traceability_Matrix.csv:row=3]`.

13. **Closing banner.**
    ```powershell
    python -m cipher.tools.demo_banner --gate G4-complete --status PASS
    ```
    Expected: `[G4] Dio demo complete — HOLD archived, traceability green.`

> Note: Steps 4, 6, 9, 10, 12 reference module entry points by their logical position in `cipher/agents/devnex/`. If a given CLI entry point is not yet exposed at demo time, the demo driver falls back to a one-liner `python -c "from cipher... import ...; ..."` form. This substitution does not change the visible artifact.

---

## 7. Open Questions for QA-PROC

QA-PROC owns the following decisions and must close them before the demo is approved for live audience presentation. Each item is a binary or numeric threshold that affects pass/fail visibility.

- **Gate G3 HOLD threshold:** Is a single MISRA hit sufficient to mark G3 as `decision=HOLD`, or must at least two distinct rules fire for the demo to be considered representative of an ASIL-B failure mode?
- **Gate G4 traceability tolerance:** What fraction of empty `LINE` cells in `Full_Traceability_Matrix.csv` is acceptable when code-side stubs are used? (Suggested: 0% — any empty cell fails G4a.)
- **Artifact diff tolerance vs. golden:** When R2 fallback swaps in `demo/dio/golden/Full_Traceability_Matrix.csv`, is a column-order or whitespace diff against the live run acceptable, or must the golden be byte-identical to a fresh capture?
- **Audit journal sufficiency:** Is one `AuditRecord` per gate (G2, G3, G4) sufficient evidence, or must every internal LLM/GCA call within a gate produce its own signed record for the demo to count as compliant?
- **Mock GCA disclosure rule:** If R3 fallback activates and `MockGCABridge` is used, does the demo driver narrate the substitution aloud (transparency), or is a post-demo footnote in the run log acceptable?
- **Failure visibility policy:** If any of risks R1–R6 fire and a fallback is taken, must the original failure be shown to the audience first, or may the fallback be invoked silently to protect the live narrative?
- **G5 exemption confirmation:** PROC-001 §3 Phase 5 makes G5 mandatory only for ASIL-D. Confirm in writing that the ASIL-B Dio demo terminates cleanly at G4 with no G5 placeholder required in the run log.
- **Re-run policy:** If the demo is rerun mid-session (e.g. an audience requests a replay), must `audit.db` and MinIO bucket `cipher-artifacts/dio/` be wiped between runs, or is append-mode acceptable?

---

*CIPHER Tech Lead — WBS-0002 v1.0 — 2026-05-17*
