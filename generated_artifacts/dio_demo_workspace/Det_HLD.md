# Det (Default Error Tracer) — High-Level Design (HLD)

| Field | Value |
|---|---|
| Document Title | Det (Default Error Tracer) — High-Level Design |
| Document ID | HLD-DET-001 |
| Version | 1.0 |
| Status | DRAFT |
| Date | 2026-05-17 |
| Author | CIPHER HLD Author (AI-assisted) |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Safety Claim | QM-default, integrator may classify higher per CAR-006 §0 (up to ASIL D when DET is reused as a safety mechanism via runtime-error routing — quote the SWS rather than assume). |
| Source Specification | CAR-006 — AUTOSAR Classic Platform R24-11, `CP_SWS_DefaultErrorTracer_017` |
| Module Short Name | Det |
| Module Long Name | **Default Error Tracer** (historically "Development Error Tracer"; renamed in recent AUTOSAR releases — short name `Det` unchanged). |
| Notice | DEMO HLD - NOT FOR PRODUCTION USE. Generated for the CIPHER ASDLC demo trial (3-API slice). Companion HLD to HLD-DIO-001. |

---

## 1. Scope & Module Purpose

The Det (Default Error Tracer) module is the AUTOSAR Classic Platform's centralised sink for development errors, runtime errors, and transient faults reported by every other BSW module. Every BSW module that enables `<Module>DevErrorDetect` (Dio enables `DioDevErrorDetect` per CAR-004 §3) calls into `Det_ReportError` with a four-parameter `(ModuleId, InstanceId, ApiId, ErrorId)` tuple that uniquely identifies the offending call site (CAR-006 §3).

**What Det does** (per CAR-006 §1 / SWS §8):
- Initialises an internal report sink at boot.
- Records a development-error tuple raised by an upstream BSW module.
- Reports its own module identification through `Std_VersionInfoType`.

**What Det does NOT do**:
- It does not perform DEM (Diagnostic Event Manager) hand-off in the demo. Real integrations may route `Det_ReportRuntimeError` into DEM — that path is out of demo scope.
- It does not generate user-visible diagnostic messages. The error sink is integrator-supplied (`DetErrorHook`, SWS §10.2.3) and is stubbed to a ring buffer in the demo.
- It does **not** call `Det_ReportError` on itself for any internal failure (self-reporting is forbidden by the SWS — see §6 and HLD-DET-006).

**Demo scope (this HLD)** — per CAR-006 §4 the three exposed APIs are:

| Demo API | SWS Section | Service ID |
|---|---|---|
| `Det_Init` | 8.1.3.1 | 0x00 |
| `Det_ReportError` | 8.1.3.2 | 0x01 |
| `Det_GetVersionInfo` | 8.1.3.6 | 0x05 |

**Declared for SWS completeness, not exercised by the demo runtime path**: `Det_Start` (8.1.3.3), `Det_ReportRuntimeError` (8.1.3.4), `Det_ReportTransientFault` (8.1.3.5). Their prototypes appear in `Det.h` so the API coverage table is complete, but the implementations are intentionally absent from `Det.c` per CAR-006 §4.

---

## 2. Dependencies

Det sits at the **bottom of the BSW stack**. By construction it has no compile-time or run-time dependency on any other BSW module — every other module depends on Det, never the other way around.

| Dependency | Direction | Purpose | SWS / CAR-006 Reference |
|---|---|---|---|
| **`Std_Types.h`** (MCAL framework) | Header dependency | Provides `Std_ReturnType`, `Std_VersionInfoType`, `E_OK` used in Det's public signatures. For the demo, the header is stubbed inline in `Det.h` behind `#ifndef STD_TYPES_INCLUDED` (same pattern as `Dio.h`). | CAR-006 §1; SWS §8 |
| (no upstream BSW module) | — | DET is the root of the error-report dependency graph — no other BSW module's API is invoked from `Det.c`. | CAR-006 §1 |

