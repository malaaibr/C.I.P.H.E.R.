/******************************************************************************
 * File:        LedActuator.c
 * Component:   LedActuator (Application Software Component)
 * Platform:    AUTOSAR Classic Application SWC (vendor demo)
 * Process:     ASPICE SWE.3 — Software Detailed Design and Unit Construction
 * Author:      CIPHER DEV+HLD Author (AI-assisted, vendor demo)
 * Date:        2026-05-17
 *
 *  ============================================================================
 *  ** WARNING — VENDOR-AUTHORED SWC, NOT A STANDARDISED AUTOSAR MODULE **
 *  ============================================================================
 *  There is NO AUTOSAR SWS for an application SWC. This file implements a
 *  vendor-authored Software Component whose STRUCTURE conforms to the AUTOSAR
 *  document `AUTOSAR_CP_TPS_SoftwareComponentTemplate` (R24-11), per CAR-008.
 *
 *  Every behavioural claim in this file is "vendor-derived from the SWC
 *  Template — not SWS-traced". Do NOT cite this module as "Dio-style SWS
 *  compliant"; cite it as "conforming to the SWC Template structural rules".
 *  ============================================================================
 *
 *  ARXML Structure (conceptual — the .arxml itself is NOT in this workspace;
 *  it would be emitted by the RTE configuration tool):
 *
 *    AR-PACKAGE  /Demo/SWCs/LedActuator
 *      AtomicSoftwareComponentType   : LedActuator
 *        InternalBehavior            : LedActuator_IB   (SwcInternalBehavior)
 *          RunnableEntity            : LedActuator_MainFunction
 *            Trigger                 : TimingEvent  period = 0.100 s (100 ms)
 *            Symbol                  : LedActuator_MainFunction
 *          ExclusiveAreas            : (none — single runnable)
 *        Ports:
 *          P_LedControl  : R-Port, SenderReceiverInterface
 *            DataElement : LedState : boolean
 *            (Sender    : upstream indicator-logic SWC — out of demo scope)
 *          P_LedHwAccess : R-Port, ClientServerInterface
 *            Operation   : SetSignal_LedOut(state : boolean)
 *            Operation   : GetSignal_Switch(out_state : boolean*)
 *            (Server    : IoHwAb BSW module)
 *
 *  Demo behaviour:
 *    Every 100 ms the runnable reads the current switch state via IoHwAb and
 *    drives the LED to match. The SWC keeps a single static last-state flag
 *    so a future LLD agent has realistic SWC-internal state to trace.
 *
 *  MISRA-C:2012:
 *    - Rule 15.5 — single point of return per function.
 *    - Rule 8.7  — static linkage for file-scope state.
 *
 *  Note on RTE.h:
 *    Per Tier 2 demo scope, the RTE-generated glue (Rte_Read_P_LedControl_*,
 *    Rte_Call_P_LedHwAccess_*) is conceptually present but invisible. This
 *    file calls the IoHwAb prototypes directly to keep the demo trace flat.
 *****************************************************************************/

#include "LedActuator.h"
#include "IoHwAb.h"
#include "Std_Types.h"   /* stubbed inline in Dio.h for this workspace */

/* =========================================================================
 *  File-scope state (.bss after C-runtime zero-init).
 *  HLD-LEDACT-005 traces here.
 * ========================================================================= */

/**
 * Last switch level observed by the runnable. Used by HLD-LEDACT-005
 * (state-transition latching). Initialised to FALSE by the C-runtime BSS
 * clear; LedActuator_Init() re-asserts the value defensively.
 */
static boolean LedActuator_LastSwitchState;

/* =========================================================================
 *  Public API — init
 * ========================================================================= */

/**
 *  LedActuator_Init
 *  ----------------
 *  Resets SWC-internal state. Conceptually invoked once by the RTE startup
 *  sequence (an InitEvent-bound runnable would normally hold this body; in
 *  this single-runnable demo we expose Init as a plain C entry point so the
 *  ECU integrator can call it from EcuM startup or from a unit-test harness).
 *
 *  Vendor-derived from SWC Template §4.5 (Internal Behavior init semantics).
 *  Not SWS-traced.
 */
void LedActuator_Init(void)
{
    LedActuator_LastSwitchState = FALSE;
    return;
}

/* =========================================================================
 *  Public API — periodic runnable
 * ========================================================================= */

/**
 *  LedActuator_MainFunction
 *  ------------------------
 *  // Runnable triggered by RTE TimingEvent @ 100 ms (configured in ARXML,
 *  // not in this file).
 *
 *  Behaviour:
 *    1. Read the current switch level via IoHwAb_GetSignal_Switch().
 *    2. Drive the LED to match via IoHwAb_SetSignal_LedOut().
 *    3. Latch the read value for the next cycle (HLD-LEDACT-005).
 *
 *  Error propagation:
 *    Both IoHwAb calls return Std_ReturnType. The SWC propagates failure by
 *    skipping the LED write when the switch read fails (HLD-LEDACT-006). No
 *    DET reporting — DET is a BSW concern; the SWC layer surfaces failures
 *    upward through return-code conventions and (in production) through the
 *    RTE's Std_ReturnType plumbing.
 *
 *  Re-entrancy:
 *    Non-reentrant. The RTE serialises calls to a single runnable instance
 *    by default (SWC Template §4.5.2). See HLD §6 FFI section.
 *
 *  Vendor-derived from SWC Template §4.5.2 / §4.5.3. Not SWS-traced.
 */
void LedActuator_MainFunction(void)
{
    boolean sw_state = FALSE;
    Std_ReturnType rc_get = E_NOT_OK;
    Std_ReturnType rc_set = E_NOT_OK;

    /* HLD-LEDACT-003 — read switch contract */
    rc_get = IoHwAb_GetSignal_Switch(&sw_state);

    if (rc_get == E_OK)
    {
        /* HLD-LEDACT-004 — LED drive contract */
        rc_set = IoHwAb_SetSignal_LedOut(sw_state);

        if (rc_set == E_OK)
        {
            /* HLD-LEDACT-005 — latch state for transition detection */
            LedActuator_LastSwitchState = sw_state;
        }
    }

    /* HLD-LEDACT-006 — failure is propagated upward implicitly: when either
     * IoHwAb call returns E_NOT_OK, no state is latched and the LED is left
     * at its previous level. A future revision may surface rc via an
     * Rte_Write on a status P-Port. */
    (void)rc_set; /* silence unused-warning when rc_set path is skipped */

    return;
}

/* End of file LedActuator.c */
