---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# WBS-0003: Full Demo Trial — 5-Component Vertical-Stack ASDLC Walkthrough

| Field | Value |
|-------|-------|
| Document ID | WBS-0003 |
| Version | 1.0 |
| ASPICE | MAN.3 — Project Management; SWE.1–SWE.6 — Software Engineering |
| ASIL Applicability | Mixed: Port / Dio / IoHwAb / LedActuator = ASIL-B; Det = QM (integrator-classifiable up to ASIL-D per CAR-006 §0) |
| Author | CIPHER Tech Lead |
| Date | 2026-05-17 |
| Status | DRAFT |
| Supersedes | WBS-0002 (partial). WBS-0002 remains valid for the Dio-only abbreviated demo path; this WBS-0003 expands the trial to a 5-component vertical stack. |
| Reference CARs | [CAR-004](../car/CAR-004-autosar-dio-sws.md) (Dio), [CAR-005](../car/CAR-005-autosar-port-sws.md) (Port), [CAR-006](../car/CAR-006-autosar-det-sws.md) (Det), [CAR-007](../car/CAR-007-autosar-iohwab-reference.md) (IoHwAb — synthesized), [CAR-008](../car/CAR-008-autosar-swc-template-reference.md) (LedActuator — vendor SWC via SWC Template) |
| Reference ADR | ADR-0003 POC Scope Lock |
| Governing process | PROC-001 (ASDLC v1.0) |
| Workspace | `generated_artifacts/dio_demo_workspace/` (shared with WBS-0002; now contains 5 component bundles) |
| Runbook | `docs/DEMO_RUNBOOK_DIO.md` §9 (Full Demo extension; appended, not replacing) |

---

## 1. Demo Goal

WBS-0002 demonstrates CIPHER ASDLC against a **single** ASIL-B driver (Dio). WBS-0003 expands that story to a **full ECU vertical stack**: an application SWC (LedActuator) calling an ECU-abstraction layer (IoHwAb), which calls an MCAL driver (Dio), which depends on an MCAL configurer (Port) and reports development errors through a BSW service (Det). The audience watches CIPHER process the **same** ASDLC phases (G0–G4) component-by-component and then sees a **cross-component traceability matrix** emerge that joins all five through symbol resolution against `firmware.map`.

The Full Demo's audience-meaningful "aha" beat is not any single component — it is the moment a reviewer clicks an LLD row in `LedActuator_TEMP_LLD.csv` and the trace walks **upward through IoHwAb, downward through Dio, sideways through Port and Det**, all without leaving the CIPHER GUI. That click closes the loop between an application-layer requirement and the underlying MCAL configuration, which is the actual integration story ISO 26262 Part 6 Clause 7 asks for.

WBS-0002 stays valid as the **abbreviated path** for shorter audiences (≤ 25 minutes) or for fallback when LLM throughput collapses (see §6 R-B).

---

## 2. Scope

### 2.1 In Scope — the 5 components

| # | Component | Layer | CAR | ASIL Claim | Demo APIs in scope | SWS status |
|---|-----------|-------|-----|-----------|--------------------|------------|
| 1 | **Det** | BSW Service | CAR-006 | QM (default); integrator-classifiable up to ASIL-D | `Det_Init`, `Det_ReportError`, `Det_GetVersionInfo` | Normative SWS (`CP_SWS_DefaultErrorTracer_017`, R24-11) |
| 2 | **Port** | MCAL Driver | CAR-005 | ASIL-B per `AUTOSAR_CP_SWS_PortDriver` | `Port_Init`, `Port_GetVersionInfo` (init-only path) | Normative SWS (`CP_SWS_PortDriver_040`, R24-11) |
| 3 | **Dio** | MCAL Driver | CAR-004 | ASIL-B per `AUTOSAR_CP_SWS_DIODriver` | `Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`, `Dio_GetVersionInfo` | Normative SWS (`CP_SWS_DIODriver_020`, R24-11) |
| 4 | **IoHwAb** | ECU Abstraction | CAR-007 | ASIL-B by inheritance from Dio | `IoHwAb_Init`, `IoHwAb_GetSignal_LedOut`, `IoHwAb_SetSignal_LedOut`, `IoHwAb_GetSignal_Switch` | **Synthesized / vendor-derived — NO single normative SWS exists.** PDF named `AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` self-describes as a guideline, not a standard. |
| 5 | **LedActuator** | Application SWC | CAR-008 | ASIL-B (claim attaches to the vendor SWC instance, not to the template) | `LedActuator_Init`, `LedActuator_MainFunction` | **Synthesized / vendor-derived — NO SWS exists for any application SWC.** Conforms to `AUTOSAR_CP_TPS_SoftwareComponentTemplate` (R24-11). |