The Det module does not depend on EcuM (`Det_Init` is invoked directly by the integrator's startup code, not by EcuM), on the scheduler, on COM, or on the NVRAM Manager. The optional `DetNotification` callouts (SWS §10.2.3) are integrator-supplied hooks DET invokes **outbound** and are not modelled as upstream dependencies.

---

## 3. Configuration Model

Configuration is structured per CAR-006 §2 / SWS §10.2 as a shallow three-container tree:

- **`Det`** (CAR-006 §2; SWS 10.2.1) — Root container; references exactly one `DetGeneral` and one `DetConfigSet`.
- **`DetGeneral`** (CAR-006 §2; SWS 10.2.2) — Module-wide switches:
  - Enables `Det_GetVersionInfo`.
  - Enables `Det_ReportRuntimeError`, `Det_ReportTransientFault` (out of demo runtime scope).
  - Controls the report-buffer behaviour (the demo hard-codes a 16-deep ring buffer; see §7).
- **`DetConfigSet`** (CAR-006 §2; SWS 10.2.4) — Aggregates per-module error-handling parameters (`DetModule`, `DetModuleInstance`) so DET can filter and route reports by `ModuleId`. The demo collapses this to "accept everything" — no per-module filtering.

Adjacent containers `DetNotification` (10.2.3), `DetModule` (10.2.5), `DetModuleInstance` (10.2.6) are noted for completeness per CAR-006 §2 but are out of demo scope.

**Variant marker.** The demo treats configuration as `VARIANT-PRE-COMPILE`: the `Det_ConfigType` passed to `Det_Init` carries a single `ConfigVariant` field (set to 0u in the demo), and `Det_Init` accepts `NULL` because all real settings are compile-time constants.

---

## 4. API Contracts

Each subsection below is one demo API. Signatures match `Det.h` exactly.

### 4.1 Det_Init (SWS 8.1.3.1)

**Synopsis.** Initialises DET internal state; must be called before any `Det_Report*` API.

**Signature.**
```c
void Det_Init(const Det_ConfigType * ConfigPtr);
```

**Pre-conditions.** None. May be invoked at any reset state.

**Post-conditions.**
- The internal ring buffer (`Det_Buffer[16]`) is zero-cleared.
- `Det_BufferIdx`, `Det_TotalCount` are reset to 0.
- `Det_Initialized` is set; subsequent `Det_ReportError` calls now record into the buffer.
- A `NULL` `ConfigPtr` is accepted in the demo (real SWS allows NULL when the PRE-COMPILE variant is used — see §3).

**DET errors.** None. DET cannot DET-report itself (see §6).

**Re-entrancy.** Not re-entrant. The integrator calls `Det_Init` exactly once from startup before any BSW module reports.

**SWS section.** 8.1.3.1 (CAR-006 §1).

---

### 4.2 Det_ReportError (SWS 8.1.3.2)

**Synopsis.** Records a development-error tuple from an upstream BSW module. The single API Dio calls.

**Signature.**
```c
Std_ReturnType Det_ReportError(uint16 ModuleId,
                               uint8  InstanceId,
                               uint8  ApiId,
                               uint8  ErrorId);
```

**Pre-conditions.**
- `Det_Init` has been called (if not, the call is a silent no-op — see HLD-DET-005).
- The tuple is fully populated per CAR-006 §3.

**Post-conditions.**
- On `Det_Initialized == 1`: a new `Det_ErrorRecord_t` is written at `Det_Buffer[Det_BufferIdx]`; `Det_BufferIdx` advances modulo 16; `Det_TotalCount` increments. The oldest record is overwritten when the buffer wraps (see HLD-DET-003).
- On `Det_Initialized == 0`: no state change.
- Always returns `E_OK` per SWS §8.1.3.2 return contract.

**DET errors.** None. DET does not validate the tuple — it records whatever the caller supplied.

**Re-entrancy.** SWS §8 declares all Det APIs re-entrant. The demo implementation is not interrupt-safe (the ring-buffer write is not atomic), which is acceptable for the demo's single-threaded test harness; a production integration would protect the buffer with an `EnterCriticalSection` macro from the OS abstraction layer.

**SWS section.** 8.1.3.2 (CAR-006 §1).

---

### 4.3 Det_GetVersionInfo (SWS 8.1.3.6)

**Synopsis.** Fills a caller-supplied `Std_VersionInfoType` structure with the Det module's vendor ID, module ID, and software version triplet.

**Signature.**
```c
void Det_GetVersionInfo(Std_VersionInfoType * versioninfo);
```

**Pre-conditions.** `versioninfo` is a non-NULL pointer to a writable `Std_VersionInfoType`.

**Post-conditions.**
- On non-NULL: `vendorID = 0x002B`, `moduleID = 15`, `sw_major/minor/patch = 4/8/0`.
- On NULL: **silent no-op** — DET cannot DET-report on itself per SWS (see §6).

**DET errors.** None — DET cannot DET-report itself.

**Re-entrancy.** Fully re-entrant when distinct `versioninfo` buffers are passed.

**SWS section.** 8.1.3.6 (CAR-006 §1).

---

## 5. Error Semantics

### 5.1 The (ModuleId, InstanceId, ApiId, ErrorId) tuple (CAR-006 §3)

Every `Det_Report*` API takes the same four-parameter tuple. The tuple is the **payload**, not a return value — DET itself does not classify or validate it; it records it for an integrator-supplied hook to consume.

| Parameter | Type | Origin | Meaning |
|---|---|---|---|
| `ModuleId` | `uint16` | Caller's published BSW module ID. | Identifies which BSW module raised the error. |
| `InstanceId` | `uint8` | Caller's per-instance index. | Disambiguates multiple instances of the same module. |
| `ApiId` | `uint8` | Caller's per-API service ID. | Identifies which function inside the module was executing. |
| `ErrorId` | `uint8` | Caller's DET error code. | Categorises the error type. |

### 5.2 How Dio populates the tuple (worked example)

Per the Dio SWS section 7.6.1 and CAR-006 §3, every Dio parameter-validation branch reports with:

| Tuple field | Value Dio supplies | Source |
|---|---|---|
| `ModuleId` | `DIO_MODULE_ID` = **120** | AUTOSAR module-ID list. |
| `InstanceId` | **0** | Dio has exactly one instance. |
| `ApiId` | per-API constant: `DIO_SID_READ_CHANNEL` (0x00), `_WRITE_CHANNEL` (0x01), `_FLIP_CHANNEL` (0x11), `_GET_VERSION_INFO` (0x12). | Dio SWS §8.2; `Dio.h`. |
| `ErrorId` | `DIO_E_PARAM_INVALID_CHANNEL_ID` (0x0A) or `DIO_E_PARAM_POINTER` (0x20). | CAR-004 §3 / Dio.h. |

The tuple identifies the offending call site precisely enough that one DET log line maps back to one line of Dio source code.

### 5.3 Error classification taxonomy (SWS §7.5)

- **7.5.1 Development Errors** — `Det_ReportError`. Path Dio uses.
- **7.5.2 Runtime Errors** — `Det_ReportRuntimeError`. Out of demo scope (prototype only).
- **7.5.3 Production Errors** — handed off to DEM. Not implemented in DET.
- **7.5.4 Extended Production Errors** — OEM-specific. Not implemented.

### 5.4 Caveat — numeric DET-internal constants unverified

CAR-006 §5 records that the PDF binary body was not parsed; numeric values of any DET-side status / API-ID constants are not quoted in the CAR. The demo therefore picks plausible values (`DET_SID_*` 0x00–0x05) without claiming SWS-verified numeric equivalence. Tracked as an Open Issue in §9.

---

## 6. ASIL Claim & FFI Rationale

**Claim.** Per CAR-006 §0: **QM by default, integrator-classified up to ASIL D** when DET is reused as a safety mechanism (e.g. when `Det_ReportRuntimeError` is routed into a safety reaction). The demo HLD claims **QM** for all three demo APIs because the demo does not route DET output into any safety reaction. The frontmatter records both positions explicitly so the integrator can lift the claim without contradiction.

**The "DET cannot DET-report itself" gotcha (real safety design point).** A naïve DET implementation that validated its own parameters via `Det_ReportError` would create an unbounded recursion: `Det_ReportError` calls itself on a bad parameter, which is also a bad parameter, etc. The SWS resolves this by mandating that DET handle its own internal failures via a **silent return or an integrator-supplied last-resort hook**, never via the public DET reporting path. The demo enforces this in two places:
1. `Det_GetVersionInfo(NULL)` → silent no-op (no `Det_ReportError` call, no abort).
2. `Det_ReportError` invoked before `Det_Init` → silent no-op.

This is **HLD-DET-006** in the requirements table and is the single most important safety-design property of the module.

**Freedom From Interference (FFI) considerations.**
- **Spatial FFI.** The only writable state is `Det_Buffer[]`, `Det_BufferIdx`, `Det_TotalCount`, `Det_Initialized` — all file-static and accessed only from within `Det.c`. No upstream module can write the buffer directly.
- **Temporal FFI.** No Det API blocks, sleeps, or yields. `Det_ReportError` is constant-time: one struct write, one modulo, one increment.
- **Information / Control-flow FFI.** No callbacks registered in the demo. The `DetNotification` hook surface is wired off.
- **Cross-ASIL caller robustness.** Because DET is QM and may be called from ASIL-B callers (Dio), a freedom-from-interference argument is required: the demo's argument is that DET state is a pure write-only sink from the caller's perspective — corruption of `Det_Buffer` cannot propagate back into the caller's control flow.

---

## 7. Memory & Sectioning

The demo Det module produces the following memory artefacts:

| Symbol | Storage Class | Linker Section (expected) | Notes |
|---|---|---|---|
| `Det_Init`, `Det_ReportError`, `Det_GetVersionInfo` | code | `.text` | Public demo APIs; placed in flash. |
| `Det_Buffer[16]` | data (static, zero-init) | **`.bss`** | 16 × `Det_ErrorRecord_t` ≈ 144 bytes. Zero-init is the natural "no records yet" sentinel, so it lives in `.bss` rather than `.data`. |
| `Det_BufferIdx`, `Det_TotalCount`, `Det_Initialized` | data (static, zero-init) | `.bss` | Scalar state. |
| `Det_ConfigType` instance(s) | rodata | **`.rodata`** | In a real integration the PRE-COMPILE `Det_ConfigType` table generated from `Det/DetGeneral/DetConfigSet` lives in `.rodata`. The demo passes NULL into `Det_Init` and has no `.rodata` config table. |
| Vendor / module / version macros | n/a (preprocessor) | n/a | Inlined at every call site of `Det_GetVersionInfo`. |

The demo Det module contributes ~150 bytes to RAM (all `.bss`) and ~0.4 KB to flash. UC 4.4 overlap-check expectation: trivially passes — no `_SAFE` / `_NVM` overlap.

---

## 8. HLD Requirement Table

Trace targets for the downstream S1N1 LLD generator. Every LLD-DET row must cite at least one of these IDs in its `HLD_PARENT` column.

| HLD_ID | Description | ASIL | Parent System Req | Verification Method | CAR-006 Section / SWS Ref |
|---|---|---|---|---|---|
| HLD-DET-001 | The Det module shall initialise its internal report sink via `Det_Init(const Det_ConfigType*)`, clearing the ring buffer and accepting a NULL ConfigPtr for the PRE-COMPILE variant. | QM | SYS-DET-100 | Test | CAR-006 §1, §4 (SWS §8.1.3.1) |
| HLD-DET-002 | The Det module shall record the `(ModuleId, InstanceId, ApiId, ErrorId)` tuple from `Det_ReportError` into a 16-deep static ring buffer and return `E_OK`. | QM | SYS-DET-101 | Test | CAR-006 §1, §3 (SWS §8.1.3.2) |
| HLD-DET-003 | When the ring buffer is full, `Det_ReportError` shall overwrite the oldest record (FIFO wrap) and continue to return `E_OK`; the monotonic `Det_TotalCount` shall record the true number of reports received. | QM | SYS-DET-102 | Test | CAR-006 §3 (buffer semantics) |
| HLD-DET-004 | `Det_GetVersionInfo` shall publish the version triplet (`DET_VENDOR_ID = 0x002B`, `DET_MODULE_ID = 15`, `4.8.0`) when called with a non-NULL `Std_VersionInfoType*`. | QM | SYS-DET-103 | Test | CAR-006 §1 (SWS §8.1.3.6) |
| HLD-DET-005 | `Det_ReportError` invoked before `Det_Init` shall be a silent no-op (no buffer write, no crash) and shall still return `E_OK`. | QM | SYS-DET-104 | Test | CAR-006 §1 (SWS §8.1.3.1 init-order) |
| HLD-DET-006 | The Det module shall not invoke `Det_ReportError`, `Det_ReportRuntimeError`, or `Det_ReportTransientFault` on any of its own internal failures (e.g. NULL pointer to `Det_GetVersionInfo`); self-reporting is forbidden by the SWS. | QM | SYS-DET-105 | Review | CAR-006 §0, §1 (DET cannot DET-report itself) |
| HLD-DET-007 | The Det module shall declare prototypes for `Det_Start`, `Det_ReportRuntimeError`, and `Det_ReportTransientFault` in `Det.h` for SWS API-surface completeness, but these APIs are NOT exercised by the demo runtime path. | QM | SYS-DET-106 | Inspection | CAR-006 §4 (demo scope hint) |
| HLD-DET-008 | The Det configuration model shall be the three-container tree `Det / DetGeneral / DetConfigSet` defined by CAR-006 §2; the demo treats the model as `VARIANT-PRE-COMPILE` and collapses per-module filtering to "accept everything". | QM | SYS-DET-107 | Review | CAR-006 §2 (SWS §10.2.1 / 10.2.2 / 10.2.4) |

---

## 9. Open Issues / Demo Limitations

The following items are inherited verbatim from CAR-006 §5 ("Unverified / flagged items" and "Limitation flag") and remain open against this HLD:

- **ASIL classification sentence unverified.** CAR-006 §5 records that the explicit ASIL classification sentence in the SWS body was reported as "Not specified in provided content"; the CIPHER team MUST confirm by reading SWS §4 / §7 of the downloaded PDF before this HLD is frozen. The §6 claim records the conservative integrator-classified position.
- **Numeric DET-internal constants unverified.** CAR-006 §5 records that the PDF binary was not parsed inside the source agent and no numeric values of DET-side status / API-ID constants are quoted. The `DET_SID_*` values 0x00–0x05 in `Det.h` are plausible but not SWS-verified.
- **`Det_Start` requiredness unverified.** CAR-006 §5 records that whether `Det_Start` is required or optional in R24-11 is unclear; the demo treats `Det_Init` alone as sufficient (per CAR-006 §4 "demo treats DET as operational immediately after `Det_Init`"). Cross-check before code generation freeze.
- **PDF body-text limitation flag.** CAR-006 §5 records that the PDF binary body text was not parsed; metadata was extracted via a single high-level WebFetch read. Any downstream artifact needing exact numeric constants or the verbatim ASIL classification paragraph MUST trigger a manual PDF review.
- **DEM hand-off not modelled.** `Det_ReportRuntimeError` is a prototype only; no DEM (Diagnostic Event Manager) routing is implemented. Real production integrations must add this path.
- **Ring buffer not interrupt-safe.** The demo `Det_ReportError` ring-buffer write is not atomic against an ISR-context caller. Acceptable for the single-threaded demo harness; a production integration must add a critical-section wrapper.

---

## 10. Traceability Notes

Downstream traceability is realised by the S1N1 LLD generator (same path as for Dio: `cipher/agents/devnex_assistant/prompts/lld_gen_v1.md`), which consumes `Det.c` / `Det.h` plus this HLD and emits `Det_TEMP_LLD_updated.csv`. Every LLD row produced by S1N1 is required to populate the `HLD_PARENT` column with one of the `HLD-DET-NNN` IDs from §8 above (with `REVIEW_NEEDED` as the recorded fallback when no match exists).

The expected coarse mapping (informative — S1N1 produces the binding mapping):

| Source element (in `Det.c` / `Det.h`) | Likely HLD parent |
|---|---|
| `void Det_Init(const Det_ConfigType * ConfigPtr)` | HLD-DET-001, HLD-DET-008 |
| `Std_ReturnType Det_ReportError(...)` | HLD-DET-002, HLD-DET-003, HLD-DET-005 |
| `void Det_GetVersionInfo(...)` | HLD-DET-004, HLD-DET-006 |
| `static Det_ErrorRecord_t Det_Buffer[16]` | HLD-DET-002, HLD-DET-003 |
| `static uint8 Det_BufferIdx / Det_TotalCount / Det_Initialized` | HLD-DET-002, HLD-DET-003, HLD-DET-005 |
| `Det_Start`, `Det_ReportRuntimeError`, `Det_ReportTransientFault` prototypes | HLD-DET-007 |
| `Det_ConfigType` typedef | HLD-DET-001, HLD-DET-008 |
| `Det_ErrorRecord_t` typedef | HLD-DET-002 |
| `DET_VENDOR_ID` / `DET_MODULE_ID` / `DET_SW_*_VERSION` | HLD-DET-004 |

Upstream traceability is provided in §8 by the `SYS-DET-1NN` Parent System Req column. These IDs are demo-synthetic and are recorded so that any future linkage to a real SYS-level requirements baseline preserves the row identity.

Companion HLD: HLD-DIO-001. The Dio HLD §5 DET-reporting path terminates at `Det_ReportError` documented in HLD-DET-002 of this document; the (ModuleId=120, InstanceId=0, ApiId=DIO_SID_*, ErrorId=DIO_E_*) tuple shape is the cross-document contract that locks the two HLDs together.

---

End of HLD.
