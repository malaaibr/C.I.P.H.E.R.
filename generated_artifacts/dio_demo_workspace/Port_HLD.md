# Port Driver — High-Level Design (HLD)

| Field | Value |
|---|---|
| Document Title | Port Driver — High-Level Design |
| Document ID | HLD-PORT-001 |
| Version | 1.0 |
| Status | DRAFT |
| Date | 2026-05-17 |
| Author | CIPHER HLD Author (AI-assisted) |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Safety Claim | ASIL-B per AUTOSAR_CP_SWS_PortDriver |
| Source Specification | CAR-005 — AUTOSAR Classic Platform R24-11, `CP_SWS_PortDriver_040` |
| Module Short Name | Port |
| Notice | DEMO HLD - NOT FOR PRODUCTION USE. Generated for the CIPHER ASDLC demo trial (init-only 2-API slice per CAR-005 §4). |

---

## 1. Scope & Module Purpose

The Port (Port Driver) module is the AUTOSAR Classic Platform MCAL component responsible for one-shot pin-multiplexer and pin-direction configuration at ECU startup. It is the upstream prerequisite for the Dio driver (CAR-004): every Dio channel addressed at runtime must first have had its parent pin configured by Port at init.

**What Port does** (per CAR-005 §1 / SWS §7):
- Applies the configured direction (input/output) and mode (digital/alt-function) to every pin enumerated in `PortConfigSet` at startup.
- Publishes its vendor ID, module ID, and software version triplet via `Port_GetVersionInfo`.

**What Port does NOT do** (in this demo):
- It does not change pin direction at runtime (`Port_SetPinDirection` — CAR-005 §1 row, OUT of demo scope per CAR-005 §4).
- It does not change pin mode at runtime (`Port_SetPinMode` — CAR-005 §1 row, OUT of demo scope per CAR-005 §4).
- It does not re-anchor configured directions (`Port_RefreshPortDirection` — CAR-005 §1 row, OUT of demo scope per CAR-005 §4).
- It does not perform any electrical read or write — those are Dio's APIs (CAR-004 §4).

**Demo scope (this HLD).** Per CAR-005 §4 the Port demo slice is the init-and-diagnostic surface only:

| Demo API | SWS Section | Service ID | CAR-005 §1 row |
|---|---|---|---|
| `Port_Init` | 8.3.1 | 0x00 | One-shot init, non-re-entrant |
| `Port_GetVersionInfo` | 8.3.4 | 0x03 | Diagnostic, re-entrant |

**Out of demo scope (deferred).** `Port_SetPinDirection` (8.3.2), `Port_RefreshPortDirection` (8.3.3), `Port_SetPinMode` (8.3.5) — catalogued in CAR-005 §1 for spec completeness, explicitly excluded by CAR-005 §4 from all downstream demo artifacts.

---

## 2. Dependencies

Compile-time and run-time dependencies (CAR-005 §1 notes; SWS §6):

| Dependency | Direction | Purpose | SWS / CAR-005 Reference |
|---|---|---|---|
| **MCAL framework (`Std_Types.h`)** | Header dependency | Provides `Std_VersionInfoType` and the `uint8 / uint16` types used in Port's public signatures. The demo re-uses the stubbed types from `Dio.h` via `#include "Dio.h"`. | SWS §8.4 |
| **MCU clocks (MCU driver)** | Upstream init-order dependency | The MCU driver must have configured the peripheral clock for each GPIO bank before `Port_Init` runs; otherwise pin writes have no effect. | SWS §6 "General Constraints" |
| **DET (Development Error Tracer)** | Downstream service | Receives error reports via `Det_ReportError(ModuleId, InstanceId, ApiId, ErrorId)` when `PortDevErrorDetect == ON`. CAR-005 §3 records seven mnemonics. | SWS §7.6, §7.6.1; CAR-005 §3 |
| **Dio driver** | Downstream consumer | Dio assumes Port has run to completion before any Dio API is invoked (CAR-004 §1 / Dio_HLD §2). Port itself does not call Dio. | CAR-004 §1 dependency footnote |

Port does NOT depend on EcuM, COM, NvM, ICU, GPT, or any scheduler service.

---

## 3. Configuration Model

The Port configuration tree is hierarchical (CAR-005 §2; SWS §10.1).