### 2.2 New ASDLC Coverage vs WBS-0002

WBS-0002 §2.1 already covers UC 1.1 (S1N1 LLD generation), UC 3.1 (ASIL gate), UC 4.4 (post-merge semantic check), UC 4.1 (Q&A), and UC 1.4 / S9N1 (full traceability). WBS-0003 invokes **the same five UCs** five times — once per component — and adds one **cross-component join** at the end (S9N1 over the union of all five components' artifacts).

### 2.3 Out of Scope

- **RTE** — intentionally excluded per Tier 2 POC scope. LedActuator's R-Port calls into IoHwAb are demonstrated at the API-prototype level only; no `Rte_Call_*` indirection is shown.
- **Application-level SWCs other than LedActuator** — a single SWC instance is sufficient to demonstrate the "application sits above IoHwAb sits above Dio" stack story.
- **MCU driver init detail** — Port stops at `Port_Init`/`Port_GetVersionInfo`; MCU clock/PLL configuration is not in scope.
- **Multi-pin grouping** — `Dio_ReadPort`, `Dio_WritePort`, `Dio_ReadChannelGroup`, `Dio_WriteChannelGroup` remain deferred per WBS-0002 §2.2. Port pin grouping likewise out of scope.
- **Real hardware execution** — the workspace ships stub map and linker scripts (`firmware.map`, `stm32h7xx_flash.ld`); no physical ECU is involved at any phase.
- **DEM (Diagnostic Event Manager)** — Det handoff into DEM via `Det_ReportRuntimeError` not in scope; the demo restricts Det to `Det_ReportError`.
- **ARXML parsing** — LedActuator's R-Port declarations (`P_LedControl`, `P_LedHwAccess`) are described in `LedActuator_HLD.md` prose only; no ARXML round-trip is executed.

---

## 3. Per-Component Phase Storyboard

Each component is processed through the same compressed five-phase sequence. Sub-tables below mirror WBS-0002 §3 layout per component. The cells are deliberately short — the runbook (`docs/DEMO_RUNBOOK_DIO.md` §9.3) carries the click-by-click detail.

### 3.1 Det (QM — gate G3 expected PASS)

| ASDLC Phase | UC invoked | Input artifact | Output artifact | Pass gate |
|-------------|-----------|----------------|-----------------|-----------|
| G0 — UC plan ack | catalog | CAR-006, WBS-0003 | terminal banner | UC IDs printed |
| G2 — LLD Gen (S1N1) | UC 1.1 | `Det_HLD.md` | `Det_TEMP_LLD_updated.csv` (≥3 rows) | CSV schema ok |
| G3 — ASIL gate | UC 3.1 | `Det_TEMP_LLD_updated.csv`, ASIL=QM | `asil_review_det.json/.md` (decision: **PASS**) | PASS expected — QM claim |
| G4 — Semantic check | UC 4.4 | `firmware.map`, linker stub | `overlap_report.json` | 0 overlaps |
| G4a — Trace (S9N1) | UC 1.4 | Det LLD + map symbols | `Det_Traceability_Matrix.csv` | 0 orphans |

### 3.2 Port (ASIL-B — gate G3 expected HOLD)

| ASDLC Phase | UC invoked | Input artifact | Output artifact | Pass gate |
|-------------|-----------|----------------|-----------------|-----------|
| G0 — UC plan ack | catalog | CAR-005, WBS-0003 | terminal banner | UC IDs printed |
| G2 — LLD Gen (S1N1) | UC 1.1 | `Port_HLD.md` | `Port_TEMP_LLD_updated.csv` (≥2 rows: Port_Init + Port_GetVersionInfo) | CSV schema ok |
| G3 — ASIL gate | UC 3.1 | `Port_TEMP_LLD_updated.csv`, ASIL=B | `asil_review_port.json/.md` (decision: **HOLD**) | HOLD expected |
| G4 — Semantic check | UC 4.4 | `firmware.map`, linker stub | `overlap_report.json` | 0 overlaps |
| G4a — Trace (S9N1) | UC 1.4 | Port LLD + map symbols | `Port_Traceability_Matrix.csv` | 0 orphans |

### 3.3 Dio (ASIL-B — gate G3 expected HOLD; identical to WBS-0002)

| ASDLC Phase | UC invoked | Input artifact | Output artifact | Pass gate |
|-------------|-----------|----------------|-----------------|-----------|
| G0 — UC plan ack | catalog | CAR-004, WBS-0003 | terminal banner | UC IDs printed |
| G2 — LLD Gen (S1N1) | UC 1.1 | `Dio_HLD.md` | `Dio_TEMP_LLD_updated.csv` (≥4 rows) | CSV schema ok |
| G3 — ASIL gate | UC 3.1 | `Dio_TEMP_LLD_updated.csv`, ASIL=B | `asil_review_dio.json/.md` (decision: **HOLD**) | HOLD expected |
| G4 — Semantic check | UC 4.4 | `firmware.map`, linker stub | `overlap_report.json` | 0 overlaps |
| G4a — Trace (S9N1) | UC 1.4 | Dio LLD + map symbols | `Dio_Traceability_Matrix.csv` (== WBS-0002 deliverable) | 0 orphans |

### 3.4 IoHwAb (ASIL-B by inheritance — gate G3 expected HOLD)

| ASDLC Phase | UC invoked | Input artifact | Output artifact | Pass gate |
|-------------|-----------|----------------|-----------------|-----------|
| G0 — UC plan ack | catalog | CAR-007 (synthesized), WBS-0003 | terminal banner | UC IDs printed |
| G2 — LLD Gen (S1N1) | UC 1.1 | `IoHwAb_HLD.md` | `IoHwAb_TEMP_LLD_updated.csv` (≥4 rows) | CSV schema ok |
| G3 — ASIL gate | UC 3.1 | `IoHwAb_TEMP_LLD_updated.csv`, ASIL=B | `asil_review_iohwab.json/.md` (decision: **HOLD**) | HOLD expected |
| G4 — Semantic check | UC 4.4 | `firmware.map`, linker stub | `overlap_report.json` | 0 overlaps; symbol resolution into Dio.o pre-validated |
| G4a — Trace (S9N1) | UC 1.4 | IoHwAb LLD + map + downward link into Dio | `IoHwAb_Traceability_Matrix.csv` | 0 orphans; downward edge to HLD-DIO-NNN present |

### 3.5 LedActuator (ASIL-B — gate G3 expected HOLD)

| ASDLC Phase | UC invoked | Input artifact | Output artifact | Pass gate |
|-------------|-----------|----------------|-----------------|-----------|
| G0 — UC plan ack | catalog | CAR-008 (template-derived), WBS-0003 | terminal banner | UC IDs printed |
| G2 — LLD Gen (S1N1) | UC 1.1 | `LedActuator_HLD.md` | `LedActuator_TEMP_LLD_updated.csv` (≥2 rows: Init + MainFunction) | CSV schema ok |
| G3 — ASIL gate | UC 3.1 | `LedActuator_TEMP_LLD_updated.csv`, ASIL=B | `asil_review_ledactuator.json/.md` (decision: **HOLD**) | HOLD expected |
| G4 — Semantic check | UC 4.4 | `firmware.map`, linker stub | `overlap_report.json` | 0 overlaps; `LedActuator_MainFunction` symbol present |
| G4a — Trace (S9N1) | UC 1.4 | LedActuator LLD + map + downward chain into IoHwAb | `LedActuator_Traceability_Matrix.csv` | 0 orphans; downward edges to HLD-IOHWAB-NNN present |

### 3.6 Phase-storyboard notes (apply to all 5 sub-tables above)

- **G0 is presenter-narrated only.** The "UC plan ack" terminal banner from WBS-0002 §3 is replayed unchanged; the UC list (`1.1, 3.1, 4.4, 4.1, 1.4`) does not change between components.
- **G1 is run once, not five times.** `pytest tests/ -v` is a project-wide gate; the Full Demo does not re-run it per component. The preflight in `DEMO_RUNBOOK_DIO.md` §1 carries G1 for all five.
- **G3a (audit trail) is shared.** A single `audit.db` accumulates AuditRecords from all five components; the count grows monotonically from ~2 (Dio-only WBS-0002 baseline) to ≥10 (Full Demo). See §8.3 for the wipe policy.
- **G4b (audience Q&A via UC 4.1) fires once, at the end** — after the cross-component matrix in §4. Per-component Q&A is not exercised; the join is the natural place to take audience questions.
- **G5 (ASIL-D Safety Engineer sign-off) remains out of scope** for every component, including LedActuator (ASIL-B). WBS-0002 §3 footnote applies unchanged.

---

## 4. Cross-Component Traceability — the "Full Demo" join

The single new artifact WBS-0003 produces beyond WBS-0002 is the **`Full_Traceability_Matrix.csv`** generated by UC 1.4 / S9N1 over the union of all five components. CIPHER processes each component **independently** at G2/G3/G4 (the LLM never sees more than one component at a time); the matrix joins them at G4a by **symbol resolution against `firmware.map`**.

### 4.1 The trace chain WBS-0003 must demonstrate

```
HLD-LEDACT-004  (application: "drive LED to match switch level")
     |  resolves via prose dependency
     v
HLD-IOHWAB-003  (ecu abs: "IoHwAb_SetSignal_LedOut maps LedOut signal -> Dio channel")
     |  resolves via symbol IoHwAb_SetSignal_LedOut -> .text -> Dio_WriteChannel call site
     v
HLD-DIO-001     (mcal: "Dio_WriteChannel sets level on configured channel")
     |  resolves via Dio's HLD-DIO-009 "depends on Port for direction"
     +---> HLD-PORT-NNN  (mcal: "Port_Init configures pin direction")
     |  resolves via Dio's HLD-DIO-005 "reports DET via Det_ReportError"
     +---> HLD-DET-NNN   (bsw: "Det_ReportError records dev errors")
```

Five HLD-IDs joined by two upward edges (LedActuator → IoHwAb → Dio) and two sideways edges (Dio → Port, Dio → Det). The matrix renders this as one row per LLD line with **all five HLD-ID columns populated where applicable**.

### 4.2 How CIPHER produces the join

1. Each per-component S9N1 run writes its own `<Component>_Traceability_Matrix.csv` (per §3.x.G4a).
2. The merge step (S9N1 cross-component pass, UC 1.4 invocation N+1) reads all five CSVs plus `firmware.map`.
3. Symbol attribution (the `<source>.c.obj` column in the map — see Deliverable B) is used to identify which component owns each `.text` entry; cross-component call edges are inferred from prose references in the HLDs (`HLD-DIO-009`, `HLD-DIO-005`, `HLD-IOHWAB-003/004`, `HLD-LEDACT-003/004`).
4. The result is `Full_Traceability_Matrix.csv` with columns: `LLD_ID, OWNING_COMPONENT, HLD_LEDACT, HLD_IOHWAB, HLD_DIO, HLD_PORT, HLD_DET, CODE_FUNCTION, FILE, LINE`.

The matrix is **the** deliverable the audience clicks through in §9.4 of the runbook.

### 4.3 What a row looks like (illustrative)

| LLD_ID | OWNING_COMPONENT | HLD_LEDACT | HLD_IOHWAB | HLD_DIO | HLD_PORT | HLD_DET | CODE_FUNCTION | FILE | LINE |
|--------|------------------|-----------|-----------|---------|----------|---------|---------------|------|------|
| LLD-LEDACT-004 | LedActuator | HLD-LEDACT-004 | HLD-IOHWAB-003 | HLD-DIO-001 | HLD-PORT-001 | HLD-DET-002 | `LedActuator_MainFunction` | `LedActuator.c` | (per S9N1) |

### 4.4 Explicit edge inventory (for UC 1.4 implementation)

The cross-component join is driven by exactly six edge classes, all inferable from HLD prose:

| Edge | Source HLD-ID | Target HLD-ID | Inference rule | Symbol-resolution check |
|------|--------------|--------------|----------------|-------------------------|
| E1 | HLD-LEDACT-003 | HLD-IOHWAB-004 | LedActuator HLD §3 names `IoHwAb_GetSignal_Switch` as a downstream service | both symbols appear in `firmware.map` `.text`; attribution `LedActuator.c.obj` and `IoHwAb.c.obj` respectively |
| E2 | HLD-LEDACT-004 | HLD-IOHWAB-003 | LedActuator HLD §3 names `IoHwAb_SetSignal_LedOut` as a downstream service | as above |
| E3 | HLD-IOHWAB-003 | HLD-DIO-001 | IoHwAb HLD body cites `Dio_WriteChannel` as the underlying MCAL call | both `.text` entries present; IoHwAb_SetSignal_LedOut sits at a higher address than Dio_WriteChannel (downward call) |
| E4 | HLD-IOHWAB-004 | HLD-DIO-002 | IoHwAb HLD body cites `Dio_ReadChannel` as the underlying MCAL call | as above |
| E5 | HLD-DIO-009 | HLD-PORT-001 | Dio HLD §5.2 / HLD-DIO-009: "depends on Port for direction" | `Port_Init` appears in `.text` before any Dio symbol (init-order proxy) |
| E6 | HLD-DIO-005 | HLD-DET-002 | Dio HLD HLD-DIO-005: "report Development Errors to DET via `Det_ReportError(...)`" | `Det_ReportError` symbol present; Dio.c references it (LLD inspection) |

These six edges + 5 owning-component self-edges = the 11 join keys the merge step needs. UC 1.4 / S9N1 cross-component pass must implement these as static inferences; no LLM call is required at the join step.

### 4.5 Synthesized-component caveat propagation

Per CAR-007 §0 and CAR-008 §0, edges E1–E4 (those touching HLD-IOHWAB-* or HLD-LEDACT-*) carry a vendor-derived caveat. The `Full_Traceability_Matrix.csv` SHOULD render this via a `PROVENANCE` column (`SWS-NORMATIVE` for Det/Port/Dio rows; `VENDOR-DERIVED` for IoHwAb/LedActuator rows). See §8.4 for the open question on this column.

---

## 5. Risks & Fallbacks

| # | Risk | Likelihood | Impact | Fallback |
|---|------|------------|--------|----------|
| R-A | **Component-order dependency at demo time.** LedActuator HLD references `IoHwAb_SetSignal_LedOut`; IoHwAb HLD references Dio APIs; Dio HLD references `Dio_Cfg.h` and `Det_ReportError`. If the presenter imports LedActuator first, the LLD generator may flag undefined upstream symbols and produce orphan trace rows. | Medium | High — visible orphan rows undermine the audience aha moment | **Fixed import order: Det → Port → Dio → IoHwAb → LedActuator** (bottom-up). The runbook §9.3 enforces this. The Config panel's Import button is single-component, so the order is presenter-controlled. |
| R-B | **Cross-component LLM token budget.** Five S1N1 prompts back-to-back (~12k–18k tokens each) can exhaust GCA retries or rate limits, killing G2 mid-component-3 or mid-component-4. | Medium | Critical — partial demo state is worse than no demo | **Two-batch presentation with audience Q&A break.** Batch A: Det + Port + Dio (the normative-SWS components). Pause for 5 minutes of Q&A. Batch B: IoHwAb + LedActuator (the synthesized components). Total LLM pressure halved. If still failing, drop to WBS-0002 abbreviated path. |
| R-C | **firmware.map symbol collisions.** Five components writing into the same `.text`/`.bss` sections in one synthetic map could produce overlapping addresses or duplicate symbol names, causing UC 4.4 to raise `SemanticConflictError`. | Low | Medium — G4 fails visibly for one or more components | **Per-component prefix namespacing in the map.** Each function symbol is prefixed by its module short name (`Port_*`, `Det_*`, `Dio_*`, `IoHwAb_*`, `LedActuator_*`). The map's symbol-attribution column further binds each line to its `<source>.c.obj` so the overlap check can disambiguate. See Deliverable B (`firmware.map`). |
| R-D | **"Where's the SWS?" reviewer question on synthesized HLDs.** IoHwAb_HLD and LedActuator_HLD have no normative SWS (CAR-007 §0 and CAR-008 §0 explicitly warn this). A reviewer who has read CAR-004 may push back when CIPHER cites CAR-007/CAR-008 with the same gravitas. | High | Medium — credibility hit if the presenter is unprepared | **Pre-empt in runbook §9.5.** The presenter has a scripted 3-sentence reply that surfaces the CAR-007/CAR-008 caveats explicitly and frames them as "vendor-derived, structurally anchored, traceable to AUTOSAR template documents". |
| R-E | **Det QM-vs-ASIL-B cross-ASIL caller awkwardness.** Det_HLD claims QM but Dio_HLD HLD-DIO-005 has Dio (ASIL-B) calling `Det_ReportError`. A safety reviewer may flag this as a freedom-from-interference violation. | Medium | Medium — derails the FFI narrative | **Use Det_HLD §6's pre-written FFI argument** (Det_Buffer is a pure write-only sink; corruption cannot propagate back into Dio's control flow). Cross-link from runbook §9.4 immediately after the cross-component trace beat. |
| R-F | **Inherited from WBS-0002 R1–R6.** ASIL gate false-PASS, traceability orphan rows, GCA retry exhaustion, MinIO outage, Langfuse lag, false `SemanticConflictError`. | Various | Various | Same fallbacks as WBS-0002 §5; the abbreviated path (WBS-0002) is itself the ultimate fallback for WBS-0003. |

