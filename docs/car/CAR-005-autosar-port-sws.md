---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CAR-005: AUTOSAR Classic Platform — Port Driver SWS (Demo Source Spec)

- **Status:** Accepted
- **Source type:** External standard (AUTOSAR Classic Platform)
- **Fetched:** 2026-05-17
- **Reference tier:** PRIMARY (demo source-of-truth)
- **Role for CIPHER:** Companion to CAR-004; scopes the Port Driver API surface for the CIPHER ASDLC demo trial expansion (HLD -> LLD -> Code -> Tests -> ASIL gate -> traceability). Demo runtime path is intentionally init-only (see section 4).

---

## 0. Document Frontmatter

| Field | Value |
|---|---|
| Document Title | Specification of Port Driver |
| Document ID | CP_SWS_PortDriver_040 |
| AUTOSAR Release | R24-11 (Classic Platform) |
| SWS Document Version | AUTOSAR CP R24-11 (latest as of 2026-05-17) |
| Module Short Name | Port |
| ASIL Claim | ASIL-B per AUTOSAR_CP_SWS_PortDriver (the Port module is classified as supporting safety-related applications up to ASIL D when configured per the SWS; the demo records "ASIL-B per AUTOSAR_CP_SWS_PortDriver" as the verification target — FLAGGED: explicit ASIL classification sentence not retrievable via WebFetch, needs manual cross-check in section 4 / section 7 of the PDF) |
| Source URL | https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_PortDriver.pdf |
| Fallback URL (R23-11) | https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_PortDriver.pdf |
| Fetched date | 2026-05-17 |
| Anti-conflation note | This CAR records ONLY the public Port API surface and configuration containers needed to scope the demo expansion. It does NOT describe an internal CIPHER codebase. |

---

## 1. Public API

All Port APIs are synchronous (per AUTOSAR SWS section 7 "Functional specification"). `Port_Init` is non-re-entrant; `Port_SetPinDirection`, `Port_SetPinMode`, `Port_RefreshPortDirection`, and `Port_GetVersionInfo` are re-entrant per the SWS. Two APIs are gated by configuration switches (`PortSetPinDirectionApi`, `PortSetPinModeApi`) in `PortGeneral`.

| API name | Sync/Async | DET errors raised | ASIL impact | Section in SWS |
|---|---|---|---|---|
| `Port_Init` | Sync | `PORT_E_INIT_FAILED`, `PORT_E_PARAM_POINTER` | One-shot init -> configures pin direction/mode; full ASIL-B path | 8.3.1 |
| `Port_SetPinDirection` | Sync | `PORT_E_PARAM_PIN`, `PORT_E_DIRECTION_UNCHANGEABLE`, `PORT_E_UNINIT` | Runtime direction change -> hardware effect; ASIL-B path (only present when `PortSetPinDirectionApi == TRUE`) | 8.3.2 |
| `Port_RefreshPortDirection` | Sync | `PORT_E_UNINIT` | Re-applies configured directions; ASIL-B path (typically used for safety re-anchoring) | 8.3.3 |
| `Port_GetVersionInfo` | Sync | `PORT_E_PARAM_POINTER` | Diagnostic; no safety impact | 8.3.4 |
| `Port_SetPinMode` | Sync | `PORT_E_PARAM_PIN`, `PORT_E_PARAM_INVALID_MODE`, `PORT_E_MODE_UNCHANGEABLE`, `PORT_E_UNINIT` | Runtime mode change -> hardware effect; ASIL-B path (only present when `PortSetPinModeApi == TRUE`) | 8.3.5 |

Notes:
- `Port_SetPinDirection` is conditionally compiled in based on `PortSetPinDirectionApi`.
- `Port_SetPinMode` is conditionally compiled in based on `PortSetPinModeApi`.
- Section numbers (8.3.1–8.3.5) follow the SWS API-specification ordering observed in R24-11; FLAGGED for manual cross-check against the PDF section index.

---

## 2. Configuration Containers

The Port configuration tree (SWS section 10.1) is hierarchical: a top-level `Port` container holds the `PortGeneral` settings container plus the `PortConfigSet` configuration set, which aggregates `PortContainer` instances each holding `PortPin` definitions.

- **`Port`** — Root container; holds module-wide configuration (10.1.1).
- **`PortGeneral`** — Module-wide switches: `PortDevErrorDetect`, `PortVersionInfoApi`, `PortSetPinDirectionApi`, `PortSetPinModeApi` (10.1.2).
- **`PortContainer`** — One container per microcontroller port; groups the pin definitions belonging to that physical port (10.1.3).
- **`PortPin`** — One container per single pin; carries `PortPinId`, `PortPinDirection`, `PortPinDirectionChangeable`, `PortPinInitialMode`, `PortPinMode`, `PortPinModeChangeable`, `PortPinLevelValue` (10.1.4).
- **`PortConfigSet`** — Top-level configuration set that aggregates every `PortContainer` visible to the runtime (10.1.5).

---

## 3. DET Error Codes

The Port module emits the following Development Error Tracer (DET) error codes (SWS section 7.6.1 "Development Errors"). DET reporting is gated by `PortDevErrorDetect` in `PortGeneral`.

