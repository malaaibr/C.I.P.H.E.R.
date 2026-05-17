# LedActuator SWC — High-Level Design (HLD)

| Field | Value |
|---|---|
| Document Title | LedActuator Application SWC — High-Level Design |
| Document ID | HLD-LEDACT-001 |
| Version | 1.0 |
| Status | DRAFT |
| Date | 2026-05-17 |
| Author | CIPHER DEV+HLD Author (AI-assisted, vendor demo) |
| Process Reference | ASPICE SWE.2 (Software Architectural Design) |
| Safety Claim | ASIL-B per CAR-008 §5 (LedActuator vendor SWC instance) |
| Source Specification | CAR-008 — AUTOSAR_CP_TPS_SoftwareComponentTemplate R24-11 |
| Component Short Name | LedActuator |
| **Notice — VENDOR-DERIVED, NOT SWS-TRACED** | **This HLD describes a VENDOR-AUTHORED application SWC. There is NO AUTOSAR SWS for an application SWC. Every requirement in §8 is derived from the AUTOSAR Software Component Template (`AUTOSAR_CP_TPS_SoftwareComponentTemplate` R24-11) — it is NOT traced to a Dio-style SWS. DEMO HLD — NOT FOR PRODUCTION USE.** |

---

## 1. Scope & Component Purpose

The **LedActuator** is a vendor-authored AUTOSAR Classic application Software Component (SWC). Its single responsibility is to drive a status LED to follow the level of a physical switch input, on a 100 ms cyclic schedule. It demonstrates the application → RTE → IoHwAb → MCAL call chain end-to-end with the minimum SWC surface that still exercises every SWC Template construct.

**What LedActuator does** (vendor-derived from SWC Template §3 / §4.5; not SWS-traced):
- Hosts exactly one `RunnableEntity` (`LedActuator_MainFunction`) bound to a `TimingEvent` of period 100 ms.
- Reads a single boolean input — the current switch level — through the IoHwAb service `IoHwAb_GetSignal_Switch(boolean*)`.
- Drives a single boolean output — the LED level — through the IoHwAb service `IoHwAb_SetSignal_LedOut(boolean)`.
- Maintains one static byte of SWC-internal state (`LedActuator_LastSwitchState`) for transition latching (HLD-LEDACT-005).

**What LedActuator does NOT do**:
- It does not configure the I/O pin direction or pin-mux (Port driver responsibility, MCAL layer).
- It does not perform debouncing, edge-detection, or filtering — those are conceptually upstream.
- It does not report errors to DET. DET is a BSW concern; SWCs propagate failures via `Std_ReturnType` and (in production) via the RTE.
- It does not own any AUTOSAR module ID or vendor ID; application SWCs are not BSW modules.
- It does not consume the conceptual `P_LedControl` sender-receiver data element in the demo build (see §9 Open Issues — the upstream indicator-logic SWC is out of demo scope).

---

## 2. Dependencies

| Dependency | Direction | Purpose | Reference |
|---|---|---|---|
| **IoHwAb** | Downstream service | Provides `IoHwAb_GetSignal_Switch(boolean*)` and `IoHwAb_SetSignal_LedOut(boolean)`, both returning `Std_ReturnType`. The LedActuator runnable calls both prototypes once per cycle. | CAR-007 (assumed; see §9). Vendor-derived from SWC Template §4.3 (Port Interfaces — ClientServerInterface). |
| **RTE** | Bidirectional infrastructure | Schedules the runnable on its bound `TimingEvent`, transports port-element data, serialises runnable invocations (FFI), and bridges `P_LedHwAccess` client-server calls to the IoHwAb server. **The RTE-generated glue (`Rte_*` symbols) is conceptually present but invisible in this workspace** per Tier 2 demo scope. | Vendor-derived from SWC Template §4.5.3 (RTEEvent); §4.3 (ClientServerInterface). |
| **`Std_Types.h`** | Header dependency | Supplies `Std_ReturnType`, `E_OK`, `E_NOT_OK`, `boolean`. Stubbed inline in `Dio.h` in this workspace. | Vendor-derived from SWC Template §4.6 (Data Types). |
| **Upstream indicator-logic SWC** (provides `P_LedControl`) | Upstream sender | Conceptually produces the `LedState : boolean` data element consumed via `P_LedControl`. **Out of demo scope** — the demo runnable reads the switch directly via IoHwAb instead of consuming `P_LedControl`. The port and interface are still declared in the ARXML view (§3) so future revisions can drop in the upstream SWC without re-architecting LedActuator. | Vendor-derived from SWC Template §4.3 (SenderReceiverInterface). |