---

## 6. Demo Prerequisites

Extends WBS-0002 §4. All P1–P11 from WBS-0002 still apply. Additional prereqs:

| # | Prereq | Verification command | Pass condition |
|---|--------|---------------------|----------------|
| P12 | All 5 component HLDs present | `Test-Path generated_artifacts/dio_demo_workspace/{Det,Port,Dio,IoHwAb,LedActuator}_HLD.md` | All `True` |
| P13 | All 5 cipher_config JSONs present | `Test-Path generated_artifacts/dio_demo_workspace/cipher_config_{det,port,dio,iohwab,ledactuator}.json` | All `True` |
| P14 | All 5 source bundles present | `Test-Path generated_artifacts/dio_demo_workspace/{Det,Port,Dio,IoHwAb,LedActuator}.{c,h}` plus `Dio_Cfg.h` | All `True` |
| P15 | All 5 TEMP_LLD seed files present | `Test-Path generated_artifacts/dio_demo_workspace/{Det,Port,Dio,IoHwAb,LedActuator}_TEMP_LLD.csv` | All `True` |
| P16 | Regenerated `firmware.map` covers all 5 components | `Select-String -Path firmware.map -Pattern 'LedActuator_MainFunction','IoHwAb_Init','Port_Init','Det_Init','Dio_WriteChannel'` | 5 matches |
| P17 | Runbook §9 has been read by presenter | manual ack | yes |

