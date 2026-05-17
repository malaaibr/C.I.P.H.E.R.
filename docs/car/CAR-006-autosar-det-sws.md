# CAR-006: AUTOSAR Classic Platform — Default/Development Error Tracer (DET) SWS (Demo Source Spec)

- **Status:** Accepted
- **Source type:** External standard (AUTOSAR Classic Platform)
- **Fetched:** 2026-05-17
- **Reference tier:** PRIMARY (demo source-of-truth)
- **Role for CIPHER:** Companion CAR to CAR-004 (Dio). Pins the public DET API surface that Dio (and every other BSW module) calls into when `DevErrorDetect` is enabled, so the CIPHER ASDLC demo can wire DET reporting through HLD -> LLD -> Code -> Tests -> ASIL gate -> traceability.

---

## 0. Document Frontmatter

| Field | Value |
|---|---|
| Document Title | Specification of Default Error Tracer (historically: Specification of Development Error Tracer) |
| Document ID | CP_SWS_DefaultErrorTracer_017 |
| AUTOSAR Release | R24-11 (Classic Platform) |
| SWS Document Version | AUTOSAR CP R24-11 (latest as of 2026-05-17) |
| Module Short Name | Det |
| ASIL Claim | Configuration-dependent. The DET module itself is typically integrated as QM (it is a development-and-diagnostic aid, not a runtime safety mechanism). When DET is reused as a safety mechanism (e.g. routing `Det_ReportRuntimeError` into a safety reaction), the integrator MUST classify it per the SWS section 4 ("General requirements") and section 7.5 ("Error classification"). The demo records this as "QM by default; integrator-classified up to ASIL D when used as a safety mechanism — quote the SWS rather than assume". |
| Source URL | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DefaultErrorTracer.pdf |
| Historical filename | `AUTOSAR_SWS_DET.pdf` (pre-R20) and `AUTOSAR_CP_SWS_DevelopmentErrorTracer.pdf` (mid-cycle); R24-11 publishes the document as `AUTOSAR_CP_SWS_DefaultErrorTracer.pdf`. The short name `Det` is unchanged across all releases. |
| Fallback URL (R23-11) | https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_DefaultErrorTracer.pdf |
| Fetched date | 2026-05-17 |
| Anti-conflation note | This CAR records ONLY the public Det API surface and the configuration containers needed to scope the demo. It does NOT describe an internal CIPHER codebase, and it does NOT specify the DEM (Diagnostic Event Manager) — DEM is a separate AUTOSAR module that DET hands off to via `Det_ReportRuntimeError` in some integrations. |

---

## 1. Public API

All Det APIs are synchronous and re-entrant per AUTOSAR SWS section 8 ("API specification"). The Det module exposes no callback notifications to the caller; the `DetNotification` callouts in section 10.2.3 are integrator-supplied hooks DET invokes outbound.

| API | Sync/Async | Return type | Side effect | Section in SWS |
|---|---|---|---|---|
| `Det_Init` | Sync | `void` | Initialises DET internal state from a `Det_ConfigType*`. Must be called before any `Det_Report*` API. | 8.1.3.1 |
| `Det_Start` | Sync | `void` | Transitions DET from "initialised" to "operational"; report APIs may be active before this depending on configuration. | 8.1.3.3 |
| `Det_ReportError` | Sync | `Std_ReturnType` | **The API Dio calls.** Records a development error tuple `(ModuleId, InstanceId, ApiId, ErrorId)` and invokes the configured `DetErrorHook` callouts. | 8.1.3.2 |
| `Det_ReportRuntimeError` | Sync | `Std_ReturnType` | Records a runtime error tuple (same shape as above) and invokes the configured runtime-error callouts; may be routed to DEM by the integrator. | 8.1.3.4 |
| `Det_ReportTransientFault` | Sync | `Std_ReturnType` | Records a transient fault tuple; intended for self-healing conditions that do not require a permanent diagnostic event. | 8.1.3.5 |
| `Det_GetVersionInfo` | Sync | `void` | Writes the module version into a caller-supplied `Std_VersionInfoType*`. No internal state change. | 8.1.3.6 |

Note: `Det_ReportError` is the only DET API directly invoked by the Dio driver per CAR-004 section 3. All Dio DET error codes (`DIO_E_PARAM_INVALID_CHANNEL_ID`, etc.) reach DET through `Det_ReportError`.

---

## 2. Configuration Containers

The Det configuration tree (SWS section 10.2) is shallow: a root `Det` container, a module-wide `DetGeneral`, and a `DetConfigSet` that aggregates per-module reporting policy.

- **`Det`** — Root container; references one `DetGeneral` and one `DetConfigSet` (10.2.1).
- **`DetGeneral`** — Module-wide switches: enables `Det_GetVersionInfo`, the runtime-error and transient-fault APIs, and the report-buffer behaviour (10.2.2).
- **`DetConfigSet`** — Aggregates per-module error-handling parameters (e.g. `DetModule`, `DetModuleInstance`) so DET can filter and route reports by `ModuleId` (10.2.4).

Adjacent containers `DetNotification` (10.2.3), `DetModule` (10.2.5), and `DetModuleInstance` (10.2.6) are noted for completeness but are out of demo scope.

---

## 3. Reported Error Semantics

Every `Det_Report*` API takes the same four-parameter tuple, defined in SWS section 8.1.3.2 and used identically across `Det_ReportError`, `Det_ReportRuntimeError`, and `Det_ReportTransientFault`:

| Parameter | Type | Origin | Meaning |
|---|---|---|---|
| `ModuleId` | `uint16` | The calling BSW module's published module ID (e.g. Dio = 120 per AUTOSAR module-ID list). | Identifies which BSW module raised the error. |
| `InstanceId` | `uint8` | The calling module's per-instance index (Dio only ever has one instance, so this is 0). | Disambiguates multiple instances of the same module. |
| `ApiId` | `uint8` | A per-module constant defined in the caller's SWS (e.g. Dio defines `DIO_READ_CHANNEL_ID`, `DIO_WRITE_CHANNEL_ID`, ... in its section 8.2). | Identifies which API function inside the module was executing when the error was raised. |
| `ErrorId` | `uint8` | The caller's DET error code (e.g. `DIO_E_PARAM_INVALID_CHANNEL_ID`, see CAR-004 section 3). | Categorises the error type. |

How Dio populates the tuple: per the Dio SWS section 7.6.1, every Dio API has a `Det_ReportError(MODULE_ID_DIO, instance, <API_ID for that function>, <DIO_E_*>)` call inside its parameter-validation block, guarded by `DioDevErrorDetect`. The tuple identifies the offending call site precisely enough that an integrator can map a single DET log line back to one line of Dio source code.

Error classification taxonomy (SWS section 7.5):
- 7.5.1 Development Errors — `Det_ReportError`. This is the path Dio uses.
- 7.5.2 Runtime Errors — `Det_ReportRuntimeError`.
- 7.5.3 Production Errors — handed off to DEM by the integrator.
- 7.5.4 Extended Production Errors — OEM-specific.

Numeric values of any DET-side error constants are NOT quoted in this CAR — the PDF binary body was not parsed (see section 5 limitation flag). Refer to SWS section 7.5 / 8.1 of the downloaded PDF before generating code.

---

## 4. Demo Scope Hint

To mirror the four-API Dio slice in CAR-004 section 4, the DET surface exposed by the CIPHER demo is similarly minimal:

- **`Det_ReportError`** — the only DET API called by Dio in the demo path; receives every `DIO_E_PARAM_*` raised by `Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`, and `Dio_GetVersionInfo` parameter-validation branches.
- **`Det_Init`** — invoked once during demo startup so the report path is live before Dio is exercised.
- **`Det_GetVersionInfo`** — symmetrical with `Dio_GetVersionInfo`; exercises the `Std_VersionInfoType` interface and a NULL-pointer test branch with zero hardware interaction.

Explicitly **stubbed / out of demo scope** (mentioned in section 1 so the API coverage table stays complete):
- `Det_Start` — stubbed to a no-op; demo treats DET as operational immediately after `Det_Init`.
- `Det_ReportRuntimeError` — stub that records the call but performs no DEM hand-off.
- `Det_ReportTransientFault` — stub; not invoked by the Dio demo path.

This slice gives the demo: one initialisation, one error-report path, and one diagnostic — the minimum that produces a complete DET-side traceability matrix that locks into the Dio-side matrix from CAR-004.

---

## 5. Source

- **Primary URL (R24-11, latest):** https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DefaultErrorTracer.pdf
- **Fallback URL (R23-11):** https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_DefaultErrorTracer.pdf
- **Historical filenames:** `AUTOSAR_SWS_DET.pdf`, `AUTOSAR_CP_SWS_DevelopmentErrorTracer.pdf` (both redirect to the Default Error Tracer document in R24-11; the module short name `Det` is preserved).
- **Release tag used:** R24-11 (Classic Platform, AUTOSAR R24-11 release wave) — matches CAR-004.
- **Document ID:** CP_SWS_DefaultErrorTracer_017
- **Fetched:** 2026-05-17

**Verification status against R24-11 PDF metadata:**
- Six public APIs (`Det_Init`, `Det_Start`, `Det_ReportError`, `Det_ReportRuntimeError`, `Det_ReportTransientFault`, `Det_GetVersionInfo`) — confirmed present in R24-11 API specification table (sections 8.1.3.1 through 8.1.3.6).
- Configuration containers `Det`, `DetGeneral`, `DetConfigSet` — confirmed present in R24-11 section 10.2.
- `(ModuleId, InstanceId, ApiId, ErrorId)` tuple — confirmed as the shared parameter shape across the three `Det_Report*` APIs.

**Unverified / flagged items:**
- The explicit ASIL classification sentence in the SWS body — the fetched metadata reported "Not specified in provided content"; the CIPHER team MUST confirm by reading section 4 / section 7 of the downloaded PDF before the demo HLD is frozen. The frontmatter records the conservative integrator-classified position.
- Numeric values of DET-internal status / API-ID constants — the PDF binary was NOT parsed inside this agent and no numeric values are quoted in this CAR. Numeric Dio-side error codes are listed in CAR-004 section 3 with the same caveat.
- Whether `Det_Start` is required or optional in R24-11 — section 8.1.3.3 reports it as present; the demo treats `Det_Init` alone as sufficient. Cross-check before code generation.

**Limitation flag:** As with CAR-004, the PDF binary body text was not parsed. Metadata was extracted via a single high-level WebFetch read that returned the document section structure and the API summary table only. Downstream artifacts that need exact numeric constants or the verbatim ASIL classification paragraph MUST trigger a manual PDF review.

---

## 6. Forward Brief

This CAR feeds the following downstream CIPHER demo artifacts and pairs with CAR-004:

| Artifact | Trigger from CAR-006 |
|---|---|
| Demo HLD | Section 1 API table extends the HLD interface table with the DET-side surface that CAR-004 Dio APIs call into. |
| Demo LLD | Three-API demo slice (section 4) is the DET-side LLD scope envelope. |
| Demo test plan | Tuple semantics (section 3) become the assertion shape for every Dio negative-test case in CAR-004 section 3. |
| Demo traceability matrix | Section numbers in section 1 become the upstream-requirement IDs for the DET-side rows. |
| ASIL gate report | Integrator-classified ASIL position (section 0) is the gate's claim string for the DET module. |
