# CAR-007: AUTOSAR Classic Platform — I/O Hardware Abstraction (IoHwAb) Reference

- **Status:** Accepted (synthesized reference — see warning below)
- **Source type:** Explanatory / Layered SWA reference — **NO single normative SWS exists for IoHwAb**
- **Fetched:** 2026-05-17
- **Reference tier:** SECONDARY (explanatory anchor; the demo IoHwAb API surface is INVENTED, not extracted)
- **Role for CIPHER:** Defines the four invented `IoHwAb_*` symbols the demo uses on top of the Dio APIs covered by CAR-004, and records the AUTOSAR explanatory documents that justify the layering.

---

## 0. Document Frontmatter

| Field | Value |
|---|---|
| Document Title | I/O Hardware Abstraction — demo reference (synthesized) |
| Source type | Explanatory / Layered SWA reference — **NO single SWS exists for IoHwAb as a normative module** |
| AUTOSAR Release | R24-11 (Classic Platform) cross-checked against R23-11 |
| Primary explanatory URL | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf |
| IoHwAb guideline URL (NOT a normative SWS) | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf |
| Fallback URL (R23-11 layered SWA) | https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf |
| Fallback URL (R23-11 IoHwAb guideline) | https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf |
| Document IDs | Layered SWA = Document ID 53; IoHwAb guideline is filed under the SWS folder but is explicitly informative |
| Fetched date | 2026-05-17 |
| **NO-SWS WARNING (repeated)** | **No single normative SWS exists for IoHwAb. The PDF named `AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` self-describes (per WebSearch summary, 2026-05-17) as "not intended to standardize this module ... but instead to be a guideline for the implementation of its functional interfaces". IoHwAb is realized vendor-by-vendor (Vector MICROSAR, EB tresos, etc.). The API surface in this CAR is therefore SYNTHESIZED for the CIPHER demo.** |

---

## 1. Architectural Role

The I/O Hardware Abstraction (IoHwAb) sits in the ECU Abstraction Layer of the AUTOSAR Classic Platform, directly above the Microcontroller Abstraction Layer (MCAL) and directly below the Runtime Environment (RTE) and the application SW-Cs. Its job is to translate **ECU-level symbolic signal names** (e.g. `LedOut`, `Switch`) into **MCAL driver channel IDs** (e.g. `Dio_ChannelType DIO_CHANNEL_LED1`). It hides which physical pin / port / microcontroller actually realizes a given logical signal, so an application or RTE port can be re-wired at the IoHwAb level without touching application code. IoHwAb consumes Dio, Port, Adc, Pwm, Icu, Ocu, and Gpt drivers as needed; for the CIPHER demo only the Dio path is in scope.

---

## 2. Why There Is No Single SWS

Per `AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf` (R24-11, Document ID 53), the ECU Abstraction Layer is **explanatory** for the IoHwAb sub-block. The companion PDF `AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` is filed in the SWS folder but explicitly states it is **a guideline, not a standardization** of the module — it does not enumerate a fixed API list, error codes, or configuration containers the way `AUTOSAR_CP_SWS_DIODriver.pdf` does for Dio. As a result, every Tier-1 / Tier-2 supplier (Vector MICROSAR, EB tresos, ETAS RTA-BSW, Mentor VSx, etc.) ships its own IoHwAb realization with proprietary symbol naming. **Repeat:** any IoHwAb API surface — including the four symbols listed below — is *synthesized*, not extracted from a normative AUTOSAR document.

---

## 3. Demo API Surface (Invented, Consistent with Layered SWA)

The four symbols below are **invented for the CIPHER demo**. They are named and shaped to be consistent with the layering described in `AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf` and with the Dio APIs CAR-004 already locked.

| API | Sync/Async | Calls downward into | Purpose |
|---|---|---|---|
| `IoHwAb_Init` | Sync | `Port_Init` (via BSW init order) | One-time init of the IoHwAb signal-to-channel map; runs before any RTE I/O port read/write |
| `IoHwAb_GetSignal_LedOut` | Sync | `Dio_ReadChannel(DIO_CHANNEL_LED1)` | Returns the latched LED output state for read-back verification |
| `IoHwAb_SetSignal_LedOut` | Sync | `Dio_WriteChannel(DIO_CHANNEL_LED1, ...)` | Drives the LED actuator |
| `IoHwAb_GetSignal_Switch` | Sync | `Dio_ReadChannel(DIO_CHANNEL_SW1)` | Reads the input switch state |

