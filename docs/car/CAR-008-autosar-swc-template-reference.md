# CAR-008: AUTOSAR Software Component Template (Demo Reference for LedActuator SWC)

- **Status:** Accepted
- **Source type:** AUTOSAR Foundation Template — defines SWC structure constraints, NOT a SWS for any specific SWC
- **Fetched:** 2026-05-17
- **Reference tier:** PRIMARY (template constraints feed the demo SWC description)
- **Role for CIPHER:** Anchors the demo LedActuator SWC artifact against AUTOSAR's vendor-SWC structural rules so the demo's HLD/LLD/traceability matrix can cite a real, downloadable AUTOSAR document.

---

## 0. Document Frontmatter

| Field | Value |
|---|---|
| Document Title | Software Component Template |
| Document ID | AUTOSAR_CP_TPS_SoftwareComponentTemplate |
| AUTOSAR Release | R24-11 (published under Classic Platform; the SWC Template is the AUTOSAR-wide structural specification for application SWCs) |
| Companion Document | AUTOSAR_CP_TPS_BSWModuleDescriptionTemplate (R24-11) — analogous template for BSW modules; cross-referenced for terminology only |
| ASIL Claim (this CAR) | ASIL-B (claim attaches to the LedActuator SWC instance, not to the template document) |
| Source URL (SWC Template) | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_TPS_SoftwareComponentTemplate.pdf |
| Source URL (BSW MDT, cross-ref) | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_TPS_BSWModuleDescriptionTemplate.pdf |
| Fetched date | 2026-05-17 |
| **WARNING — Template vs SWS** | **There is NO AUTOSAR SWS for an application SWC.** AUTOSAR publishes the **Software Component Template**, which defines the structural constraints every vendor-authored SWC must satisfy. The demo's LedActuator SWC is a vendor SWC described AGAINST this template — it is NOT a standardised AUTOSAR module like Dio (CAR-004). Do not cite this CAR as "the SWS for LedActuator"; cite it as "structural template the LedActuator SWC conforms to". |

---

## 1. SWC Template Constraint List

The Software Component Template (`AUTOSAR_CP_TPS_SoftwareComponentTemplate`, R24-11) imposes the following structural rules on every vendor-authored application SWC. Section numbers below reference the R24-11 template document and MUST be re-verified against the downloaded PDF before the demo HLD is frozen.

- **Must declare exactly one component type** — typically `AtomicSoftwareComponentType` for a leaf SWC; `CompositionSwComponentType` is used to aggregate atomic SWCs (template §4.2 "Component Type").
- **Must declare at least one `InternalBehavior`** (specifically `SwcInternalBehavior` for atomic SWCs) attached to the component type (template §4.5 "Internal Behavior").
- **Must declare at least one `RunnableEntity`** inside the `InternalBehavior`; the runnable is the unit of executable code the RTE schedules (template §4.5.2 "RunnableEntity").
- **Each `RunnableEntity` must be triggered by at least one `RTEEvent`** — see §2 of this CAR for the allowed event subtypes (template §4.5.3 "RTEEvent").
- **Port prototypes must reference a `PortInterface`** of one of: `SenderReceiverInterface`, `ClientServerInterface`, `ModeSwitchInterface`, `NvDataInterface`, `ParameterInterface`, `TriggerInterface` (template §4.3 "Ports and Port Interfaces").
- **Data-element types must be declared in the AUTOSAR data type system** — `ApplicationDataType` / `ImplementationDataType`, with a `DataTypeMappingSet` linking them (template §4.6 "Data Types").
- **Optional: `ExclusiveArea`** must be declared on the `InternalBehavior` when two or more runnables share mutable state and need RTE-managed serialisation (template §4.5.4 "ExclusiveArea"). The LedActuator demo SWC declares none — single runnable, no shared state.
- **All artifacts live in a single ARXML namespace** rooted at the SWC's `AR-PACKAGE` (template §3 "Document Structure" and the Generic Structure Template, `AUTOSAR_FO_TPS_GenericStructureTemplate`).

---

## 2. Runnable Triggering Modes

The SWC Template §4.5.3 enumerates the `RTEEvent` subtypes a `RunnableEntity` may be bound to. The demo SWC uses exactly one.

| RTEEvent subtype | Trigger semantics | Used in demo? |
|---|---|---|
| `TimingEvent` | Periodic trigger; RTE fires the runnable every `period` seconds | **Yes — 100 ms** |
| `DataReceivedEvent` | Fires when a sender-receiver R-Port receives a fresh data element | No |
| `OperationInvokedEvent` | Fires when a client-server P-Port operation is invoked (server side) | No |
| `InitEvent` | One-shot trigger fired by the RTE at SWC startup | No |
| `ModeSwitchEvent` / `BackgroundEvent` / `DataReceiveErrorEvent` | Other allowed subtypes per template §4.5.3 | No |

**Demo binding:** `LedActuator_MainFunction` is bound to a single `TimingEvent` with `period = 0.1 s` (100 ms). This matches the cyclic-task pattern integrators expect for indicator actuator SWCs and keeps the demo trace deterministic.

---

## 3. Demo SWC Description — LedActuator

The demo describes a single vendor-authored SWC, `LedActuator`, conforming to the SWC Template constraints listed in §1.