If P12–P16 fail, the demo falls back to WBS-0002 abbreviated path (Dio-only) and the presenter narrates the downgrade aloud per the transparency policy (WBS-0002 §7).

---

## 7. Runbook Pointer

See `docs/DEMO_RUNBOOK_DIO.md` **§9** for the click-by-click multi-component walkthrough. §9 is appended to DEMO_RUNBOOK_DIO (not a separate runbook) so the presenter has a single document on screen during the demo. The earlier sections (§1–§8) remain the canonical Dio-only script and are reused verbatim for steps that do not change between WBS-0002 and WBS-0003 (launch sequence, preflight base checks, post-demo capture).

---

## 8. Open Questions for QA-PROC

The following are WBS-0003-specific questions. WBS-0002 §7 open questions remain open and still bind.

### 8.1 Component presentation order

**Question.** Bottom-up (Det → Port → Dio → IoHwAb → LedActuator) vs top-down (LedActuator → IoHwAb → Dio → Port → Det)?

**Recommendation: bottom-up.** Three reasons. (a) Risk R-A — LedActuator and IoHwAb reference upstream symbols; importing them before their upstreams produces visible orphan rows in the per-component matrices. (b) Audience cognitive load — Det and Port have small API surfaces and clean SWS provenance; starting there warms the audience up before the harder ASIL-B/synthesized story arrives. (c) Narrative payoff — finishing with LedActuator means the final per-component G4a matrix already contains the downward chain into IoHwAb→Dio→Port/Det, which is the natural lead-in to the cross-component join in §9.4 of the runbook.

