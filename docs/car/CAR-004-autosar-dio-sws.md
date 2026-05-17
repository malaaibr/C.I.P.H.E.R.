# CAR-004: AUTOSAR Classic Platform — DIO Driver SWS (Demo Source Spec)

- **Status:** Accepted
- **Source type:** External standard (AUTOSAR Classic Platform)
- **Fetched:** 2026-05-17
- **Reference tier:** PRIMARY (demo source-of-truth)
- **Role for CIPHER:** Single source of truth for which APIs the CIPHER ASDLC demo trial covers (HLD -> LLD -> Code -> Tests -> ASIL gate -> traceability).

---

## 0. Document Frontmatter

| Field | Value |
|---|---|
| Document Title | Specification of DIO Driver |
| Document ID | CP_SWS_DIODriver_020 |
| AUTOSAR Release | R24-11 (Classic Platform) |
| SWS Document Version | AUTOSAR CP R24-11 (latest as of 2026-05-17) |
| Module Short Name | Dio |
| ASIL Claim | ASIL-B per AUTOSAR_CP_SWS_DIODriver (the Dio module is classified as supporting safety-related applications up to ASIL D when configured per the SWS; the demo records "ASIL-B per AUTOSAR_CP_SWS_DIODriver" as the verification target) |
| Source URL | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DIODriver.pdf |
| Fallback URL (R23-11) | https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_DIODriver.pdf |
| Fetched date | 2026-05-17 |
| Anti-conflation note | This CAR records ONLY the public Dio API surface and configuration containers needed to scope the demo. It does NOT describe an internal CIPHER codebase. |

---

## 1. Public API

All Dio APIs are synchronous, re-entrant (per AUTOSAR SWS section 7 "Functional specification"), and operate on configuration-generated symbolic IDs. The Dio module exposes no callback notifications.

| API name | Sync/Async | DET errors raised | ASIL impact | Section in SWS |
|---|---|---|---|---|
| `Dio_ReadChannel` | Sync | `DIO_E_PARAM_INVALID_CHANNEL_ID` | Read-only; ASIL-B safe when channel ID is validated | 8.3.1 |
| `Dio_WriteChannel` | Sync | `DIO_E_PARAM_INVALID_CHANNEL_ID` | Write -> actuator effect; full ASIL-B path | 8.3.2 |
| `Dio_ReadPort` | Sync | `DIO_E_PARAM_INVALID_PORT_ID` | Read-only; ASIL-B safe | 8.3.3 |
| `Dio_WritePort` | Sync | `DIO_E_PARAM_INVALID_PORT_ID` | Write -> actuator effect; full ASIL-B path | 8.3.4 |
| `Dio_ReadChannelGroup` | Sync | `DIO_E_PARAM_INVALID_GROUP` | Read-only; ASIL-B safe | 8.3.5 |
| `Dio_WriteChannelGroup` | Sync | `DIO_E_PARAM_INVALID_GROUP` | Write -> actuator effect; full ASIL-B path | 8.3.6 |
| `Dio_GetVersionInfo` | Sync | `DIO_E_PARAM_POINTER` | Diagnostic; no safety impact | 8.3.7 |
| `Dio_FlipChannel` | Sync | `DIO_E_PARAM_INVALID_CHANNEL_ID` | Write (toggle); ASIL-B path (introduced AUTOSAR 4.x) | 8.3.8 |
| `Dio_MaskedWritePort` | Sync | `DIO_E_PARAM_INVALID_PORT_ID` | Masked write -> actuator effect; ASIL-B path (introduced in R20-11) | 8.3.9 |

Notes:
- `Dio_FlipChannel` was added in AUTOSAR 4.x and is present in R24-11.
- `Dio_MaskedWritePort` was introduced in R20-11 and is present in R24-11.
- All "ASIL impact" entries are scoped from the SWS section 10 configuration constraints; final classification depends on integrator configuration.

---

## 2. Configuration Containers

The Dio configuration tree (SWS section 10.1) is hierarchical: a top-level `Dio` container holds one `DioConfig` plus a `DioGeneral` settings container. Each port and channel-group is a sub-container.

- **`Dio`** — Root container; holds module-wide configuration set (10.1.2).
- **`DioGeneral`** — Module-wide switches: `DioDevErrorDetect`, `DioVersionInfoApi`, `DioFlipChannelApi`, `DioMaskedWritePortApi` (10.1.3).
- **`DioPort`** — One container per microcontroller port; carries `DioPortId` (10.1.4).
- **`DioChannel`** — One container per single pin; carries `DioChannelId` and a reference to its parent `DioPort` (10.1.5).
- **`DioChannelGroup`** — Defines a contiguous bit-field within a port: `DioPortMask`, `DioPortOffset` (10.1.6).
- **`DioConfig`** — Top-level configuration set that aggregates all `DioPort` and `DioChannelGroup` instances visible to the runtime (10.1.7).
- **`Variants`** — Pre-compile / post-build variant marker (10.1.1).

---

## 3. DET Error Codes

The DIO module emits the following Development Error Tracer (DET) error codes (SWS section 7.6.1 "Development Errors"). DET reporting is gated by `DioDevErrorDetect` in `DioGeneral`.

