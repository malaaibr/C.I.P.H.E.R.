# Dio Driver — High-Level Design (HLD)

| Field | Value |
|---|---|
| Document Title | Dio Driver — High-Level Design |
| Document ID | HLD-DIO-001 |
| Version | 1.0 |
| Status | DRAFT |
| Date | 2026-05-17 |
| Author | CIPHER HLD Author (AI-assisted) |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Safety Claim | ASIL-B per AUTOSAR_CP_SWS_DIODriver |
| Source Specification | CAR-004 — AUTOSAR Classic Platform R24-11, `CP_SWS_DIODriver_020` |
| Module Short Name | Dio |
| Notice | DEMO HLD - NOT FOR PRODUCTION USE. Generated for the CIPHER ASDLC demo trial (4-API slice). |

---

## 1. Scope & Module Purpose

The Dio (Digital Input/Output) module provides synchronous, re-entrant access to MCU general-purpose digital pins via configuration-generated symbolic IDs. It is part of the AUTOSAR Classic Platform Microcontroller Abstraction Layer (MCAL) and is consumed by upper Basic Software (BSW) modules and, through the RTE, by application Software Components (SWCs).

**What Dio does** (per CAR-004 §1 / SWS §7):
- Reads the latched electrical level of a single configured channel.
- Writes a commanded level (`STD_HIGH` / `STD_LOW`) to a single configured channel.
- Atomically toggles (flips) the level of a single configured channel (read-modify-write).
- Reports module identification and version information through `Std_VersionInfoType`.

**What Dio does NOT do**:
- It does not configure pin direction (input vs output). Pin direction is owned by the **Port Driver** (see §2).
- It does not handle analog signals — those are the responsibility of the ADC/DAC modules.
- It does not generate or service interrupts. Edge detection and pin-change notifications belong to the ICU and GPT modules.
- It does not perform any non-volatile storage of the last-written level; the only persistence is the latched MCU port register.

**Demo scope (this HLD)**. Per WBS-0002 §2.2 the CIPHER ASDLC demo trial covers exactly four APIs (CAR-004 §4):

| Demo API | SWS Section | Service ID |
|---|---|---|
| `Dio_WriteChannel` | 8.3.2 | 0x01 |
| `Dio_ReadChannel`  | 8.3.1 | 0x00 |
| `Dio_FlipChannel`  | 8.3.8 | 0x11 |
| `Dio_GetVersionInfo` | 8.3.7 | 0x12 |

**Out of demo scope (deferred)**. `Dio_ReadPort` (8.3.3), `Dio_WritePort` (8.3.4), `Dio_ReadChannelGroup` (8.3.5), `Dio_WriteChannelGroup` (8.3.6), and `Dio_MaskedWritePort` (8.3.9) are part of the full SWS surface and are catalogued in CAR-004 §1 for coverage completeness, but they are explicitly excluded from the demo HLD requirement table in §8 and from all downstream demo artifacts (LLD, code, tests).

---

## 2. Dependencies

The Dio module has the following compile-time and run-time dependencies (CAR-004 §1 notes; SWS §6 "General Constraints"):

| Dependency | Direction | Purpose | SWS / CAR-004 Reference |
|---|---|---|---|
| **Port Driver** (Port_Init) | Upstream init-order dependency | Configures the MCU pin multiplexer and direction (input/output) for every pin Dio will subsequently address. Dio assumes the pin has already been switched to digital and to the correct direction before any Dio API is called. | SWS §6 "Constraints"; CAR-004 §1 (ASIL impact column footnote) |
| **`Std_Types.h`** (MCAL framework) | Header dependency | Provides `Std_ReturnType`, `Std_VersionInfoType`, `STD_HIGH`/`STD_LOW` symbols used in Dio's public signatures (CAR-004 §1, §3). For the demo, the header is stubbed inline in `Dio.h` behind `#ifndef STD_TYPES_INCLUDED`. | SWS §8.4 (Type definitions) |
| **DET (Development Error Tracer)** | Downstream service | Receives error reports via `Det_ReportError(ModuleId, InstanceId, ApiId, ErrorId)` when `DioDevErrorDetect == ON`. The Dio module does not depend on DET for production-error reporting (none defined — CAR-004 §3 closing note). | SWS §7.6, §7.6.1; CAR-004 §3 |
| **MCU register map** | Hardware contract | Provides the physical port-data registers that Dio reads and writes. In the demo, this is replaced by the in-memory `Dio_PortShadow[]` array (see §7). | SWS §7 introduction |