### 8.2 Per-component-end-to-end vs all-G1-then-all-G2-etc

**Question.** Process one component fully through G0→G4a before moving to the next, or batch-process all 5 through G1, then all 5 through G2, etc?

**Recommendation: per-component end-to-end.** Two reasons. (a) ASDLC story coherence — the audience sees a complete vertical slice land before the next one starts, reinforcing the "one component, one pipeline" mental model. Batch-by-phase forces five context switches per gate (5×5 = 25 transitions vs 5). (b) The G3 narrative depends on the audience holding "Det PASSes because QM, the other four HOLD because ASIL-B" in mind — that contrast lands harder when the gates fire in immediate succession per component than when spread across five batched G3 runs.

### 8.3 DEMO_RUNBOOK §6 audit.db note — still applies?

**Question.** WBS-0002's runbook §6 includes a presenter note that `audit.db` may be manually wiped before a clean live run. With 5 components and ~5× the audit records, does this still apply?

**Recommendation: yes, still applies — with one addition.** The Full Demo produces roughly 5× the audit volume (≥ 10 signed AuditRecords at minimum: 1 LLM call + 1 ASIL decision per component × 5). The presenter judgment call to wipe `audit.db` is unchanged. **Addition:** if the wipe is taken, the presenter should also clear any per-component `asil_review_*.json/.md` files in the workspace from prior dry-runs, to avoid Step 8 of §3 surfacing a stale ASIL decision. The decision remains a manual judgment call — not enforced by preflight, not required by WBS-0003.