- **`Port`** (CAR-005 §2; SWS 10.1.1) — Root container; one per ECU configuration.
- **`PortGeneral`** (CAR-005 §2; SWS 10.1.2) — Module-wide switches: `PortDevErrorDetect`, `PortVersionInfoApi`, `PortSetPinDirectionApi`, `PortSetPinModeApi`. The demo treats `PortSetPinDirectionApi` and `PortSetPinModeApi` as FALSE (those APIs are out of scope per CAR-005 §4) and `PortVersionInfoApi` as TRUE.
- **`PortContainer`** (CAR-005 §2; SWS 10.1.3) — One container per microcontroller port. The demo defines three (PortA, PortB, PortC) to align with the Dio demo (CAR-004).
- **`PortPin`** (CAR-005 §2; SWS 10.1.4) — One container per single pin; carries `PortPinId`, `PortPinDirection`, `PortPinDirectionChangeable`, `PortPinInitialMode`, `PortPinMode`, `PortPinModeChangeable`, `PortPinLevelValue`. The demo projection (`Port_PinConfig_t` in `Port.h`) keeps only `PinId`, `Direction`, and `Mode` — the `*_Changeable` flags are irrelevant in the init-only slice.
- **`PortConfigSet`** (CAR-005 §2; SWS 10.1.5) — Top-level set passed to `Port_Init`. The demo projection is `Port_ConfigType { uint16 NumPins; const Port_PinConfig_t * Pins; }`.

The demo treats the configuration as pre-compile (constants prepared by the integrator and passed as `ConfigPtr` to `Port_Init`).

---

## 4. API Contracts

Each subsection below is one demo API. Signatures match `Port.h` exactly.

### 4.1 Port_Init (SWS 8.3.1)

**Synopsis.** One-shot initialisation: walks the `Port_ConfigType` pin list and records each pin's configured direction and mode into the in-memory pin-shadow table.

**Signature.**
```c
void Port_Init(const Port_ConfigType * ConfigPtr);
```

**Pre-conditions.**
- The MCU driver has run and the GPIO peripheral clocks are enabled (CAR-005 §1, SWS §6).
- `ConfigPtr` is non-NULL and points to a fully populated `Port_ConfigType` whose `Pins` array has `NumPins` entries.
- The call is the first invocation of `Port_Init` since power-on (the API is non-re-entrant per CAR-005 §1).

**Post-conditions.**
- On success: every in-range pin in the config set has its `Direction` and `Mode` recorded in `Port_PinShadow[]`; the module-internal flag `Port_Initialized` is set TRUE.
- On NULL `ConfigPtr`: no shadow mutation; `PORT_E_INIT_FAILED` is reported to DET; `Port_Initialized` stays FALSE.
- On a pin entry with an out-of-range `PinId`: that entry is skipped, `PORT_E_PARAM_PIN` is reported to DET, the remaining entries continue to be processed.

**DET errors.** `PORT_E_INIT_FAILED` (NULL `ConfigPtr`), `PORT_E_PARAM_PIN` (out-of-range entry) — CAR-005 §3.

**Re-entrancy.** Non-re-entrant (CAR-005 §1). A second call replaces the previous shadow state.

**MISRA notes.** Single-exit pattern (R15.5); explicit `((const Port_ConfigType *)0)` NULL comparison (R14.4).

