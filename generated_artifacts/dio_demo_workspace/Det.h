/******************************************************************************
 * File:        Det.h
 * Module:      Det (Default Error Tracer) - Public Interface
 * Standard:    AUTOSAR Classic Platform R24-11
 * SWS Ref:     CP_SWS_DefaultErrorTracer_017 (AUTOSAR_CP_SWS_DefaultErrorTracer)
 * Safety:      QM by default; integrator may classify up to ASIL D when DET is
 *              reused as a safety mechanism (CAR-006 §0, SWS §4 / §7.5).
 * Notice:      DEMO SOURCE - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial (3-API slice).
 *****************************************************************************/
#ifndef DET_H
#define DET_H

/*============================================================================*/
/* INLINE Std_Types STUB (matches Dio.h convention)                            */
/*============================================================================*/
#ifndef STD_TYPES_INCLUDED
#define STD_TYPES_INCLUDED

typedef unsigned char       uint8;
typedef unsigned short      uint16;
typedef unsigned long       uint32;

typedef uint8               Std_ReturnType;

#ifndef E_OK
#define E_OK                ((Std_ReturnType)0x00u)
#endif
#ifndef E_NOT_OK
#define E_NOT_OK            ((Std_ReturnType)0x01u)
#endif

typedef struct {
    uint16 vendorID;
    uint16 moduleID;
    uint8  sw_major_version;
    uint8  sw_minor_version;
    uint8  sw_patch_version;
} Std_VersionInfoType;

#endif /* STD_TYPES_INCLUDED */

/*============================================================================*/
/* MODULE IDENTIFICATION (CAR-006 §0, AUTOSAR module ID list)                  */
/*============================================================================*/
#define DET_VENDOR_ID               0x002Bu
#define DET_MODULE_ID               15u
#define DET_INSTANCE_ID             0u
#define DET_SW_MAJOR_VERSION        4
#define DET_SW_MINOR_VERSION        8
#define DET_SW_PATCH_VERSION        0

/*============================================================================*/
/* API SERVICE IDs (CAR-006 §1, SWS §8.1.3.x)                                  */
/*============================================================================*/
#define DET_SID_INIT                    0x00u
#define DET_SID_REPORT_ERROR            0x01u
#define DET_SID_START                   0x02u
#define DET_SID_REPORT_RUNTIME_ERROR    0x03u
#define DET_SID_REPORT_TRANSIENT_FAULT  0x04u
#define DET_SID_GET_VERSION_INFO        0x05u

/*============================================================================*/
/* RING BUFFER GEOMETRY (demo)                                                 */
/*============================================================================*/
#define DET_BUFFER_DEPTH            16u

/*============================================================================*/
/* TYPEDEFS                                                                    */
/*============================================================================*/
/**
 * @brief Opaque configuration handle (CAR-006 §2, SWS §10.2.1).
 *        Real integrations populate via DetGeneral / DetConfigSet trees.
 */
typedef struct {
    uint8 ConfigVariant;   /* PRE-COMPILE = 0u, POST-BUILD = 1u (demo: 0u) */
} Det_ConfigType;

/**
 * @brief One ring-buffer entry capturing the SWS (ModuleId, InstanceId,
 *        ApiId, ErrorId) tuple per CAR-006 §3 plus a monotonic timestamp.
 */
typedef struct {
    uint16 ModuleId;
    uint8  InstanceId;
    uint8  ApiId;
    uint8  ErrorId;
    uint32 Timestamp;
} Det_ErrorRecord_t;

/*============================================================================*/
/* PUBLIC API - DEMO SCOPE (CAR-006 §4)                                        */
/*============================================================================*/

/** Det_Init - CAR-006 §1, SWS §8.1.3.1. */
void Det_Init(const Det_ConfigType * ConfigPtr);

/** Det_ReportError - CAR-006 §1, SWS §8.1.3.2. The API Dio calls. */
Std_ReturnType Det_ReportError(uint16 ModuleId,
                               uint8  InstanceId,
                               uint8  ApiId,
                               uint8  ErrorId);

/** Det_GetVersionInfo - CAR-006 §1, SWS §8.1.3.6. */
void Det_GetVersionInfo(Std_VersionInfoType * versioninfo);

/*============================================================================*/
/* DECLARED FOR SWS COMPLETENESS - NOT EXERCISED IN DEMO (CAR-006 §4)          */
/*============================================================================*/
// Declared for SWS completeness; not exercised in demo.
void Det_Start(void);

// Declared for SWS completeness; not exercised in demo.
Std_ReturnType Det_ReportRuntimeError(uint16 ModuleId,
                                      uint8  InstanceId,
                                      uint8  ApiId,
                                      uint8  ErrorId);

// Declared for SWS completeness; not exercised in demo.
Std_ReturnType Det_ReportTransientFault(uint16 ModuleId,
                                        uint8  InstanceId,
                                        uint8  ApiId,
                                        uint8  ErrorId);

#endif /* DET_H */
/* End of file: Det.h */