The LedActuator does not depend on COM, NVRAM Manager, EcuM (beyond invoking `LedActuator_Init`), or any timing service other than the RTE-generated `TimingEvent`.

---

## 3. Configuration Model

> **VENDOR-DERIVED — NOT SWS-TRACED.** The "configuration model" of an application SWC is its ARXML description, governed by `AUTOSAR_CP_TPS_SoftwareComponentTemplate` R24-11. The ARXML file itself is NOT in this workspace; it would be emitted by the RTE configuration tool from the structural description below. Only the C source representing the runnable body is delivered here.

The LedActuator SWC's ARXML structure is (per CAR-008 §1 / SWC Template §3, §4):

- **`AtomicSoftwareComponentType`** — short-name `LedActuator`. (SWC Template §4.2 "Component Type".)
- **`SwcInternalBehavior`** — short-name `LedActuator_IB`, attached to `LedActuator`. Declares no `ExclusiveArea` (single runnable, no shared mutable state — SWC Template §4.5 / §4.5.4).
- **`RunnableEntity`** — short-name `LedActuator_MainFunction`, owned by `LedActuator_IB`.
  - `Symbol` = `LedActuator_MainFunction` (matches the C entry point in `LedActuator.c`).
  - `CanBeInvokedConcurrently` = `false` (non-reentrant; the RTE serialises invocations — see §6 FFI).