**SWS section.** 8.3.1 (CAR-005 §1; section number FLAGGED in CAR-005 §5 limitation #3).

---

### 4.2 Port_GetVersionInfo (SWS 8.3.4)

**Synopsis.** Fills a caller-supplied `Std_VersionInfoType` with the Port module's vendor ID, module ID, and software version triplet.

**Signature.**
```c
void Port_GetVersionInfo(Std_VersionInfoType * versioninfo);
```

**Pre-conditions.**
- `versioninfo` is a non-NULL pointer to a writable `Std_VersionInfoType`.
- `PortVersionInfoApi == ON` in `PortGeneral` (CAR-005 §2).

**Post-conditions.**
- Fields are populated from the compile-time symbols in `Port.h`: `PORT_VENDOR_ID = 0x002B`, `PORT_MODULE_ID = 124`, version `4.8.0`.
- On NULL pointer: no fields are written; `PORT_E_PARAM_POINTER` is reported to DET.

**DET errors.** `PORT_E_PARAM_POINTER` (CAR-005 §3).

**Re-entrancy.** Re-entrant (CAR-005 §1).

**MISRA notes.** Single-exit via guard (R15.5); explicit `((Std_VersionInfoType *)0)` NULL comparison (R14.4).

**SWS section.** 8.3.4 (CAR-005 §1; FLAGGED per CAR-005 §5 limitation #3).

---

## 5. Error Handling

### 5.1 DET model

The Port module uses DET as its sole error-reporting channel (CAR-005 §3; SWS §7.6). Every API in §4 emits at most one DET error per invocation before any state mutation. The reporting call is:

```c
Det_ReportError(PORT_MODULE_ID /* 124 */, 0u, <ApiId>, <ErrorId>);
```

When `PortDevErrorDetect == OFF`, the `Det_ReportError` call site is compiled out by the integrator. Port declares no production / runtime errors in the standard configuration (CAR-005 §3 closing note).

### 5.2 DET error codes (from CAR-005 §3 — see §5.3 caveat)

| Mnemonic | Typical Value | Reported by (demo) | Trigger condition |
|---|---|---|---|
| `PORT_E_PARAM_PIN` | `0x0A` | `Port_Init` (demo extension for out-of-range entry in config set); `Port_SetPinDirection`/`Port_SetPinMode` (out of demo scope) | `PinId` not in configured set |
| `PORT_E_DIRECTION_UNCHANGEABLE` | `0x0B` | (out of demo scope — `Port_SetPinDirection`) | Pin's `PortPinDirectionChangeable == FALSE` |
| `PORT_E_INIT_FAILED` | `0x0C` | `Port_Init` | NULL or invalid `ConfigPtr` |
| `PORT_E_PARAM_INVALID_MODE` | `0x0D` | (out of demo scope — `Port_SetPinMode`) | Mode not in pin's allowed-modes set |
| `PORT_E_MODE_UNCHANGEABLE` | `0x0E` | (out of demo scope — `Port_SetPinMode`) | Pin's `PortPinModeChangeable == FALSE` |
| `PORT_E_UNINIT` | `0x0F` | (out of demo scope — `Set*` / `Refresh*`) | API called before `Port_Init` |
| `PORT_E_PARAM_POINTER` | `0x10` | `Port_GetVersionInfo`, `Port_Init` | NULL pointer where non-NULL required |

### 5.3 Caveat — numeric DET values and ASIL claim unverified

CAR-005 §5 "Limitation flag" records four items as **not verified inside the CAR agent**:
1. Numeric DET error code values (§7.6.1 body text not parsable via WebFetch).
2. Explicit ASIL classification sentence (§4 / §7 body text not parsable via WebFetch).
3. Exact SWS section numbers 8.3.1–8.3.5 for each API (typical R24-11 ordering — needs PDF section-index cross-check).
4. Whether R24-11 introduces vendor-extension DET codes beyond the seven mnemonics.

These four items are carried forward to §9 of this HLD as Open Issues and must be confirmed during the manual cross-check of `AUTOSAR_CP_SWS_PortDriver.pdf` (R24-11) before the demo safety case freezes.

### 5.4 API Service IDs

| API | Service ID |
|---|---|
| `Port_Init` | `0x00` |
| `Port_GetVersionInfo` | `0x03` |

---

## 6. ASIL Claim & FFI Rationale

**Claim.** CAR-005 §0 records the verification target as **"ASIL-B per AUTOSAR_CP_SWS_PortDriver"**, with the broader SWS note that Port can be configured to support applications up to ASIL D. The Port demo HLD therefore claims **ASIL-B** for `Port_Init` (a configuration-data validation path that is the safety prerequisite for every downstream Dio actuator/sensor API) and **QM** for the purely diagnostic `Port_GetVersionInfo`.

**Why ASIL-B is sufficient for the demo slice.**
1. `Port_Init` consumes a statically-known configuration set; its input domain is finite and review-bounded.
2. There is no shared mutable state with other ASIL partitions during init — Port runs once before any application code observes the pin shadow.
3. DET acts as a safety net for systematic config-data faults at integration time.

**Freedom From Interference (FFI) considerations.**
- **Spatial FFI.** The only writable Port state is `Port_PinShadow[48]` and the `Port_Initialized` flag. Both are touched only by `Port_Init`. No other module writes either symbol.
- **Temporal FFI.** `Port_Init` is non-re-entrant and runs before any application runnable. `Port_GetVersionInfo` is a pure read of compile-time constants. Neither blocks.
- **Information / Control-flow FFI.** No callbacks, no ISRs, no shared queues.
- **DET safety net.** When `PortDevErrorDetect == ON`, every NULL-pointer and out-of-range-pin path is observable via DET, enabling integrator-level supervisors to detect systematic config faults without modifying production behaviour.

---

## 7. Memory & Sectioning

| Symbol | Storage Class | Linker Section (expected) | Notes |
|---|---|---|---|
| `Port_Init`, `Port_GetVersionInfo` | code | `.text` | Public APIs; placed in flash by the STM32H7 linker script. |
| `Port_IsValidPinId` | code (static) | `.text` | File-scope helper; internal linkage by MISRA R8.7. |
| `Port_PinShadow[48]` | data (static, zero-initialised) | `.bss` | 48 × `Port_PinConfig_t`. Zero-init by the C runtime; no flash image required. |
| `Port_Initialized` | data (static, zero-initialised) | `.bss` | Single `boolean`; FALSE at startup. |
| `ConfigPtr` target (the integrator-supplied `Port_ConfigType` and its `Port_PinConfig_t` array) | rodata | `.rodata` | The config struct table is `const`-qualified and lives in flash. The pointer is read-only inside `Port_Init`. |
| Vendor / module / version macros | n/a (preprocessor) | n/a | Inlined at every call site of `Port_GetVersionInfo`. |

**UC 4.4 overlap concern.** The Port module contributes `Port_PinShadow[]` and `Port_Initialized` to `.bss`. These do not overlap any `_SAFE` or `_NVM` region defined in `stm32h7xx_flash.ld`. The expectation is that the overlap check passes trivially for the demo.

**Demo limitation.** Addresses in `firmware.map` are synthetic (the demo is not linked through a real ARM toolchain); the §10 traceability path links HLD-PORT requirements to LLD symbols but does not depend on numeric addresses.

---

## 8. HLD Requirement Table

Every LLD-PORT row produced downstream by S1N1 must cite at least one of these IDs in its `HLD_PARENT` column.

| HLD_ID | Description | ASIL | Parent System Req | Verification Method | CAR-005 Section |
|---|---|---|---|---|---|
| HLD-PORT-001 | The Port module shall, via `Port_Init`, record the configured `Direction` and `Mode` of every in-range `Port_PinConfig_t` entry in the supplied `Port_ConfigType` into the pin shadow table, and shall mark the module initialised on success. | ASIL-B | SYS-PORT-100 | Test | §1, §4 |
| HLD-PORT-002 | The Port module shall, via `Port_GetVersionInfo`, populate the caller-supplied `Std_VersionInfoType` with `PORT_VENDOR_ID`, `PORT_MODULE_ID`, and the software version triplet defined in `Port.h`. | QM | SYS-PORT-101 | Test | §1, §4 |
| HLD-PORT-003 | The Port module shall report Development Errors to DET via `Det_ReportError(PORT_MODULE_ID, 0, <ApiId>, <ErrorId>)` using the seven mnemonics defined in CAR-005 §3, gated on `PortDevErrorDetect`. | ASIL-B | SYS-PORT-102 | Inspection | §3 |
| HLD-PORT-004 | `Port_Init` shall, upon detecting a NULL `ConfigPtr`, report `PORT_E_INIT_FAILED` to DET and leave the pin shadow and `Port_Initialized` flag unmodified. | ASIL-B | SYS-PORT-103 | Test | §3, §4 |
| HLD-PORT-005 | The Port module shall expose a single `Port_Initialized` flag set TRUE only on a successful `Port_Init` completion, enabling downstream code to detect un-initialised Port usage (multi-init / pre-init protection). | ASIL-B | SYS-PORT-104 | Review | §1, §4 |
| HLD-PORT-006 | The Port module shall be invoked after the MCU driver has enabled the GPIO peripheral clocks and before any Dio API is called; the integration order is recorded as a precondition rather than enforced inside Port. | ASIL-B | SYS-PORT-105 | Review | §1 (notes), §4 |
| HLD-PORT-007 | The Port module shall accept only pin IDs in the range `[0, 48)` (3 ports × 16 pins) at init; entries outside this range shall be DET-flagged with `PORT_E_PARAM_PIN` and skipped, without aborting the init pass. | ASIL-B | SYS-PORT-106 | Test | §2, §3 |
| HLD-PORT-008 | `Port_GetVersionInfo` shall report `PORT_E_PARAM_POINTER` to DET when called with a NULL `versioninfo` pointer, and shall not write any field of the output structure in that case. | QM | SYS-PORT-107 | Test | §3, §4 |

---

## 9. Open Issues / Demo Limitations

The four CAR-005 §5 limitation-flag items are carried into this HLD as Open Issues and must be confirmed during the manual cross-check of `AUTOSAR_CP_SWS_PortDriver.pdf` (R24-11):

- **OI-PORT-1 — DET numeric values unverified.** Per CAR-005 §5 item (1), the numeric values `0x0A / 0x0B / 0x0C / 0x0D / 0x0E / 0x0F / 0x10` are *typical* AUTOSAR R24-11 assignments. They have not been confirmed against the body text of SWS §7.6.1. Manual cross-check against the downloaded PDF is required before any safety-case freeze.
- **OI-PORT-2 — ASIL classification sentence unverified.** Per CAR-005 §5 item (2), the explicit ASIL classification sentence in §4 / §7 of the PDF was not retrievable via WebFetch. The "ASIL-B per AUTOSAR_CP_SWS_PortDriver" claim must be cross-checked against the body text.
- **OI-PORT-3 — SWS section numbers unverified.** Per CAR-005 §5 item (3), the section numbers 8.3.1 (`Port_Init`) and 8.3.4 (`Port_GetVersionInfo`) used throughout this HLD are quoted from the *typical* R24-11 ordering and need a PDF section-index cross-check.
- **OI-PORT-4 — Vendor-extension DET codes unverified.** Per CAR-005 §5 item (4), it is not confirmed whether R24-11 adds vendor-extension DET codes beyond the seven mnemonics listed. The §5.2 table must be revisited once the PDF is reviewed.
- **OI-PORT-5 — DET is stubbed.** `Det_ReportError` is declared `extern` in `Port.c` and is not linked against a real DET sink in the demo. Negative-path tests inspect call invocation only.
- **OI-PORT-6 — No real MCU init.** The demo assumes the MCU peripheral-clock prerequisite is met; there is no `Mcu_Init` invocation in the demo runtime.
- **OI-PORT-7 — Synthetic firmware.map.** The addresses in `firmware.map` are placeholders; the demo is not linked through a real ARM toolchain. UC 4.4 overlap checks are structural only.

---

## 10. Traceability Notes

Downstream traceability is realised by the **S1N1 LLD generator** (`cipher/agents/devnex_assistant/prompts/lld_gen_v1.md`), which consumes `Port.c` / `Port.h` plus this HLD and emits `Port_TEMP_LLD_updated.csv`. Every LLD row populates `HLD_PARENT` with one of the `HLD-PORT-NNN` IDs from §8 (with `REVIEW_NEEDED` as the recorded fallback when no match exists).

Expected coarse mapping (informative — S1N1 produces the binding mapping):

| Source element (in `Port.c` / `Port.h`) | Likely HLD parent |
|---|---|
| `void Port_Init(const Port_ConfigType *)` | HLD-PORT-001, HLD-PORT-003, HLD-PORT-004, HLD-PORT-005, HLD-PORT-007 |
| `void Port_GetVersionInfo(Std_VersionInfoType *)` | HLD-PORT-002, HLD-PORT-003, HLD-PORT-008 |
| `static Port_PinShadow[48]` | HLD-PORT-001, HLD-PORT-007 |
| `static Port_Initialized` | HLD-PORT-005 |
| `static Port_IsValidPinId(...)` | HLD-PORT-007 |
| `PORT_E_*` macros | HLD-PORT-003 |
| `PORT_SID_*` macros | HLD-PORT-003 |
| `PORT_VENDOR_ID` / `PORT_MODULE_ID` / `PORT_SW_*_VERSION` | HLD-PORT-002 |
| `Port_PinConfig_t`, `Port_ConfigType`, `Port_PinDirectionType`, `Port_PinModeType`, `Port_PinType` | HLD-PORT-001, HLD-PORT-002 (typedef carriers) |
| `Det_ReportError` extern declaration | HLD-PORT-003 |

Upstream traceability is provided in §8 by the `SYS-PORT-1NN` Parent System Req column. These IDs are demo-synthetic and are recorded so that any future linkage to a real SYS-level requirements baseline preserves the row identity.

---

End of HLD.