All four are synchronous and re-entrant by inheritance from the underlying Dio APIs (CAR-004 §1). None of them define new DET error codes; any DET reporting is forwarded from the Dio layer.

---

## 4. Symbolic-to-Physical Mapping

| Signal symbol | Dio channel ID | Direction |
|---|---|---|
| `LedOut` | `DIO_CHANNEL_LED1 = 0x12` | Output (actuator) |
| `Switch` | `DIO_CHANNEL_SW1 = 0x05` | Input (sensor) |

**Flag:** the CIPHER demo's current `generated_artifacts/dio_demo_workspace/Dio.h` does **not** yet define the symbols `DIO_CHANNEL_LED1` or `DIO_CHANNEL_SW1` (verified 2026-05-17 by Grep — only the `Dio_*Channel(Dio_ChannelType ChannelId, ...)` prototypes are present). The integers `0x12` and `0x05` are therefore the values the demo's HLD/LLD must inject into `Dio.h` (or a generated `Dio_Cfg.h`) when CAR-007 is realized. This must be tracked as an open item in the demo backlog.

---

## 5. ASIL Claim

IoHwAb has no normative ASIL classification of its own (no SWS, see §0 and §2). The demo claim is **ASIL-B by inheritance** from the consumed Dio channels (CAR-004 §0, "ASIL-B per AUTOSAR_CP_SWS_DIODriver"). Any IoHwAb function in the demo is treated as a transparent pass-through that neither raises nor lowers the ASIL of the underlying Dio call. Freedom-from-interference between the four IoHwAb symbols is guaranteed structurally (each touches a distinct Dio channel ID).

---

## 6. Demo Scope Hint

The CIPHER demo exposes only the four APIs listed in §3 — `IoHwAb_Init`, `IoHwAb_GetSignal_LedOut`, `IoHwAb_SetSignal_LedOut`, `IoHwAb_GetSignal_Switch`. No port-level, group-level, ADC, PWM, or ICU IoHwAb wrappers are in scope. This matches the four-Dio-API slice locked by CAR-004 §4 (`Dio_WriteChannel`, `Dio_ReadChannel`, `Dio_FlipChannel`, `Dio_GetVersionInfo`) with the deliberate note that the demo's `IoHwAb_*` slice does NOT consume `Dio_FlipChannel` or `Dio_GetVersionInfo` — those two Dio APIs remain reachable directly from the demo's test harness, not via IoHwAb.

---

## 7. Source

- **`AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf` (R24-11)** — https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf — Document ID 53. Contributes the architectural placement of IoHwAb in the ECU Abstraction Layer, used in §1 and §2.
- **`AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` (R24-11)** — https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf — Despite the `SWS_` filename prefix, this document self-describes as a guideline, NOT a normative module specification. Contributes the rationale in §2 and the high-level idea of "signal-symbol to driver-channel" mapping used in §3 and §4.
- **`AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf` (R23-11 fallback)** — https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_EXP_LayeredSoftwareArchitecture.pdf — Identical layered diagram; held as fallback in case R24-11 link rots.
- **`AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf` (R23-11 fallback)** — https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_IOHardwareAbstraction.pdf — R23-11 IoHwAb guideline; same caveat applies.
- **CAR-004 (internal)** — `docs/car/CAR-004-autosar-dio-sws.md` — Source of the Dio API list and ASIL-B claim that IoHwAb inherits.

**NO-SWS caveat (final repeat):** Every API name, signature, direction, and channel value in this CAR-007 is **SYNTHESIZED for the CIPHER demo**. No row in §3 or §4 is a verbatim extract from any AUTOSAR normative SWS, because none exists for IoHwAb. Reviewers checking trace fidelity should treat CAR-007 as a *demo design artifact justified by* the explanatory documents above, not as an external standard extract. Only CAR-004 (Dio) is a true external-standard extract.