- **Component Type:** `AtomicSoftwareComponentType` — short name `LedActuator`.
- **InternalBehavior:** `LedActuator_IB` — single `SwcInternalBehavior` attached to `LedActuator`.
- **Runnable:** `LedActuator_MainFunction`
  - Trigger: `TimingEvent`, `period = 0.1 s` (100 ms).
  - Symbol: `LedActuator_MainFunction` (the generated RTE entry point invoked by the OS task).
  - Body summary: reads the latched `LedState` from `P_LedControl`, then invokes `IoHwAb_SetSignal_LedOut(state)` via `P_LedHwAccess`.
- **Port `P_LedControl`:**
  - Direction: R-Port (receiver).
  - Interface kind: `SenderReceiverInterface`.
  - Data element: `LedState` of type `boolean` (mapped from `ApplicationDataType` `LedState_T` to `ImplementationDataType` `boolean`).
  - Conceptual sender: an upstream indicator-logic SWC (out of demo scope; declared as "external" so the demo SWC remains self-contained).
- **Port `P_LedHwAccess`:**
  - Direction: R-Port (client side of a client-server contract).
  - Interface kind: `ClientServerInterface`.
  - Operation referenced: `SetSignal_LedOut(state : boolean)`.
  - Server: the IoHwAb module (CAR-005 / IoHwAb SWS); the call is mediated by the RTE per the SWC Template §4.3.
- **Calls at end of MainFunction:** exactly one — `IoHwAb_SetSignal_LedOut(state)`. No other RTE writes, no DET reports from the SWC itself (DET is a BSW concern).
- **ExclusiveAreas:** none (single runnable, no shared mutable state).

---

## 4. Port Interface Contracts

| Port | Direction | Interface kind | Element(s) | Type |
|---|---|---|---|---|
| `P_LedControl` | R-Port (receiver) | SenderReceiverInterface | `LedState` (data element) | `boolean` (ImplementationDataType) |
| `P_LedHwAccess` | R-Port (client) | ClientServerInterface | `SetSignal_LedOut(state)` (operation) | `state : boolean` (in-argument) |

Both ports are R-Ports on the LedActuator SWC: the SWC consumes a logical LED command from upstream and consumes the IoHwAb service to drive the physical pin. No P-Ports are declared on LedActuator in the demo.

---

## 5. ASIL Claim

- **Claim:** ASIL-B.
- **Rationale:** ASIL-B is the typical safety classification for indicator / status-LED actuator SWCs in passenger vehicle E/E architectures (e.g., a warning-lamp driver where loss of indication is a safety-relevant failure but is itself mitigated by redundant diagnostics). The claim attaches to the **LedActuator SWC instance**, not to the SWC Template document — the template itself is structural and ASIL-agnostic.
- **Gate string for the demo ASIL-gate report:** `ASIL-B per CAR-008 §5 (LedActuator vendor SWC, conforming to AUTOSAR_CP_TPS_SoftwareComponentTemplate R24-11)`.
- **Integrator note:** Final ASIL allocation depends on the integrator's item-definition and HARA; this CAR records only the demo's claim target.

---

## 6. Demo Scope Hint

To keep the CIPHER demo trial focused and under the 10-minute wall-clock budget (cf. CAR-004 §4), the demo exposes **only the LedActuator SWC** — no upstream indicator-logic SWC, no composition SWC, no second runnable. The chain the audience sees is:

```
TimingEvent (100 ms)
   -> LedActuator_MainFunction (RunnableEntity)
        -> read P_LedControl.LedState (RTE_Read, SenderReceiverInterface)
        -> call P_LedHwAccess.SetSignal_LedOut(state) (RTE_Call, ClientServerInterface)
             -> IoHwAb_SetSignal_LedOut(state) (BSW service, out of SWC scope)
```

This single chain exercises three SWC-Template constructs (component type, internal behavior, port prototype) plus one RTE-event subtype (TimingEvent) — enough surface area for the demo's HLD/LLD/test/traceability stages to each have a non-trivial artifact, without dragging in compositions, multiple runnables, or mode management.

---

## 7. Source

- **Primary URL — Software Component Template (R24-11):** https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_TPS_SoftwareComponentTemplate.pdf
  - One-line note: the structural template every vendor application SWC must conform to; defines component types, internal behavior, runnables, ports, data types, and exclusive areas.
- **Cross-reference URL — BSW Module Description Template (R24-11):** https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_TPS_BSWModuleDescriptionTemplate.pdf
  - One-line note: the analogous structural template for BSW modules (ICC3 / ICC2 / library); cited here only so the SWC-vs-BSW distinction in the demo HLD has a downloadable anchor — the LedActuator SWC is NOT a BSW module and does NOT conform to this template.
- **Release tag used:** R24-11 (latest stable AUTOSAR release as of 2026-05-17).
- **Document IDs:** `AUTOSAR_CP_TPS_SoftwareComponentTemplate`, `AUTOSAR_CP_TPS_BSWModuleDescriptionTemplate`.

**WARNING (repeated from §0):** There is **no AUTOSAR SWS for an application SWC**. The LedActuator described in this CAR is a **vendor-authored SWC documented against the SWC Template** — it is not a standardised AUTOSAR module. Any downstream demo artifact (HLD, LLD, test plan, traceability matrix, ASIL-gate report) that cites CAR-008 MUST preserve this distinction: cite "conformance to AUTOSAR_CP_TPS_SoftwareComponentTemplate R24-11", never "compliance with the LedActuator SWS".

**Limitation flag:** PDF binaries were NOT parsed inside this agent. Section numbers in §1 and §2 are quoted from the public AUTOSAR R24-11 template structure and the AUTOSAR methodology document; the CIPHER team should download both PDFs above and verify section anchors before the demo HLD is frozen.