The Dio module does not depend on any timing/scheduler service (no periodic main function), on EcuM, on COM, or on the NVRAM Manager.

---

## 3. Configuration Model

Configuration is structured as a hierarchical tree of ECU Configuration Parameters (SWS §10.1; CAR-004 §2). Each container is described once below.

- **`Dio`** (CAR-004 §2; SWS 10.1.2) — The root container. Each ECU configuration instantiates exactly one `Dio` container which aggregates one `DioConfig` set and one `DioGeneral` settings block.

- **`DioGeneral`** (CAR-004 §2; SWS 10.1.3) — Module-wide compile-time switches that gate optional behaviour:
  - `DioDevErrorDetect` — enables DET reporting paths in every API (see §5).
  - `DioVersionInfoApi` — enables compilation of `Dio_GetVersionInfo`.
  - `DioFlipChannelApi` — enables compilation of `Dio_FlipChannel`.
  - `DioMaskedWritePortApi` — enables compilation of `Dio_MaskedWritePort` (out of demo scope).

- **`DioPort`** (CAR-004 §2; SWS 10.1.4) — One container per microcontroller port. Carries `DioPortId` (the symbolic port identifier). The demo configuration (`cipher_config_dio.json`) defines three ports (PortA, PortB, PortC) each 16 bits wide.

- **`DioChannel`** (CAR-004 §2; SWS 10.1.5) — One container per single pin. Carries `DioChannelId` and a reference to its parent `DioPort`. The valid set of channel IDs at run-time is the union of every `DioChannel` instance under every `DioPort` under the active `DioConfig`.

- **`DioChannelGroup`** (CAR-004 §2; SWS 10.1.6) — Defines a contiguous bit-field within a port via `DioPortMask` and `DioPortOffset`. **Not used by any demo API**; documented here for spec completeness.

- **`DioConfig`** (CAR-004 §2; SWS 10.1.7) — The top-level configuration set that aggregates every `DioPort` and `DioChannelGroup` instance the runtime is allowed to address. A future `Dio_Init(const Dio_ConfigType*)` (vendor extension, not in the 4-API demo slice) would receive a pointer to one such set.

- **Variant marker** (`VARIANT-PRE-COMPILE` / `VARIANT-POST-BUILD`) — SWS 10.1.1. The demo treats configuration as pre-compile (constants baked into `Dio.c`).

---

## 4. API Contracts

Each subsection below is one demo API. Signatures match `Dio.h` exactly.

### 4.1 Dio_WriteChannel (SWS 8.3.2)

**Synopsis.** Sets the electrical level of a single configured Dio channel.

**Signature.**
```c
void Dio_WriteChannel(Dio_ChannelType ChannelId, Dio_LevelType Level);
```

**Pre-conditions.**
- The Port Driver has been initialised and `ChannelId` corresponds to a pin configured as **output** (SWS §6).
- `ChannelId` is a member of the active `DioConfig` channel set.
- `Level` is either `STD_HIGH` or `STD_LOW`.

**Post-conditions.**
- On success: the latched output of the addressed pin equals `Level`. A subsequent `Dio_ReadChannel(ChannelId)` returns `Level` (assuming no external pin override).
- On detected invalid `ChannelId`: no port register is modified; `DIO_E_PARAM_INVALID_CHANNEL_ID` is reported to DET (see §5).

