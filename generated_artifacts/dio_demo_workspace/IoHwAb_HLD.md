# IoHwAb (I/O Hardware Abstraction) — High-Level Design (HLD)

| Field | Value |
|---|---|
| Document Title | IoHwAb — High-Level Design |
| Document ID | HLD-IOHWAB-001 |
| Version | 1.0 |
| Status | DRAFT |
| Date | 2026-05-17 |
| Author | CIPHER HLD Author (AI-assisted) |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Safety Claim | ASIL-B by inheritance from Dio (CAR-007 §5; CAR-004 §0) |
| Source Specification | CAR-007 — AUTOSAR Classic Platform R24-11, Layered SWA reference |
| Module Short Name | IoHwAb |
| Notice | DEMO HLD — NOT FOR PRODUCTION USE. Generated for the CIPHER ASDLC demo trial (4-API slice). |
| **WARNING** | **SYNTHESIZED — NO NORMATIVE SWS. The IoHwAb API surface described here is INVENTED for the CIPHER demo. No single AUTOSAR SWS standardizes IoHwAb — see CAR-007 §0 and §2. Every requirement and contract below is non-normative.** |

---

## 1. Scope & Module Purpose

The I/O Hardware Abstraction (IoHwAb) module sits in the **ECU Abstraction Layer** of the AUTOSAR Classic Platform, directly above the Microcontroller Abstraction Layer (MCAL) — i.e. above Dio, Port, Adc, Pwm, Icu, etc. — and directly below the Runtime Environment (RTE) and the application Software Components (SWCs).

**What IoHwAb does** (per CAR-007 §1):
- Translates **ECU-level symbolic signal names** (e.g. `LedOut`, `Switch`) into **MCAL driver channel IDs** (e.g. `DIO_CHANNEL_LED1`, `DIO_CHANNEL_SW1`).
- Hides which physical pin / port / microcontroller realizes a given logical signal so an application or RTE port can be re-wired at the IoHwAb level without touching application code.
- Acts as a **transparent pass-through** to the underlying MCAL drivers — no buffering, no scaling, no filtering.