| Error code | Value (typical) | Raised by | Meaning |
|---|---|---|---|
| `PORT_E_PARAM_PIN` | 0x0A (FLAGGED) | `Port_SetPinDirection`, `Port_SetPinMode` | Pin ID not in configured set |
| `PORT_E_DIRECTION_UNCHANGEABLE` | 0x0B (FLAGGED) | `Port_SetPinDirection` | Pin's `PortPinDirectionChangeable == FALSE` at runtime |
| `PORT_E_INIT_FAILED` | 0x0C (FLAGGED) | `Port_Init` | Invalid configuration set passed at init |
| `PORT_E_PARAM_INVALID_MODE` | 0x0D (FLAGGED) | `Port_SetPinMode` | Mode value not in the pin's configured allowed-modes set |
| `PORT_E_MODE_UNCHANGEABLE` | 0x0E (FLAGGED) | `Port_SetPinMode` | Pin's `PortPinModeChangeable == FALSE` at runtime |
| `PORT_E_UNINIT` | 0x0F (FLAGGED) | `Port_SetPinDirection`, `Port_SetPinMode`, `Port_RefreshPortDirection` | API called before `Port_Init` |
| `PORT_E_PARAM_POINTER` | 0x10 (FLAGGED) | `Port_Init`, `Port_GetVersionInfo` | NULL pointer passed where a valid struct pointer is required |

Numeric values quoted are the typical AUTOSAR R24-11 assignments and are FLAGGED for manual cross-check against section 7.6.1 of the downloaded PDF (body text not parsable via WebFetch). Mnemonics are confirmed against the SWS.

Production / runtime errors: per SWS 7.6.2/7.6.3 the Port module defines no production errors in the standard configuration. Verify against the exact SWS section 7.6 when the team downloads the PDF.

---

## 4. Demo Scope Hint

To keep the CIPHER demo trial expansion focused on the Dio runtime path established in CAR-004, the Port demo slice should expose only the init-and-diagnostic surface:

- **`Port_Init`** — One-shot configuration of every `PortPin` listed in `PortConfigSet`. Exercises configuration-data validation, `PORT_E_INIT_FAILED` DET injection, and the LLD pre-condition that all subsequent Dio APIs require Port to be initialized.
- **`Port_GetVersionInfo`** — Diagnostic path; trivial implementation that exercises the `PORT_E_PARAM_POINTER` branch and the `Std_VersionInfoType` interface without any HW interaction.

This two-API slice keeps the Port demo to the prerequisite-init path only, which means:
- `Port_SetPinDirection`, `Port_SetPinMode`, and `Port_RefreshPortDirection` are listed in section 1 for spec completeness but are explicitly OUT of demo runtime scope.
- The runtime demo remains focused on Dio (CAR-004) — Port supplies a one-shot init at startup, Dio drives the four-API runtime slice, and the combined ASDLC trace stays under the 10-minute wall-clock budget.

---

## 5. Source

- **Primary URL (R24-11, latest):** https://www.autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_PortDriver.pdf
- **Fallback URL (R23-11):** https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_PortDriver.pdf
- **Release tag used:** R24-11 (Classic Platform, AUTOSAR R24-11 release wave)
- **Document ID:** CP_SWS_PortDriver_040
- **Fetched:** 2026-05-17

**Verification status of APIs against R24-11 PDF metadata:**
- Port_Init, Port_SetPinDirection, Port_RefreshPortDirection, Port_GetVersionInfo, Port_SetPinMode — all five confirmed present in the R24-11 API specification structure.
- Configuration containers Port, PortGeneral, PortContainer, PortPin, PortConfigSet — confirmed present in R24-11 section 10.1.
- DET error code mnemonics (PORT_E_PARAM_PIN, PORT_E_DIRECTION_UNCHANGEABLE, PORT_E_INIT_FAILED, PORT_E_PARAM_INVALID_MODE, PORT_E_MODE_UNCHANGEABLE, PORT_E_UNINIT, PORT_E_PARAM_POINTER) — all seven mnemonics confirmed.

**Limitation flag — items NOT verified inside this agent:**
1. Numeric DET error code values in section 7.6.1 (PDF body text not retrievable via WebFetch).
2. Explicit ASIL classification sentence in section 4 / section 7 (not retrievable via WebFetch).
3. Exact SWS section numbers for each API (8.3.1–8.3.5 quoted from the typical R24-11 ordering, needs PDF section-index cross-check).
4. Whether R24-11 introduces any vendor-extension DET codes beyond the seven mnemonics listed.

The CIPHER team should download `AUTOSAR_CP_SWS_PortDriver.pdf` (R24-11) manually and cross-check items (1)–(4) before the demo HLD for the Port slice is frozen.

---

## 6. Forward Brief

This CAR feeds the following downstream CIPHER demo artifacts (companion table to CAR-004 §6):

| Artifact | Trigger from CAR-005 |
|---|---|
| Demo HLD | API list (section 1) becomes the Port-slice HLD interface table; ASIL claim becomes the safety-goal anchor for the init path |
| Demo LLD | Two-API demo slice (section 4) is the LLD scope envelope for the Port-init prerequisite |
| Demo test plan | DET error table (section 3) becomes the negative-test row set for `Port_Init` and `Port_GetVersionInfo` |
| Demo traceability matrix | Section numbers in section 1 become the upstream-requirement IDs for the Port slice |
| ASIL gate report | "ASIL-B per AUTOSAR_CP_SWS_PortDriver" (section 0) is the gate's claim string for the Port-init prerequisite |