**DET errors.** `DIO_E_PARAM_INVALID_CHANNEL_ID` when `ChannelId` is not in the configured set (CAR-004 §3).

**Re-entrancy.** Re-entrant for **different** channel IDs (SWS §7 "Functional specification"); concurrent calls on the **same** channel produce an implementation-defined ordering (last writer wins at the port register level — acceptable since each Dio channel is owned by exactly one SWC, see §6).

**MISRA notes.** Implementation in `Dio.c` uses MISRA-C:2012 Rule 15.5 single-exit pattern; the read-modify-write of the port shadow is bracketed by a range check.

**SWS section.** 8.3.2 (CAR-004 §1).

---

### 4.2 Dio_ReadChannel (SWS 8.3.1)

**Synopsis.** Returns the current latched electrical level of a single configured Dio channel.

**Signature.**
```c
Dio_LevelType Dio_ReadChannel(Dio_ChannelType ChannelId);
```

**Pre-conditions.**
- The Port Driver has been initialised and `ChannelId` corresponds to a pin configured as **input or output** (a configured-output pin may be legally read back — SWS §7).
- `ChannelId` is a member of the active `DioConfig` channel set.

**Post-conditions.**
- Return value is `STD_HIGH` if the addressed bit in the port input/data register is set; `STD_LOW` otherwise.
- On detected invalid `ChannelId`: the function reports `DIO_E_PARAM_INVALID_CHANNEL_ID` and returns `STD_LOW` as the safe default (consistent with `Dio.c` line 110 initialisation of `retval`).

**DET errors.** `DIO_E_PARAM_INVALID_CHANNEL_ID` (CAR-004 §3).

**Re-entrancy.** Fully re-entrant — pure read with no shared mutable state visible at the API boundary.

**MISRA notes.** Single exit point (R15.5); explicit cast on bit-mask construction to silence R10.x integer-promotion warnings.

**SWS section.** 8.3.1 (CAR-004 §1).

---

### 4.3 Dio_FlipChannel (SWS 8.3.8, introduced AUTOSAR 4.x)

**Synopsis.** Inverts (toggles) the level of a single configured Dio channel and returns the **new** level.

**Signature.**
```c
Dio_LevelType Dio_FlipChannel(Dio_ChannelType ChannelId);
```

**Pre-conditions.**
- The Port Driver has been initialised and `ChannelId` corresponds to a pin configured as **output**.
- `ChannelId` is a member of the active `DioConfig` channel set.
- The optional API is enabled in configuration: `DioFlipChannelApi == ON` in `DioGeneral`.

**Post-conditions.**
- The latched output of the addressed pin is the logical complement of its value at function entry.
- Return value reflects the **post-flip** level (`STD_HIGH` if the bit is now set, otherwise `STD_LOW`).
- On detected invalid `ChannelId`: no port register is modified; DET is notified; the function returns `STD_LOW`.

**DET errors.** `DIO_E_PARAM_INVALID_CHANNEL_ID` (CAR-004 §3).

**Re-entrancy.** Re-entrant for different channel IDs. The read-modify-write on the same channel is **not** automatically atomic against a concurrent `Dio_WriteChannel` on the same port (lost-update window of one XOR operation). Per §6 each channel is owned by exactly one SWC, so the demo treats this as benign.

**MISRA notes.** Single exit (R15.5); explicit operator parenthesisation around `(~bit_mask)` for R12.1.

**SWS section.** 8.3.8 (CAR-004 §1).

---

### 4.4 Dio_GetVersionInfo (SWS 8.3.7)

**Synopsis.** Fills a caller-supplied `Std_VersionInfoType` structure with the Dio module's vendor ID, module ID, and software version triplet.

**Signature.**
```c
void Dio_GetVersionInfo(Std_VersionInfoType* VersionInfo);
```

