/******************************************************************************
 * File:        IoHwAb.c
 * Module:      I/O Hardware Abstraction (IoHwAb) - Implementation
 * Layer:       AUTOSAR Classic ECU Abstraction Layer
 * Standard:    AUTOSAR Classic Platform R24-11
 * Source:      CAR-007 (synthesized reference; see warning below)
 * Safety:      ASIL-B by inheritance from consumed Dio channels (CAR-007 sec.5)
 * Notice:      DEMO IMPLEMENTATION - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial (4-API slice).
 *
 ******************************************************************************
 *  *** SYNTHESIZED - NO NORMATIVE AUTOSAR SWS EXISTS FOR IoHwAb ***
 *
 *  This module's API surface is INVENTED for the CIPHER demo. It is derived
 *  from AUTOSAR_CP_EXP_LayeredSoftwareArchitecture (Doc ID 53, explanatory)
 *  and the (non-normative) AUTOSAR_CP_SWS_IOHardwareAbstraction guideline,
 *  which self-describes as "not intended to standardize this module ... but
 *  instead to be a guideline for the implementation of its functional
 *  interfaces". IoHwAb is realized vendor-by-vendor (Vector MICROSAR,
 *  EB tresos, ETAS RTA-BSW). See CAR-007 sections 0, 2, 3 for the full
 *  rationale. Every API name, signature, channel value, and behaviour below
 *  is SYNTHESIZED, not extracted from any AUTOSAR normative document.
 *
 *  Coding standard: MISRA-C:2012 - Rule 15.5 single-exit pattern applied
 *  to every function below. NULL pointer policy: return E_NOT_OK without
 *  touching the downstream Dio call.
 ******************************************************************************/

#include "IoHwAb.h"
#include "Dio.h"
#include "Dio_Cfg.h"

/*============================================================================*/
/* INTERNAL STATE                                                              */
/*============================================================================*/

/* Initialization flag. Set TRUE by IoHwAb_Init, consumed (informationally)
 * by all four demo APIs. The standard IoHwAb pattern - see CAR-007 sec.3 -
 * is that the upper layer (EcuM/BswM) sequences Port_Init -> Dio init ->
 * IoHwAb_Init before any RTE I/O traffic is generated. Because the demo's
 * Dio is stateless and Port is a no-op stub, this flag is not strictly
 * required for correctness - it is kept for symmetry with vendor designs. */
static boolean IoHwAb_Initialized = (boolean)0u; /* FALSE */

/*============================================================================*/
/* PUBLIC API IMPLEMENTATIONS (CAR-007 section 3)                              */
/*============================================================================*/

/* ---------------------------------------------------------------------------
 * IoHwAb_Init
 * Synthesized per CAR-007 section 3 - no SWS counterpart.
 * Caller contract: Port_Init() and any Dio init must already have run.
 * --------------------------------------------------------------------------- */
Std_ReturnType IoHwAb_Init(void)
{
    Std_ReturnType retval = E_OK;

    IoHwAb_Initialized = (boolean)1u; /* TRUE */

    return retval;
}

/* ---------------------------------------------------------------------------
 * IoHwAb_GetSignal_LedOut
 * Synthesized per CAR-007 section 3.
 * Downstream call: Dio_ReadChannel(DIO_CHANNEL_LED1) (CAR-007 sec.4).
 * NULL pointer -> no-op, E_NOT_OK (MISRA single exit).
 * --------------------------------------------------------------------------- */
Std_ReturnType IoHwAb_GetSignal_LedOut(boolean * out_state)
{
    Std_ReturnType retval = E_NOT_OK;

    if (out_state != ((boolean *)0))
    {
        Dio_LevelType level = Dio_ReadChannel(DIO_CHANNEL_LED1);
        *out_state = (boolean)((level == STD_HIGH) ? 1u : 0u);
        retval = E_OK;
    }

    return retval;
}

/* ---------------------------------------------------------------------------
 * IoHwAb_SetSignal_LedOut
 * Synthesized per CAR-007 section 3.
 * Downstream call: Dio_WriteChannel(DIO_CHANNEL_LED1, level) (CAR-007 sec.4).
 * No NULL guard (value-by-copy boolean argument).
 * --------------------------------------------------------------------------- */
Std_ReturnType IoHwAb_SetSignal_LedOut(boolean state)
{
    Std_ReturnType retval = E_OK;
    Dio_LevelType  level;

    level = (state != (boolean)0u) ? STD_HIGH : STD_LOW;
    Dio_WriteChannel(DIO_CHANNEL_LED1, level);

    return retval;
}

/* ---------------------------------------------------------------------------
 * IoHwAb_GetSignal_Switch
 * Synthesized per CAR-007 section 3.
 * Downstream call: Dio_ReadChannel(DIO_CHANNEL_SW1) (CAR-007 sec.4).
 * NULL pointer -> no-op, E_NOT_OK (MISRA single exit).
 * --------------------------------------------------------------------------- */
Std_ReturnType IoHwAb_GetSignal_Switch(boolean * out_state)
{
    Std_ReturnType retval = E_NOT_OK;

    if (out_state != ((boolean *)0))
    {
        Dio_LevelType level = Dio_ReadChannel(DIO_CHANNEL_SW1);
        *out_state = (boolean)((level == STD_HIGH) ? 1u : 0u);
        retval = E_OK;
    }

    return retval;
}

/* End of IoHwAb.c */