**What IoHwAb does NOT do**:
- It does not configure pin direction (Port driver's job).
- It does not generate DET errors of its own (CAR-007 §3 — no DET hooks in standard architecture).
- It does not carry an AUTOSAR module ID, vendor ID, or version triplet (no SWS-mandated identification).

**Demo scope (this HLD)**. Per CAR-007 §3 / §6 the CIPHER demo covers exactly four IoHwAb APIs, all synchronous, all consuming the Dio MCAL only:

| Demo API | Downstream Dio call (CAR-007 §3, §4) | Direction |
|---|---|---|
| `IoHwAb_Init` | (none directly; sequenced after `Port_Init`) | init |
| `IoHwAb_GetSignal_LedOut` | `Dio_ReadChannel(DIO_CHANNEL_LED1)` | output read-back |
| `IoHwAb_SetSignal_LedOut` | `Dio_WriteChannel(DIO_CHANNEL_LED1, level)` | output |
| `IoHwAb_GetSignal_Switch` | `Dio_ReadChannel(DIO_CHANNEL_SW1)` | input |

**Out of demo scope (deferred)**. Port-level, group-level, ADC, PWM, ICU, OCU, and GPT wrappers. The demo's IoHwAb slice deliberately does NOT consume `Dio_FlipChannel` or `Dio_GetVersionInfo` (CAR-007 §6).

---

## 2. Dependencies

| Dependency | Direction | Purpose | Reference |
|---|---|---|---|
| **Dio Driver** (`Dio_ReadChannel`, `Dio_WriteChannel`) | Downstream call dependency | Realizes every IoHwAb_Get/Set call in this demo slice. Channel IDs `DIO_CHANNEL_LED1` and `DIO_CHANNEL_SW1` defined in `Dio_Cfg.h`. | CAR-007 §3, §4; CAR-004 §1 |
| **Port Driver** (`Port_Init`) | Upstream init-order dependency | Configures pin direction and mux before any IoHwAb_* read or write is legal. Sequenced by EcuM/BswM before `IoHwAb_Init`. | CAR-007 §3 (init order note) |
| **`Dio_Cfg.h`** (config-generated header) | Header dependency | Provides the channel-ID macros (`DIO_CHANNEL_LED1`, `DIO_CHANNEL_SW1`). In production this is emitted by the Dio config tool from ARXML. | CAR-007 §4; this workspace's `Dio_Cfg.h` |
| **`Std_Types.h`** (MCAL framework) | Header dependency | Provides `Std_ReturnType`, `boolean`, `E_OK`, `E_NOT_OK`. In the demo, these are stubbed inline in `IoHwAb.h` and `Dio.h`. | (no SWS for IoHwAb — synthesized) |
| **MCU driver** | Optional | A real IoHwAb could consume MCU for trim/calibration; not used in this demo slice. | CAR-007 §1 |

IoHwAb does **not** depend on DET (no error reporting paths defined by standard architecture, CAR-007 §3), nor on EcuM, COM, NVRAM Manager, or any timing/scheduler service. No periodic main function.

---

## 3. Configuration Model

**SYNTHESIZED — NO NORMATIVE SWS.** Unlike Dio (whose `Dio`, `DioPort`, `DioChannel`, `DioChannelGroup`, `DioConfig` containers are normatively defined in `AUTOSAR_CP_SWS_DIODriver` §10.1), IoHwAb has **no AUTOSAR-mandated configuration container schema**. The (non-normative) `AUTOSAR_CP_SWS_IOHardwareAbstraction` guideline self-describes as "not intended to standardize this module" and does not enumerate configuration parameters. See CAR-007 §2 for the full caveat.

The demo's configuration consists of:

- **`Dio_Cfg.h`** (this workspace) — Provides the channel-ID macros `DIO_CHANNEL_LED1 = 0x12` (port 1, pin 2) and `DIO_CHANNEL_SW1 = 0x05` (port 0, pin 5). Per AUTOSAR convention, config-generated channel symbols live in `Dio_Cfg.h`, not the base `Dio.h`. CAR-007 §4.
- **Symbolic mapping table** (compiled into `IoHwAb.c`) — IoHwAb_GetSignal_LedOut hard-codes `DIO_CHANNEL_LED1`; IoHwAb_GetSignal_Switch hard-codes `DIO_CHANNEL_SW1`. In a production IoHwAb this would be a const lookup table indexed by an enum of signal IDs; the demo collapses it for clarity.
- **Optional vendor table** — Vector MICROSAR, EB tresos, etc. each ship their own proprietary container schema (e.g. `IoHwAbConfig`, `IoHwAbSignal`, `IoHwAbPhysicalLink`). These are vendor extensions and are not standardized.

Variant: pre-compile only in the demo. Post-build variant is conceivable for an IoHwAb but not exercised here.

---

## 4. API Contracts

Each subsection below is one demo API. Signatures match `IoHwAb.h` exactly.

### 4.1 IoHwAb_Init (synthesized, CAR-007 §3)

**Synopsis.** One-time initialization of the IoHwAb signal-to-channel map.

**Signature.**
```c
Std_ReturnType IoHwAb_Init(void);
```

**Pre-conditions.**
- `Port_Init` has already been invoked by EcuM/BswM (CAR-007 §3 init-order note).
- The Dio driver has been initialized (Dio_Init in a full integration; the demo Dio is stateless and needs no init).

**Post-conditions.**
- An internal `IoHwAb_Initialized` flag is set to TRUE.
- Returns `E_OK`.

**Downstream call.** None directly — initialization is essentially a flag toggle in this demo slice. A vendor IoHwAb would unpack a configuration set here.

**Re-entrancy.** Not re-entrant (initialization API).

**MISRA notes.** Single exit (R15.5).

---

### 4.2 IoHwAb_GetSignal_LedOut (synthesized, CAR-007 §3)

**Synopsis.** Reads back the latched LedOut actuator state via the Dio MCAL.

**Signature.**
```c
Std_ReturnType IoHwAb_GetSignal_LedOut(boolean * out_state);
```

**Pre-conditions.**
- `IoHwAb_Init` has been called.
- `out_state` is a non-NULL pointer to writable storage.
- The pin behind `DIO_CHANNEL_LED1` is configured as **output** (Port responsibility).

**Post-conditions.**
- On success: `*out_state = (Dio_ReadChannel(DIO_CHANNEL_LED1) == STD_HIGH)`; returns `E_OK`.
- On NULL pointer: no downstream Dio call is performed; returns `E_NOT_OK`. No DET (CAR-007 §3, no DET hooks).

**Downstream call.** `Dio_ReadChannel(DIO_CHANNEL_LED1)` (CAR-004 §4; SWS 8.3.1).

**Re-entrancy.** Re-entrant by inheritance from `Dio_ReadChannel` (pure read; HLD-DIO-006).

**MISRA notes.** Single exit (R15.5); explicit `((boolean *)0)` NULL comparison (R14.4).

---

### 4.3 IoHwAb_SetSignal_LedOut (synthesized, CAR-007 §3)

**Synopsis.** Drives the LedOut actuator to the requested logical state.

**Signature.**
```c
Std_ReturnType IoHwAb_SetSignal_LedOut(boolean state);
```

**Pre-conditions.**
- `IoHwAb_Init` has been called.
- The pin behind `DIO_CHANNEL_LED1` is configured as **output** (Port responsibility).

**Post-conditions.**
- `Dio_WriteChannel(DIO_CHANNEL_LED1, state ? STD_HIGH : STD_LOW)` is invoked.
- Returns `E_OK`.

**Downstream call.** `Dio_WriteChannel(DIO_CHANNEL_LED1, level)` (CAR-004 §4; SWS 8.3.2).

**Re-entrancy.** Re-entrant for distinct channels; same channel is single-owner per CAR-004 §6 FFI rationale (inherited).

**MISRA notes.** Single exit (R15.5).

---

### 4.4 IoHwAb_GetSignal_Switch (synthesized, CAR-007 §3)

**Synopsis.** Reads the current Switch input sensor state via the Dio MCAL.

**Signature.**
```c
Std_ReturnType IoHwAb_GetSignal_Switch(boolean * out_state);
```

**Pre-conditions.**
- `IoHwAb_Init` has been called.
- `out_state` is a non-NULL pointer.
- The pin behind `DIO_CHANNEL_SW1` is configured as **input** (Port responsibility).

**Post-conditions.**
- On success: `*out_state = (Dio_ReadChannel(DIO_CHANNEL_SW1) == STD_HIGH)`; returns `E_OK`.
- On NULL pointer: no downstream Dio call; returns `E_NOT_OK`.

**Downstream call.** `Dio_ReadChannel(DIO_CHANNEL_SW1)` (CAR-004 §4; SWS 8.3.1).

**Re-entrancy.** Re-entrant — pure read.

**MISRA notes.** Single exit (R15.5); explicit NULL comparison.

---

## 5. Error Handling

**SYNTHESIZED — no DET hooks in standard architecture (CAR-007 §3).** The demo IoHwAb APIs do not invoke `Det_ReportError` and do not declare any `IOHWAB_E_*` mnemonics. The rationale:

1. No normative SWS exists for IoHwAb, hence no enumeration of standard error codes (CAR-007 §0, §2).
2. CAR-007 §3 records that "none of [the four APIs] define new DET error codes; any DET reporting is forwarded from the Dio layer."
3. Parameter validation failures (NULL `out_state` in this slice) are surfaced via the function return value as `E_NOT_OK`. This is the standard `Std_ReturnType` pattern.

Downstream DET errors raised by `Dio_ReadChannel` / `Dio_WriteChannel` (notably `DIO_E_PARAM_INVALID_CHANNEL_ID = 0x0A`) propagate transparently — the calling IoHwAb function continues to return `E_OK` because the Dio API has no return-code on the write path and returns `STD_LOW` (safe default) on the read path. The integrator is responsible for inspecting the DET sink if needed.

**No production errors** are defined.

---

## 6. ASIL Claim & FFI Rationale

**Claim.** Per CAR-007 §5, IoHwAb has **no normative ASIL classification of its own** (no SWS). The demo claim is **ASIL-B by inheritance** from the consumed Dio channels (CAR-004 §0). IoHwAb is treated as a transparent pass-through that neither raises nor lowers the ASIL of the underlying Dio call.

**Why inheritance is valid.**
1. Each IoHwAb_* API in §4 reduces to exactly one Dio_ReadChannel or Dio_WriteChannel (or, for `IoHwAb_Init`, a single boolean assignment).
2. No new mutable state is introduced at the IoHwAb layer beyond the `IoHwAb_Initialized` flag — which is written once and never read across partition boundaries.
3. Argument transformations (`boolean -> STD_HIGH/STD_LOW`, `STD_HIGH -> boolean TRUE`) are trivial branch-free or single-branch conversions verifiable by inspection.

**Freedom From Interference (FFI).**
- **Spatial FFI.** IoHwAb owns no shared mutable data beyond `IoHwAb_Initialized` (single-writer at init time). All other state lives in the Dio shadow registers, governed by Dio's FFI claim (HLD-DIO-006 / CAR-004 §6 inherited).
- **Temporal FFI.** No blocking, no sleeps, no callbacks. WCET = WCET(Dio_*) + O(1) wrapper overhead.
- **Information / Control-flow FFI.** No callbacks registered, no interrupts handled.
- **No DET coupling.** Because IoHwAb does not call DET (§5), it adds zero new coupling surface beyond what Dio already declares.

---

## 7. Memory & Sectioning

| Symbol | Storage Class | Linker Section (expected) | Notes |
|---|---|---|---|
| `IoHwAb_Init`, `IoHwAb_GetSignal_LedOut`, `IoHwAb_SetSignal_LedOut`, `IoHwAb_GetSignal_Switch` | code | `.text` | Public APIs; flash. |
| `IoHwAb_Initialized` | data (static, zero-init) | `.bss` | One byte; written by `IoHwAb_Init`. |
| (no const config tables in demo) | rodata | `.rodata` | A production IoHwAb would carry a `const IoHwAbSignal_t signal_map[]` here. Demo inlines the mapping. |

**Flag — no significant data.** The IoHwAb module contributes essentially nothing to RAM beyond a single byte flag. There is no UC 4.4 overlap concern.

**Demo limitation.** As with Dio, the addresses in `firmware.map` are synthetic — the demo is not linked through a real toolchain.

---

## 8. HLD Requirement Table

The following requirements are the **trace targets** for the downstream S1N1 LLD generator. Every LLD-IOHWAB row produced by S1N1 must cite at least one of these IDs in its `HLD_PARENT` column. **The "SWS Section" column intentionally reads "N/A — synthesized" for every row because no normative SWS exists for IoHwAb.**

| HLD_ID | Description | ASIL | Parent System Req | Verification Method | SWS Section |
|---|---|---|---|---|---|
| HLD-IOHWAB-001 | The IoHwAb module shall provide a one-time initialization API `IoHwAb_Init` that completes before any IoHwAb_Get*/IoHwAb_Set* call and that returns `E_OK`. The caller (EcuM/BswM) is responsible for sequencing `Port_Init` before `IoHwAb_Init`. | ASIL-B | SYS-IOHWAB-100 | Test | N/A — synthesized (see CAR-007 §3) |
| HLD-IOHWAB-002 | The IoHwAb module shall abstract ECU-level symbolic signal names (`LedOut`, `Switch`) to MCAL Dio channel IDs (`DIO_CHANNEL_LED1`, `DIO_CHANNEL_SW1`) so application/RTE code can be re-wired without modification. | ASIL-B | SYS-IOHWAB-101 | Review | N/A — synthesized (see CAR-007 §1, §4; AUTOSAR_CP_EXP_LayeredSoftwareArchitecture Doc ID 53) |
| HLD-IOHWAB-003 | `IoHwAb_SetSignal_LedOut(boolean state)` shall drive the LED actuator by invoking `Dio_WriteChannel(DIO_CHANNEL_LED1, state ? STD_HIGH : STD_LOW)` and shall return `E_OK`. | ASIL-B | SYS-IOHWAB-102 | Test | N/A — synthesized (see CAR-007 §3) |
| HLD-IOHWAB-004 | `IoHwAb_GetSignal_LedOut(boolean * out_state)` shall read back the LED actuator state by invoking `Dio_ReadChannel(DIO_CHANNEL_LED1)` and shall write `TRUE` to `*out_state` iff the returned level is `STD_HIGH`. | ASIL-B | SYS-IOHWAB-103 | Test | N/A — synthesized (see CAR-007 §3) |
| HLD-IOHWAB-005 | `IoHwAb_GetSignal_Switch(boolean * out_state)` shall read the Switch input by invoking `Dio_ReadChannel(DIO_CHANNEL_SW1)` and shall write `TRUE` to `*out_state` iff the returned level is `STD_HIGH`. | ASIL-B | SYS-IOHWAB-104 | Test | N/A — synthesized (see CAR-007 §3) |
| HLD-IOHWAB-006 | Every IoHwAb_* API that accepts a pointer output parameter shall, on a NULL pointer argument, perform no downstream Dio call and shall return `E_NOT_OK`. | ASIL-B | SYS-IOHWAB-105 | Test | N/A — synthesized (see CAR-007 §3 — no DET hooks; NULL surfaced via Std_ReturnType only) |
| HLD-IOHWAB-007 | Every IoHwAb_Get*/IoHwAb_Set* API shall be implemented as a transparent delegation to exactly one Dio MCAL call (`Dio_ReadChannel` or `Dio_WriteChannel`), with no buffering, scaling, filtering, or retry. | ASIL-B | SYS-IOHWAB-106 | Review | N/A — synthesized (see CAR-007 §3; AUTOSAR_CP_EXP_LayeredSoftwareArchitecture) |
| HLD-IOHWAB-008 | The IoHwAb module shall **not** call `Det_ReportError` and shall **not** define any `IOHWAB_E_*` development-error mnemonics. Any error condition observable at the IoHwAb boundary shall be surfaced via the `Std_ReturnType` return value (`E_OK` / `E_NOT_OK`) only. | ASIL-B | SYS-IOHWAB-107 | Inspection | N/A — synthesized (see CAR-007 §3 — "none of [the APIs] define new DET error codes; any DET reporting is forwarded from the Dio layer") |
| HLD-IOHWAB-009 | The IoHwAb module's ASIL-B claim shall be by inheritance from the consumed Dio channels (CAR-004 §0) and shall not modify ASIL upward or downward; freedom-from-interference between the four signal APIs is guaranteed structurally because each touches a distinct Dio channel ID. | ASIL-B | SYS-IOHWAB-108 | Analysis | N/A — synthesized (see CAR-007 §5) |

---

## 9. Open Issues / Demo Limitations

- **SYNTHESIZED — NO NORMATIVE SWS (repeated).** The entire IoHwAb API surface in this HLD is INVENTED for the CIPHER demo. Per CAR-007 §0, §2, §7, no AUTOSAR SWS standardizes IoHwAb; the `AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` is explicitly a guideline, not a normative module specification. Reviewers should treat every requirement in §8 as a *demo design artifact* and not as a trace to an external standard. Only the downstream Dio calls (CAR-004) are externally traceable.
- **Vendor-divergent reality.** Real IoHwAb implementations from Vector MICROSAR, EB tresos, ETAS RTA-BSW, Mentor VSx, etc. all carry proprietary symbol naming, container schemas, and (often) DET hooks. The four `IoHwAb_GetSignal_* / IoHwAb_SetSignal_*` names chosen here are illustrative only.
- **No real Port driver init.** As with the Dio HLD, the demo assumes the pin direction has been correctly configured. HLD-IOHWAB-001 records the `Port_Init` sequencing requirement but does not exercise it.
- **`Dio_Cfg.h` is demo-only.** The channel-ID macros in `Dio_Cfg.h` (`DIO_CHANNEL_LED1 = 0x12`, `DIO_CHANNEL_SW1 = 0x05`) are hand-written for the demo. In production they would be generated by the Dio configuration tool from ARXML containers (`DioPort`, `DioChannel`).
- **No DET — and therefore no negative-path observability.** Because IoHwAb has no DET (HLD-IOHWAB-008), the only negative-path signal at the IoHwAb boundary is the `E_NOT_OK` return on NULL pointer. Downstream `DIO_E_PARAM_INVALID_CHANNEL_ID` is observable only at the Dio layer's stubbed DET, which itself is unlinked in the demo (Dio_HLD.md §9).
- **R24-11 vs R23-11.** CAR-007 §0 lists both releases for the Layered SWA reference and the (non-normative) IoHwAb guideline. Any later manual review should confirm no material delta in the layering description between the two releases.
- **No IoHwAb-Init configuration argument.** A production IoHwAb often takes a `const IoHwAb_ConfigType *` at init. The demo `IoHwAb_Init(void)` deliberately omits this for the 4-API slice.

---

## 10. Traceability Notes

Downstream traceability is realised by the **S1N1 LLD generator** (`cipher/agents/devnex_assistant/prompts/lld_gen_v1.md`), which consumes `IoHwAb.c` / `IoHwAb.h` plus this HLD and emits `IoHwAb_TEMP_LLD_updated.csv`. Every LLD row produced by S1N1 is required by the prompt to populate the `HLD_PARENT` column with one of the `HLD-IOHWAB-NNN` IDs from §8 above (with `REVIEW_NEEDED` as the recorded fallback when no match exists).

**Critical reviewer note.** Because every HLD-IOHWAB-NNN requirement is itself **non-normative** (synthesized from CAR-007, not extracted from an AUTOSAR SWS — see §8 column "SWS Section" and the §0 frontmatter warning), the upward trace from LLD ends at this HLD and does **not** continue into an external standard. Any audit chain that requires an external normative anchor for IoHwAb must explicitly note that the chain terminates at CAR-007 / `AUTOSAR_CP_EXP_LayeredSoftwareArchitecture` (explanatory) — not at a SWS.

Expected coarse mapping (informative — S1N1 produces the binding mapping):

| Source element (in `IoHwAb.c` / `IoHwAb.h` / `Dio_Cfg.h`) | Likely HLD parent |
|---|---|
| `Std_ReturnType IoHwAb_Init(void)` | HLD-IOHWAB-001 |
| `Std_ReturnType IoHwAb_SetSignal_LedOut(boolean)` | HLD-IOHWAB-002, HLD-IOHWAB-003, HLD-IOHWAB-007, HLD-IOHWAB-009 |
| `Std_ReturnType IoHwAb_GetSignal_LedOut(boolean *)` | HLD-IOHWAB-002, HLD-IOHWAB-004, HLD-IOHWAB-006, HLD-IOHWAB-007, HLD-IOHWAB-009 |
| `Std_ReturnType IoHwAb_GetSignal_Switch(boolean *)` | HLD-IOHWAB-002, HLD-IOHWAB-005, HLD-IOHWAB-006, HLD-IOHWAB-007, HLD-IOHWAB-009 |
| `static boolean IoHwAb_Initialized` | HLD-IOHWAB-001 |
| `#define DIO_CHANNEL_LED1` / `DIO_CHANNEL_SW1` (in `Dio_Cfg.h`) | HLD-IOHWAB-002 |
| Absence of any `Det_ReportError` call site | HLD-IOHWAB-008 |

Upstream traceability is provided in §8 by the `SYS-IOHWAB-1NN` Parent System Req column. These IDs are demo-synthetic and are recorded so that any future linkage to a real SYS-level requirements baseline preserves the row identity.

---

End of HLD.