**Pre-conditions.**
- `VersionInfo` is a non-NULL pointer to a writable `Std_VersionInfoType`.
- The optional API is enabled in configuration: `DioVersionInfoApi == ON` in `DioGeneral`.

**Post-conditions.**
- `VersionInfo->vendorID`, `moduleID`, `sw_major_version`, `sw_minor_version`, `sw_patch_version` are populated from the compile-time symbols defined in `Dio.h` (`DIO_VENDOR_ID = 0x002B`, `DIO_MODULE_ID = 120`, version triplet `4.8.0`).
- On NULL pointer: no fields are written; `DIO_E_PARAM_POINTER` is reported to DET.

**DET errors.** `DIO_E_PARAM_POINTER` (CAR-004 §3).

**Re-entrancy.** Fully re-entrant when distinct `VersionInfo` buffers are passed; behaviour with aliased buffers is the caller's concern.

**MISRA notes.** Single exit via guard (R15.5); explicit `((Std_VersionInfoType*)0)` NULL comparison rather than implicit boolean conversion (R14.4).

**SWS section.** 8.3.7 (CAR-004 §1).

---

## 5. Error Handling

### 5.1 DET model

The Dio module uses the Development Error Tracer (DET) as its sole error-reporting channel (SWS §7.6; CAR-004 §3). Every API in §4 emits at most one DET error per invocation, **before** any side-effect on the shadow port register. The reporting call is:

```c
Det_ReportError(DIO_MODULE_ID /* 120 */, 0u, <ApiId>, <ErrorId>);
```

When `DioDevErrorDetect == OFF`, the `Det_ReportError` call site is compiled out by the integrator. The Dio module declares **no production / runtime errors** in the standard configuration (SWS §7.6.2; CAR-004 §3 closing note).

### 5.2 DET error codes (from CAR-004 §3 — see §5.3 caveat)

| Mnemonic | Typical Value | Reported by (demo) | Trigger condition |
|---|---|---|---|
| `DIO_E_PARAM_INVALID_CHANNEL_ID` | `0x0A` | `Dio_ReadChannel`, `Dio_WriteChannel`, `Dio_FlipChannel` | `ChannelId` not present in the active `DioConfig` channel set. The demo enforces this with `ChannelId >= DIO_DEMO_MAX_CHANNEL_ID`. |
| `DIO_E_PARAM_INVALID_PORT_ID` | `0x14` | (out of demo scope — `Dio_Read/WritePort`, `Dio_MaskedWritePort`) | `PortId` not present in active config. Listed for spec completeness. |
| `DIO_E_PARAM_INVALID_GROUP` | `0x1F` | (out of demo scope — group APIs) | Group pointer not in active config. Listed for spec completeness. |
| `DIO_E_PARAM_POINTER` | `0x20` | `Dio_GetVersionInfo` | `VersionInfo == NULL`. |
| `DIO_E_PARAM_CONFIG` | `0x30` | (vendor extension — `Dio_Init`) | Invalid `Dio_ConfigType*` at init. Not exercised by the 4-API demo slice. |

### 5.3 Caveat — numeric DET values unverified

CAR-004 §5 "Verification status" explicitly flags the numeric DET error values as **"typical AUTOSAR assignments [that] MUST be re-verified against section 7.6.1 of the downloaded PDF before they appear in generated code."** The values above are reproduced from CAR-004 and from `Dio.h` lines 26–30, but the CAR-004 author was unable to extract them directly from the body text of SWS §7.6.1. This is recorded as an Open Issue in §9 and is to be confirmed during the manual verification pass that CAR-004 §5 mandates.

### 5.4 API Service IDs

Service IDs used in DET reports (SWS §8.2; matches `Dio.h`):

| API | Service ID |
|---|---|
| `Dio_ReadChannel` | `0x00` |
| `Dio_WriteChannel` | `0x01` |
| `Dio_FlipChannel` | `0x11` |
| `Dio_GetVersionInfo` | `0x12` |