### 8.4 Synthesized-HLD audit posture

**Question.** When `Full_Traceability_Matrix.csv` is captured post-demo, do the IoHwAb and LedActuator rows need a "VENDOR-DERIVED" column flag, or is the CAR-007 / CAR-008 caveat in the HLD frontmatter sufficient?

**Recommendation: add an explicit column.** A reviewer reading the matrix in isolation (without the HLDs open) cannot tell normative-SWS rows from vendor-derived rows. A single `PROVENANCE` column with values `SWS-NORMATIVE` (Det/Port/Dio) and `VENDOR-DERIVED` (IoHwAb/LedActuator) makes the caveat travel with the artifact. Tech Lead owns the schema bump; QA-PROC owns approval.

### 8.5 Det QM caller-isolation evidence

**Question.** Does the FFI argument in `Det_HLD.md` §6 (the "pure write-only sink" rationale) need to be re-stated in the WBS-0003 demo narrative, or is it sufficient to cite Det_HLD §6 by reference when a reviewer asks?

**Recommendation: cite by reference only.** Reading Det_HLD §6 aloud during the demo costs ~90 seconds and breaks pacing. The presenter has the section bookmarked and opens it only if a reviewer pushes (see runbook §9.5 fallback script).

---

*CIPHER Tech Lead — WBS-0003 v1.0 — 2026-05-17*
*WBS-0002 (Dio-only abbreviated demo) remains valid and is the canonical fallback path for WBS-0003.*
