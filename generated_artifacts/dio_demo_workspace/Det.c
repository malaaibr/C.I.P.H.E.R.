/******************************************************************************
 * File:        Det.c
 * Module:      Det (Default Error Tracer) - Implementation
 * Standard:    AUTOSAR Classic Platform R24-11
 * SWS Ref:     CP_SWS_DefaultErrorTracer_017 (AUTOSAR_CP_SWS_DefaultErrorTracer)
 * Safety:      QM by default; integrator may classify higher per CAR-006 §0
 *              ("QM by default; integrator-classified up to ASIL D when used
 *              as a safety mechanism - quote the SWS rather than assume").
 * Notice:      DEMO SOURCE - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial. Implements the 3-API
 *              demo slice (Init / ReportError / GetVersionInfo) backed by a
 *              16-deep static ring buffer. No DEM hand-off, no callouts.
 *****************************************************************************/

#include "Det.h"

/*============================================================================*/
/* MODULE-INTERNAL STATE (file-scope, MISRA-C:2012 R8.7 single TU)             */
/*============================================================================*/

/* Ring buffer: last DET_BUFFER_DEPTH error tuples (CAR-006 §3). Lives in .bss
 * because zero-init is the natural "no records yet" sentinel. */
static Det_ErrorRecord_t Det_Buffer[DET_BUFFER_DEPTH];

/* Write index into Det_Buffer (modulo DET_BUFFER_DEPTH). */
static uint8  Det_BufferIdx;

/* Monotonic count of every report received since Det_Init. Acts as the per-
 * record timestamp and as the buffer-overflow indicator (>= DEPTH => wrapped). */
static uint32 Det_TotalCount;

/* Set by Det_Init; gates the ReportError path per SWS §8.1.3.1. */
static uint8  Det_Initialized;

/*============================================================================*/
/* PUBLIC API - Det_Init (CAR-006 §1, SWS §8.1.3.1)                            */
/*============================================================================*/
/**
 * @brief  Initialises DET internal state.
 * @param  ConfigPtr  Opaque configuration handle. NULL accepted in demo;
 *                    real SWS allows NULL when PRE-COMPILE variant is used.
 */
void Det_Init(const Det_ConfigType * ConfigPtr)
{
    /* MISRA-C:2012 R15.5 - single exit (fall-through). */
    uint8 i;

    (void)ConfigPtr;  /* PRE-COMPILE demo: configuration is compile-time. */

    for (i = 0u; i < (uint8)DET_BUFFER_DEPTH; i++)
    {
        Det_Buffer[i].ModuleId   = (uint16)0u;
        Det_Buffer[i].InstanceId = (uint8)0u;
        Det_Buffer[i].ApiId      = (uint8)0u;
        Det_Buffer[i].ErrorId    = (uint8)0u;
        Det_Buffer[i].Timestamp  = (uint32)0u;
    }

    Det_BufferIdx   = (uint8)0u;
    Det_TotalCount  = (uint32)0u;
    Det_Initialized = (uint8)1u;
}

/*============================================================================*/
/* PUBLIC API - Det_ReportError (CAR-006 §1, SWS §8.1.3.2)                     */
/*============================================================================*/
/**
 * @brief  Records a development error tuple. The API Dio calls.
 * @param  ModuleId    Caller's BSW module ID (Dio = 120).
 * @param  InstanceId  Caller's instance index (Dio = 0).
 * @param  ApiId       Per-API service ID from the caller's SWS.
 * @param  ErrorId     Caller's DET error code (e.g. DIO_E_PARAM_*).
 * @return E_OK always (SWS §8.1.3.2 return contract).
 *
 * In production, may invoke configurable error sink; demo: ring buffer only.
 */
Std_ReturnType Det_ReportError(uint16 ModuleId,
                               uint8  InstanceId,
                               uint8  ApiId,
                               uint8  ErrorId)
{
    /* MISRA-C:2012 R15.5 - single exit point. */
    Std_ReturnType retval = E_OK;

    if (Det_Initialized != (uint8)0u)
    {
        Det_Buffer[Det_BufferIdx].ModuleId   = ModuleId;
        Det_Buffer[Det_BufferIdx].InstanceId = InstanceId;
        Det_Buffer[Det_BufferIdx].ApiId      = ApiId;
        Det_Buffer[Det_BufferIdx].ErrorId    = ErrorId;
        Det_Buffer[Det_BufferIdx].Timestamp  = Det_TotalCount;

        Det_BufferIdx  = (uint8)((Det_BufferIdx + (uint8)1u) % (uint8)DET_BUFFER_DEPTH);
        Det_TotalCount = Det_TotalCount + (uint32)1u;
    }
    /* else: pre-init call - silent no-op per SWS §8.1.3.1 (uninit behaviour). */

    return retval;
}

/*============================================================================*/
/* PUBLIC API - Det_GetVersionInfo (CAR-006 §1, SWS §8.1.3.6)                  */
/*============================================================================*/
/**
 * @brief  Populates a Std_VersionInfoType with the Det module version.
 * @param  versioninfo  Output pointer. NULL => silent no-op (DET cannot
 *                      DET-report on itself per SWS).
 */
void Det_GetVersionInfo(Std_VersionInfoType * versioninfo)
{
    /* MISRA-C:2012 R15.5 - single exit via guard. */
    if (versioninfo != ((Std_VersionInfoType *)0))
    {
        versioninfo->vendorID         = (uint16)DET_VENDOR_ID;
        versioninfo->moduleID         = (uint16)DET_MODULE_ID;
        versioninfo->sw_major_version = (uint8)DET_SW_MAJOR_VERSION;
        versioninfo->sw_minor_version = (uint8)DET_SW_MINOR_VERSION;
        versioninfo->sw_patch_version = (uint8)DET_SW_PATCH_VERSION;
    }
    /* else: NULL pointer - DET MUST NOT DET-report itself. Silent return. */
}

/* End of file: Det.c */