---

## 6. ASIL Claim & FFI Rationale

**Claim.** CAR-004 §0 records the demo's verification target as **"ASIL-B per AUTOSAR_CP_SWS_DIODriver"**, with the broader note that the SWS itself classifies Dio as supporting safety applications up to ASIL D when configured per the standard. The demo HLD therefore claims **ASIL-B** for the three actuator/sensor APIs (`Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`) and **QM** for the purely diagnostic `Dio_GetVersionInfo`.

**Why ASIL-B is sufficient for the demo slice.**
1. Each demo API has a finite, statically-known input domain (a `Dio_ChannelType` in `[0, DIO_DEMO_MAX_CHANNEL_ID)`), making boundary verification by inspection and test exhaustive at the channel-ID layer.
2. There is no shared mutable state across SWCs: per the FFI assumption in §6 below, each channel is owned by exactly one SWC.
3. DET acts as a safety net for systematic parameter-validation failures at integration time.

**Freedom From Interference (FFI) considerations.**
- **Spatial FFI.** The only writable state is `Dio_PortShadow[]` (in the demo) or the MCU port-data register (in production). Both are bit-addressed, and the demo configuration assigns each channel to a single owning SWC by design (recorded in `cipher_config_dio.json`). No two ASIL partitions write the same bit. Read paths do not modify state and are therefore FFI-trivial.
- **Temporal FFI.** No Dio API blocks, sleeps, or yields. Worst-case execution time is bounded by an integer division, modulo, and a single memory access — well within the WCET budgets of any ASIL-B caller's runnable.
- **Information / Control-flow FFI.** No callback registration, no interrupt, no shared queue. The four APIs are pure functions of their arguments plus the latched port state.
- **DET as safety net.** When `DioDevErrorDetect == ON`, every invalid-parameter path is observable through the DET interface, allowing an integrator-level supervisor to detect systematic faults during integration testing without modifying production behaviour.

---

## 7. Memory & Sectioning