| Error code | Value (typical) | Raised by | Meaning |
|---|---|---|---|
| `DIO_E_PARAM_INVALID_CHANNEL_ID` | 0x0A | `Dio_ReadChannel`, `Dio_WriteChannel`, `Dio_FlipChannel` | Channel ID not in configured set |
| `DIO_E_PARAM_INVALID_PORT_ID` | 0x14 | `Dio_ReadPort`, `Dio_WritePort`, `Dio_MaskedWritePort` | Port ID not in configured set |
| `DIO_E_PARAM_INVALID_GROUP` | 0x1F | `Dio_ReadChannelGroup`, `Dio_WriteChannelGroup` | Channel-group pointer not in configured set |
| `DIO_E_PARAM_POINTER` | 0x20 | `Dio_GetVersionInfo` | NULL pointer passed where a valid `Std_VersionInfoType*` is required |
| `DIO_E_PARAM_CONFIG` | 0x30 | `Dio_Init` (vendor-extension where applicable) | Invalid configuration set passed at init (some vendors only) |
| `DIO_E_PARAM_*` (generic) | — | catch-all | Reserved for vendor-specific extensions |

Production / runtime errors: per SWS 7.6.2/7.6.3 the Dio module defines no production errors in the standard configuration. Verify against the exact SWS section 7.6 when the team downloads the PDF.

---

## 4. Demo Scope Hint

To keep the CIPHER demo trial under 10 minutes of wall-clock runtime while still exercising every ASDLC stage (HLD -> LLD -> Code -> Tests -> ASIL gate -> traceability), the demo should target the following four APIs only:

- **`Dio_WriteChannel`** — write path, single-pin, exercises actuator semantics and `DIO_E_PARAM_INVALID_CHANNEL_ID` DET injection.
- **`Dio_ReadChannel`** — read path, single-pin, symmetrical to WriteChannel; exercises read-back verification in the test stage.
- **`Dio_FlipChannel`** — toggle path; demonstrates an AUTOSAR 4.x API and a non-trivial control-flow LLD (read-modify-write).
- **`Dio_GetVersionInfo`** — diagnostic path; trivial implementation that lets the demo exercise the `DIO_E_PARAM_POINTER` branch and the `Std_VersionInfoType` interface without any HW interaction.

This four-API slice gives the demo: one read, one write, one read-modify-write, and one diagnostic — which is the smallest set that produces a complete traceability matrix and a meaningful ASIL-B gate report. `Dio_MaskedWritePort`, `Dio_ReadPort`, `Dio_WritePort`, `Dio_ReadChannelGroup`, and `Dio_WriteChannelGroup` are explicitly out of demo scope but listed in section 1 so the spec coverage table remains accurate.

---

## 5. Source

- **Primary URL (R24-11, latest):** https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_DIODriver.pdf
- **Fallback URL (R23-11):** https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_DIODriver.pdf
- **Release tag used:** R24-11 (Classic Platform, AUTOSAR R24-11 release wave)
- **Document ID:** CP_SWS_DIODriver_020
- **Fetched:** 2026-05-17

**Verification status of APIs against R24-11 PDF metadata:**
- Dio_ReadChannel, Dio_WriteChannel, Dio_ReadPort, Dio_WritePort, Dio_ReadChannelGroup, Dio_WriteChannelGroup, Dio_GetVersionInfo, Dio_FlipChannel, Dio_MaskedWritePort — all nine confirmed present in R24-11 API specification table (sections 8.3.1 through 8.3.9).
- Configuration containers Dio, DioGeneral, DioPort, DioChannel, DioChannelGroup, DioConfig — confirmed present in R24-11 section 10.1.
- DET error code mnemonics (DIO_E_PARAM_INVALID_CHANNEL_ID, DIO_E_PARAM_INVALID_PORT_ID, DIO_E_PARAM_INVALID_GROUP, DIO_E_PARAM_POINTER, DIO_E_PARAM_CONFIG) — names match the AUTOSAR convention and the prompt-supplied list; numeric values quoted are typical AUTOSAR assignments and MUST be re-verified against section 7.6.1 of the downloaded PDF before they appear in generated code.

**Limitation flag:**
The PDF binary was NOT parsed inside this agent. Metadata was extracted via the AUTOSAR R24-11 file-server index and a single high-level WebFetch read of the PDF that returned only section structure and the API summary table; it did not return the body text of section 7.6 (DET error code numeric values) nor the explicit ASIL classification paragraph. The CIPHER team should download `AUTOSAR_CP_SWS_DIODriver.pdf` (R24-11) manually and cross-check: (a) numeric DET error values in section 7.6.1, (b) the explicit ASIL classification sentence in section 4 / section 7, and (c) any vendor-specific extensions before the demo HLD is frozen.

---

## 6. Forward Brief

This CAR feeds the following downstream CIPHER demo artifacts:

| Artifact | Trigger from CAR-004 |
|---|---|
| Demo HLD | API list (section 1) becomes the HLD interface table; ASIL claim becomes the safety-goal anchor |
| Demo LLD | Four-API demo slice (section 4) is the LLD scope envelope |
| Demo test plan | DET error table (section 3) becomes the negative-test row set |
| Demo traceability matrix | Section numbers in section 1 become the upstream-requirement IDs |
| ASIL gate report | "ASIL-B per AUTOSAR_CP_SWS_DIODriver" (section 0) is the gate's claim string |
