/******************************************************************************
 * File:        IoHwAb.h
 * Module:      I/O Hardware Abstraction (IoHwAb) - Public Interface
 * Layer:       AUTOSAR Classic ECU Abstraction Layer
 * Standard:    AUTOSAR Classic Platform R24-11
 * Source:      CAR-007 (synthesized reference, no normative SWS exists)
 * Safety:      ASIL-B by inheritance from consumed Dio channels (CAR-007 sec.5)
 *
 ******************************************************************************
 *  *** SYNTHESIZED - NO NORMATIVE AUTOSAR SWS EXISTS FOR IoHwAb ***
 *
 *  The four IoHwAb_* APIs declared here are INVENTED for the CIPHER demo.
 *  They are derived from AUTOSAR_CP_EXP_LayeredSoftwareArchitecture (Doc ID 53)
 *  and the (non-normative) AUTOSAR_CP_SWS_IOHardwareAbstraction guideline,
 *  which self-describes as "not intended to standardize this module".
 *  See CAR-007 sections 0, 2, and 3 for the full rationale.
 *  Every API name, signature, and direction below is SYNTHESIZED, not
 *  extracted from any AUTOSAR normative document.
 ******************************************************************************/

#ifndef IOHWAB_H
#define IOHWAB_H

/* Std_ReturnType, boolean, E_OK, E_NOT_OK are normally provided by Std_Types.h
 * The demo's Dio.h carries the stubbed type set (see Dio.h lines 42-55) which
 * is sufficient for this 4-API IoHwAb slice. */
#include "Dio.h"

/*============================================================================*/
/* DEMO TYPE STUBS (production: from Std_Types.h)                              */
/*============================================================================*/
#ifndef E_OK
#define E_OK      ((Std_ReturnType)0x00u)
#endif
#ifndef E_NOT_OK
#define E_NOT_OK  ((Std_ReturnType)0x01u)
#endif

#ifndef STD_TYPES_RETURNTYPE_DEFINED
typedef uint8 Std_ReturnType;
#define STD_TYPES_RETURNTYPE_DEFINED
#endif

#ifndef STD_TYPES_BOOLEAN_DEFINED
typedef uint8 boolean;
#define STD_TYPES_BOOLEAN_DEFINED
#endif

/*============================================================================*/
/* PUBLIC API PROTOTYPES (demo 4-API slice, CAR-007 section 3)                 */
/*                                                                             */
/* NOTE: IoHwAb has NO AUTOSAR-assigned vendor ID, module ID, or version       */
/* macros because no SWS standardizes the module. Vendor implementations       */
/* (Vector MICROSAR, EB tresos, ETAS RTA-BSW) carry their own proprietary      */
/* identification - intentionally omitted here.                                */
/*============================================================================*/

/**
 * @brief  One-time initialization of the IoHwAb signal-to-channel map.
 * @return E_OK on success.
 *
 * Downstream: none directly. Caller (EcuM/BswM) is responsible for having
 * already invoked Port_Init() and any required Dio init prior to this call.
 * Sets an internal initialized flag consumed by the Get/Set APIs.
 *
 * Source: CAR-007 section 3 (synthesized).
 */
extern Std_ReturnType IoHwAb_Init(void);

/**
 * @brief  Read back the latched LedOut actuator state.
 * @param  out_state Caller-provided buffer; receives TRUE if pin is STD_HIGH.
 * @return E_OK on success, E_NOT_OK if out_state is NULL.
 *
 * Downstream call: Dio_ReadChannel(DIO_CHANNEL_LED1).
 * Source: CAR-007 section 3 / section 4 (synthesized).
 */
extern Std_ReturnType IoHwAb_GetSignal_LedOut(boolean * out_state);

/**
 * @brief  Drive the LedOut actuator to the requested logical state.
 * @param  state  TRUE -> STD_HIGH, FALSE -> STD_LOW.
 * @return E_OK (Dio_WriteChannel has no return).
 *
 * Downstream call: Dio_WriteChannel(DIO_CHANNEL_LED1, state ? STD_HIGH : STD_LOW).
 * Source: CAR-007 section 3 / section 4 (synthesized).
 */
extern Std_ReturnType IoHwAb_SetSignal_LedOut(boolean state);

/**
 * @brief  Read the current Switch input sensor state.
 * @param  out_state Caller-provided buffer; receives TRUE if pin is STD_HIGH.
 * @return E_OK on success, E_NOT_OK if out_state is NULL.
 *
 * Downstream call: Dio_ReadChannel(DIO_CHANNEL_SW1).
 * Source: CAR-007 section 3 / section 4 (synthesized).
 */
extern Std_ReturnType IoHwAb_GetSignal_Switch(boolean * out_state);

#endif /* IOHWAB_H */