The demo Dio module produces the following memory artefacts (cross-referenced against the workspace's `firmware.map` and `stm32h7xx_flash.ld`):

| Symbol | Storage Class | Linker Section (expected) | Notes |
|---|---|---|---|
| `Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`, `Dio_GetVersionInfo` | code | `.text` | Public APIs; placed in flash by the STM32H7 linker script. |
| `Dio_GetPortBackingRef` | code (static) | `.text` | File-scope helper; internal linkage by MISRA R8.7. |
| (no const config tables in demo) | rodata | `.rodata` | In a full integration, `DioConfig` and the channel-to-port lookup would live here. The demo collapses these into compile-time constants. |
| `Dio_PortShadow[3]` | data (static, initialised non-zero) | `.data` | 3 × `Dio_PortRegister_t` (each ≈ 4 bytes). Initialised image lives in flash and is copied to RAM at startup by the C runtime. |
| Vendor / module / version macros | n/a (preprocessor) | n/a | Inlined at every call site of `Dio_GetVersionInfo`. |

**UC 4.4 overlap concern.** The CIPHER demo UC 4.4 ("memory layout overlap check") cross-validates that no static-storage symbol from any module overlaps a `_SAFE` or `_NVM` region defined in `stm32h7xx_flash.ld`. The Dio module contributes only `Dio_PortShadow[]` to RAM, and only to the default `.data` region. The expectation is that the overlap check passes trivially for the demo and that any later real Dio implementation declares its shadow state in the same `.data` (or vendor-defined `.dio_shadow`) section to keep the overlap report stable.

**Demo limitation.** The addresses in `firmware.map` are synthetic (the demo is not linked against a real toolchain). The §10 traceability path links HLD-DIO requirements to LLD symbols but does not depend on the numeric addresses being physically meaningful.

---

## 8. HLD Requirement Table

The following requirements are the **trace targets** for the downstream S1N1 LLD generator. Every LLD-DIO row produced by S1N1 must cite at least one of these IDs in its `HLD_PARENT` column.

| HLD_ID | Description | ASIL | Parent System Req | Verification Method | SWS Section |
|---|---|---|---|---|---|
| HLD-DIO-001 | The Dio module shall set the electrical level of a single configured channel (`STD_HIGH` or `STD_LOW`) via `Dio_WriteChannel`, with no side effect when `ChannelId` is outside the active configuration set. | ASIL-B | SYS-DIO-100 | Test | 8.3.2 |
| HLD-DIO-002 | The Dio module shall return the current latched level of a single configured channel via `Dio_ReadChannel`, returning `STD_LOW` as the safe default when `ChannelId` is outside the active configuration set. | ASIL-B | SYS-DIO-101 | Test | 8.3.1 |
| HLD-DIO-003 | The Dio module shall atomically invert (toggle) the level of a single configured channel via `Dio_FlipChannel` and return the post-flip level; the operation shall be a no-op when `ChannelId` is outside the active configuration set. | ASIL-B | SYS-DIO-102 | Test | 8.3.8 |
| HLD-DIO-004 | The Dio module shall publish its vendor ID, module ID, and software version triplet through `Dio_GetVersionInfo` whenever a non-NULL `Std_VersionInfoType*` is supplied. | QM | SYS-DIO-103 | Test | 8.3.7 |
| HLD-DIO-005 | The Dio module shall report Development Errors to DET via `Det_ReportError(DIO_MODULE_ID, 0, <ApiId>, <ErrorId>)` for every invalid-parameter detection, gated on `DioDevErrorDetect`, using the five mnemonics defined in CAR-004 §3 (`DIO_E_PARAM_INVALID_CHANNEL_ID`, `_INVALID_PORT_ID`, `_INVALID_GROUP`, `_POINTER`, `_CONFIG`). | ASIL-B | SYS-DIO-104 | Inspection | 7.6, 7.6.1 |
| HLD-DIO-006 | All public Dio APIs shall be synchronous and re-entrant with respect to distinct channel IDs, requiring no internal locking, no interrupt masking, and no callback registration. | ASIL-B | SYS-DIO-105 | Analysis | 7.5, 7 (intro) |
| HLD-DIO-007 | The Dio module shall accept only channel IDs that are members of the active `DioConfig` set defined by the `Dio`, `DioPort`, and `DioChannel` configuration containers; any out-of-set ID shall fail the parameter check before any port register is modified. | ASIL-B | SYS-DIO-106 | Review | 10.1 (10.1.2, 10.1.4, 10.1.5, 10.1.7) |
| HLD-DIO-008 | `Dio_GetVersionInfo` shall expose the version triplet (`DIO_VENDOR_ID`, `DIO_MODULE_ID`, `DIO_SW_MAJOR_VERSION` / `_MINOR_` / `_PATCH_`) defined in `Dio.h`, and shall report `DIO_E_PARAM_POINTER` when called with a NULL output pointer. | QM | SYS-DIO-107 | Test | 8.3.7, 7.6.1 |
| HLD-DIO-009 | The Dio module shall depend on the Port Driver for pin-direction configuration and shall not modify any pin-mux or direction setting at any point in its own API surface. | ASIL-B | SYS-DIO-108 | Review | 6 (Constraints), 7 (intro) |
| HLD-DIO-010 | Compile-time inclusion of the optional APIs `Dio_FlipChannel` and `Dio_GetVersionInfo` shall be gated by `DioFlipChannelApi` and `DioVersionInfoApi` switches in `DioGeneral` respectively. | ASIL-B | SYS-DIO-109 | Inspection | 10.1.3 |

---

## 9. Open Issues / Demo Limitations

- **DET is stubbed.** `Det_ReportError` is declared `extern` in `Dio.c` and is not linked against a real DET implementation in the demo. Negative-path tests inspect call invocation rather than DET sink behaviour.
- **DET numeric codes unverified.** Per CAR-004 §5 "Limitation flag", the numeric values `0x0A / 0x14 / 0x1F / 0x20 / 0x30` are typical AUTOSAR assignments and have **not** been confirmed against the body text of SWS §7.6.1. Manual cross-check against the downloaded `AUTOSAR_CP_SWS_DIODriver.pdf` is required before any safety case freeze.
- **Synthetic firmware.map.** The addresses in `firmware.map` are placeholders; the demo is not linked through a real ARM toolchain. UC 4.4 overlap checks are structural only.
- **No real Port driver.** The demo assumes pin direction has already been set correctly; there is no `Port_Init` invocation in the demo runtime. Any HLD requirement that says "pin must be configured as output" (HLD-DIO-001, HLD-DIO-003) is satisfied by assumption rather than by demonstration.
- **R24-11 vs R23-11.** CAR-004 §0 records the source release as **R24-11**, with an R23-11 fallback URL listed. The body-text inspection that CAR-004 §5 flags as missing may, when performed, surface minor deltas between the two releases (most likely in optional-API gating). If R24-11 is unavailable to the manual reviewer, the §6 ASIL claim and the §5.2 DET table should be re-confirmed against R23-11 and any deltas captured in a v1.1 of this HLD.
- **No `Dio_Init` in demo.** The Dio_Init API and `DIO_E_PARAM_CONFIG` are documented for spec completeness only; they are not exercised by the 4-API slice.

---

## 10. Traceability Notes

Downstream traceability is realised by the **S1N1 LLD generator** (`cipher/agents/devnex_assistant/prompts/lld_gen_v1.md`), which consumes `Dio.c` / `Dio.h` plus this HLD and emits `Dio_TEMP_LLD_updated.csv`. Every LLD row produced by S1N1 is required by the prompt to populate the `HLD_PARENT` column with one of the `HLD-DIO-NNN` IDs from §8 above (with `REVIEW_NEEDED` as the recorded fallback when no match exists).

The expected coarse mapping (informative — S1N1 produces the binding mapping):

| Source element (in `Dio.c` / `Dio.h`) | Likely HLD parent |
|---|---|
| `void Dio_WriteChannel(...)` | HLD-DIO-001, HLD-DIO-005, HLD-DIO-007 |
| `Dio_LevelType Dio_ReadChannel(...)` | HLD-DIO-002, HLD-DIO-005, HLD-DIO-007 |
| `Dio_LevelType Dio_FlipChannel(...)` | HLD-DIO-003, HLD-DIO-005, HLD-DIO-007, HLD-DIO-010 |
| `void Dio_GetVersionInfo(...)` | HLD-DIO-004, HLD-DIO-008, HLD-DIO-010 |
| `static Dio_PortShadow[...]` | HLD-DIO-001, HLD-DIO-002, HLD-DIO-003 (state backing the actuator/sensor APIs) |
| `static Dio_GetPortBackingRef(...)` | HLD-DIO-002 (read-path helper) |
| `DIO_E_PARAM_*` macros | HLD-DIO-005 |
| `DIO_SID_*` macros | HLD-DIO-005 |
| `DIO_VENDOR_ID` / `DIO_MODULE_ID` / `DIO_SW_*_VERSION` | HLD-DIO-008 |
| `Std_VersionInfoType`, `Dio_ChannelType`, `Dio_PortType`, `Dio_LevelType`, `Dio_PortLevelType`, `Dio_PortRegister_t` | HLD-DIO-004 / HLD-DIO-008 (typedef carriers) |
| `Det_ReportError` extern declaration | HLD-DIO-005 |

Upstream traceability is provided in §8 by the `SYS-DIO-1NN` Parent System Req column. These IDs are demo-synthetic and are recorded so that any future linkage to a real SYS-level requirements baseline preserves the row identity.

---

End of HLD.