- **`TimingEvent`** — short-name `LedActuator_TE_100ms`, owned by `LedActuator_IB`, references the runnable above, `period = 0.1 s` (100 ms). This is the sole RTEEvent binding for the runnable (SWC Template §4.5.3).
- **`PortPrototype` `P_LedControl`** — R-Port on `LedActuator`, typed by `SenderReceiverInterface` `IF_LedControl` which declares one `VariableDataPrototype` `LedState : boolean` (ApplicationDataType `LedState_T` → ImplementationDataType `boolean` via the package-level `DataTypeMappingSet`). (SWC Template §4.3 / §4.6.)
- **`PortPrototype` `P_LedHwAccess`** — R-Port on `LedActuator`, typed by `ClientServerInterface` `IF_LedHwAccess` which declares two operations:
  - `SetSignal_LedOut(IN state : boolean) : Std_ReturnType`
  - `GetSignal_Switch(OUT state : boolean) : Std_ReturnType`
  Both operations are connected to the IoHwAb server side at integration time (out of this artifact's scope).
- **AR-PACKAGE** — single namespace `/Demo/SWCs/LedActuator` rooting all of the above (SWC Template §3 "Document Structure" + `AUTOSAR_FO_TPS_GenericStructureTemplate`).
- **Variant marker** — `VARIANT-PRE-COMPILE`. The demo bakes the period and port wiring at compile time.

---

## 4. API Contracts

Each subsection below describes one externally visible C entry point. Signatures match `LedActuator.h` exactly.

### 4.1 LedActuator_Init

**Synopsis.** Resets SWC-internal state. Conceptually invoked once during ECU startup before the RTE begins firing the runnable's `TimingEvent`.

**Signature.**
```c
void LedActuator_Init(void);
```

**Trigger.** Single one-shot call from the integrator's startup sequence (or, in a future revision, from an `InitEvent`-bound init runnable). Vendor-derived from SWC Template §4.5 — not SWS-traced.

**Side effects.** Clears `LedActuator_LastSwitchState` to `FALSE`.

**Downstream calls.** None.

**Timing budget.** Constant-time; well below 100 µs on any target the demo would plausibly run on.

### 4.2 LedActuator_MainFunction

**Synopsis.** Periodic runnable body. Reads switch, drives LED, latches state.

**Signature.**
```c
void LedActuator_MainFunction(void);
```

**Trigger.** RTE `TimingEvent` with `period = 0.1 s` (100 ms), declared in ARXML (§3). Vendor-derived from SWC Template §4.5.3.

**Side effects.** Writes the LED level via `IoHwAb_SetSignal_LedOut(...)`. Updates `LedActuator_LastSwitchState` on a successful read+write cycle.

**Downstream calls.** Two, in order:
1. `IoHwAb_GetSignal_Switch(&sw_state)` — read switch.
2. `IoHwAb_SetSignal_LedOut(sw_state)` — drive LED.

If the read fails (`rc_get != E_OK`), the LED write is skipped and the previous LED level is preserved (HLD-LEDACT-006).

**Timing budget.** ≤ 1 ms wall-clock per invocation (HLD-LEDACT-008), well within the 100 ms task period. The dominant cost is the two IoHwAb calls; the SWC body itself is a handful of branches and one byte write.

---

## 5. Error Handling

The LedActuator SWC has **no DET integration** — DET is a Basic Software service and SWCs do not directly invoke `Det_ReportError`. Instead the SWC propagates downstream failure via the `Std_ReturnType` return values from IoHwAb:

- `IoHwAb_GetSignal_Switch` returns `E_NOT_OK` ⇒ the LED is left at its previous level, `LedActuator_LastSwitchState` is not updated, and the cycle is skipped.
- `IoHwAb_SetSignal_LedOut` returns `E_NOT_OK` ⇒ `LedActuator_LastSwitchState` is not updated (we did not actually commit the new LED level).

In a future revision the SWC could surface failure through a status P-Port (Rte_Write); none is declared in the demo to keep the SWC R-Port-only.

Vendor-derived from SWC Template §4.5.2 (RunnableEntity semantics) and from the standard AUTOSAR `Std_ReturnType` convention. **Not SWS-traced** — there is no SWS for an application SWC (CAR-008 §0).

---

## 6. ASIL Claim & FFI Rationale

**Claim.** ASIL-B for the LedActuator SWC instance, per CAR-008 §5. The claim attaches to this SWC instance (an indicator/status-LED actuator), not to the SWC Template document, which is structural and ASIL-agnostic.

**Why ASIL-B is sufficient for the demo slice.**
1. The runnable's input domain is one boolean and its output domain is one boolean — exhaustively testable in two cycles.
2. The SWC carries no shared mutable state between runnables (it has only one runnable) and no inter-SWC writable data.
3. Downstream failures are surfaced via `Std_ReturnType`; the SWC fails safely (LED retains previous level) on read-side errors.

**Freedom From Interference (FFI) considerations.**
- **Spatial FFI.** The only writable state in the SWC is the file-scope `LedActuator_LastSwitchState` byte. It is written only by `LedActuator_MainFunction` and `LedActuator_Init`. The RTE serialises calls to `LedActuator_MainFunction` because `CanBeInvokedConcurrently = false` in the ARXML (§3) — non-reentrant by design.
- **Temporal FFI.** The runnable does not block, sleep, or yield. Worst-case execution time is bounded by the IoHwAb call costs plus a handful of branches — comfortably under the 100 ms task period (HLD-LEDACT-008).
- **Information / Control-flow FFI.** No callback registration, no interrupt, no shared queue. The runnable is a pure function of the switch level read from IoHwAb plus the previously latched state.
- **RTE serialisation.** Per SWC Template §4.5.2, the RTE schedules non-reentrant runnables on a single OS task per SWC instance, removing the need for ExclusiveArea declarations in this SWC.

---

## 7. Memory & Sectioning

| Symbol | Storage Class | Linker Section (expected) | Notes |
|---|---|---|---|
| `LedActuator_Init`, `LedActuator_MainFunction` | code | `.text` | Public API entry points; placed in flash. |
| `LedActuator_LastSwitchState` | data (static, zero-init) | `.bss` | One byte; cleared by C-runtime startup, defensively reasserted by `LedActuator_Init`. |
| (no rodata config) | rodata | `.rodata` | The SWC's configuration lives in the ARXML, not in C constants. There is no `LedActuator_ConfigType` table. |

There is no `.dio_shadow`-style vendor section; the SWC's single byte of state lives in the default `.bss` region. UC 4.4 overlap-check semantics from `Dio_HLD.md` §7 apply identically.

---

## 8. HLD Requirement Table

> **VENDOR-DERIVED — NOT SWS-TRACED.** Every row's `SWS Section` column reads `N/A — vendor SWC (see CAR-008 §<n>)` or cites a section of `AUTOSAR_CP_TPS_SoftwareComponentTemplate` R24-11. **No row points to an SWS section, because there is no SWS for an application SWC.**

| HLD_ID | Description | ASIL | Parent System Req | Verification Method | SWS Section |
|---|---|---|---|---|---|
| HLD-LEDACT-001 | The LedActuator SWC shall expose `LedActuator_Init(void)` to reset all SWC-internal state to a defined safe initial value (LED off, `LedActuator_LastSwitchState = FALSE`) before the first invocation of any runnable. | ASIL-B | SYS-LEDACT-100 | Test | N/A — vendor SWC (see CAR-008 §3); structural anchor SWC Template §4.5 |
| HLD-LEDACT-002 | The runnable `LedActuator_MainFunction` shall be bound in ARXML to exactly one `TimingEvent` with `period = 0.1 s` (100 ms) and shall be re-invoked every 100 ms by the RTE for the lifetime of the ECU. | ASIL-B | SYS-LEDACT-101 | Review | N/A — vendor SWC (see CAR-008 §2); structural anchor SWC Template §4.5.3 |
| HLD-LEDACT-003 | On every invocation, `LedActuator_MainFunction` shall read the current switch level by invoking `IoHwAb_GetSignal_Switch(boolean *out_state)` via the `P_LedHwAccess` ClientServer R-Port, and shall not proceed to the LED-drive step when the IoHwAb call returns `E_NOT_OK`. | ASIL-B | SYS-LEDACT-102 | Test | N/A — vendor SWC (see CAR-008 §4); structural anchor SWC Template §4.3 |
| HLD-LEDACT-004 | When the switch read in HLD-LEDACT-003 succeeds, `LedActuator_MainFunction` shall drive the LED level to match the read switch level by invoking `IoHwAb_SetSignal_LedOut(boolean state)` via the `P_LedHwAccess` ClientServer R-Port. | ASIL-B | SYS-LEDACT-103 | Test | N/A — vendor SWC (see CAR-008 §4); structural anchor SWC Template §4.3 |
| HLD-LEDACT-005 | `LedActuator_MainFunction` shall update the file-scope `LedActuator_LastSwitchState` to the most recently read switch level only when both IoHwAb calls in HLD-LEDACT-003 and HLD-LEDACT-004 have returned `E_OK`. | ASIL-B | SYS-LEDACT-104 | Inspection | N/A — vendor SWC (see CAR-008 §3); structural anchor SWC Template §4.5 |
| HLD-LEDACT-006 | The LedActuator SWC shall propagate IoHwAb failure upward by skipping the affected step (no LED write on read failure; no state latch on write failure) and shall not invoke any DET service; DET is a BSW concern. | ASIL-B | SYS-LEDACT-105 | Review | N/A — vendor SWC (see CAR-008 §3 closing note); structural anchor SWC Template §4.5.2 |
| HLD-LEDACT-007 | The LedActuator SWC's ARXML shall declare exactly two R-Ports — `P_LedControl` (SenderReceiverInterface, data element `LedState : boolean`) and `P_LedHwAccess` (ClientServerInterface, operations `SetSignal_LedOut` and `GetSignal_Switch`) — and no P-Ports. | ASIL-B | SYS-LEDACT-106 | Review | N/A — vendor SWC (see CAR-008 §3, §4); structural anchor SWC Template §4.3 |
| HLD-LEDACT-008 | The wall-clock execution time of one `LedActuator_MainFunction` invocation shall not exceed 1 ms on the target ECU, leaving at least 99 % of the 100 ms task period for other tasks. | ASIL-B | SYS-LEDACT-107 | Analysis | N/A — vendor SWC; structural anchor SWC Template §4.5.2 (RunnableEntity execution semantics) |

---

## 9. Open Issues / Demo Limitations

- **Vendor-derived, not SWS-traced.** Repeated from §0 and §3: there is NO AUTOSAR SWS for an application SWC. Every HLD-LEDACT-NNN requirement above is derived from the AUTOSAR Software Component Template (`AUTOSAR_CP_TPS_SoftwareComponentTemplate` R24-11). Any downstream artifact (LLD, test plan, traceability matrix, ASIL-gate report) MUST preserve this caveat.
- **ARXML not in workspace.** The `LedActuator.arxml` describing the structure in §3 is NOT delivered here. It would be emitted by the RTE configuration tool and is conceptually present but invisible. Only the C source representing the runnable is in this workspace.
- **IoHwAb prototypes assumed.** The HLD assumes the IoHwAb agent (running in parallel) delivers exactly `Std_ReturnType IoHwAb_SetSignal_LedOut(boolean state)` and `Std_ReturnType IoHwAb_GetSignal_Switch(boolean *out_state)`. If CAR-007 (the IoHwAb reference) lands later and the prototypes differ, this HLD will need a v1.1 to re-align HLD-LEDACT-003 and HLD-LEDACT-004.
- **`P_LedControl` not consumed in demo build.** The R-Port is declared in the ARXML view (§3) so a future upstream indicator-logic SWC can drop in unchanged, but the demo runnable bypasses `P_LedControl` and reads the switch directly. HLD-LEDACT-007 still mandates the port declaration; HLD-LEDACT-003 / -004 deliberately do NOT reference `P_LedControl`.
- **No RTE.h in this workspace.** Per Tier 2 demo scope, the RTE-generated glue (`Rte_Read_*`, `Rte_Call_*`) is invisible. The C source calls IoHwAb directly. A production version would route through `Rte_Call_P_LedHwAccess_*`.
- **No real I/O.** IoHwAb itself is stubbed (CAR-007 deliverable). The demo does not light an actual LED.

---

## 10. Traceability Notes

Downstream traceability is realised by the **S1N1 LLD generator**, which consumes `LedActuator.c` / `LedActuator.h` plus this HLD and emits `LedActuator_TEMP_LLD.csv`. Every LLD row produced by S1N1 must populate the `HLD_PARENT` column with one of the `HLD-LEDACT-NNN` IDs from §8 above (with `REVIEW_NEEDED` as the recorded fallback when no match exists).

Expected coarse mapping (informative — S1N1 produces the binding mapping):

| Source element (in `LedActuator.c` / `.h`) | Likely HLD parent |
|---|---|
| `void LedActuator_Init(void)` | HLD-LEDACT-001 |
| `void LedActuator_MainFunction(void)` | HLD-LEDACT-002, HLD-LEDACT-003, HLD-LEDACT-004, HLD-LEDACT-005, HLD-LEDACT-006, HLD-LEDACT-008 |
| `static boolean LedActuator_LastSwitchState` | HLD-LEDACT-005 |
| Call `IoHwAb_GetSignal_Switch(&sw_state)` | HLD-LEDACT-003, HLD-LEDACT-006 |
| Call `IoHwAb_SetSignal_LedOut(sw_state)` | HLD-LEDACT-004, HLD-LEDACT-006 |
| ARXML port `P_LedControl` (conceptual) | HLD-LEDACT-007 |
| ARXML port `P_LedHwAccess` (conceptual) | HLD-LEDACT-007 |

Upstream traceability is recorded in §8's `Parent System Req` column using demo-synthetic IDs `SYS-LEDACT-100` through `SYS-LEDACT-107`. These IDs are placeholders so that any future linkage to a real system-level requirements baseline preserves row identity.

---

End of HLD.
