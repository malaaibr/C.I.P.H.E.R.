/******************************************************************************
 * File:        LedActuator.h
 * Component:   LedActuator (Application Software Component)
 * Platform:    AUTOSAR Classic Application SWC (vendor demo)
 *
 *  ============================================================================
 *  ** WARNING — VENDOR-AUTHORED SWC, NOT A STANDARDISED AUTOSAR MODULE **
 *  ============================================================================
 *  There is NO AUTOSAR SWS for an application SWC. This header is part of a
 *  vendor-authored SWC whose structure conforms to
 *  `AUTOSAR_CP_TPS_SoftwareComponentTemplate` (R24-11), per CAR-008.
 *
 *  Behavioural prototypes below are "vendor-derived from the SWC Template
 *  — not SWS-traced". No AUTOSAR module IDs or vendor IDs are declared here;
 *  application SWCs do not own AUTOSAR module identifiers (only BSW modules
 *  do — see AUTOSAR_CP_TPS_BSWModuleDescriptionTemplate for the BSW case).
 *  ============================================================================
 *****************************************************************************/

#ifndef LEDACTUATOR_H
#define LEDACTUATOR_H

/* -------------------------------------------------------------------------
 *  Forward / minimal typedefs
 * -------------------------------------------------------------------------
 *  The SWC consumes IoHwAb's Std_ReturnType-returning prototypes; both
 *  Std_ReturnType and `boolean` live in Std_Types.h (stubbed inline in
 *  Dio.h within this workspace).
 *
 *  No port-element typedefs are forward-declared here because the demo
 *  uses primitive `boolean` for the single SenderReceiver data element
 *  (`LedState`), and primitive `boolean` arguments for the ClientServer
 *  operations on P_LedHwAccess. A future revision that introduces an
 *  ApplicationDataType / ImplementationDataType mapping would add the
 *  generated typedef header here (e.g. `#include "Rte_Type.h"`).
 * ------------------------------------------------------------------------- */

/* -------------------------------------------------------------------------
 *  Public API prototypes
 * -------------------------------------------------------------------------
 *  Both functions are file-scope-external by AUTOSAR convention; they are
 *  the symbols the (conceptual) RTE will bind to the OS tasks generated
 *  for this SWC.
 * ------------------------------------------------------------------------- */

/**
 *  Reset SWC-internal state. Called once by the RTE startup sequence (or
 *  by EcuM in the integrator's runtime).
 *
 *  HLD trace: HLD-LEDACT-001
 */
extern void LedActuator_Init(void);

/**
 *  Periodic runnable body. Bound in ARXML to a TimingEvent with
 *  `period = 0.1 s` (100 ms). Reads the switch via IoHwAb and drives the
 *  LED to match.
 *
 *  HLD trace: HLD-LEDACT-002, HLD-LEDACT-003, HLD-LEDACT-004,
 *             HLD-LEDACT-005, HLD-LEDACT-006, HLD-LEDACT-008
 */
extern void LedActuator_MainFunction(void);

#endif /* LEDACTUATOR_H */

/* End of file LedActuator.h */
