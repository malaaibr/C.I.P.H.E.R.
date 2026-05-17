/******************************************************************************
 * File:        Port.h
 * Module:      Port (AUTOSAR Port Driver) - Public Interface
 * Standard:    AUTOSAR Classic Platform R24-11
 * SWS Ref:     CP_SWS_PortDriver_040 (AUTOSAR_CP_SWS_PortDriver, sections 8.3.x)
 * Safety:      ASIL-B per AUTOSAR_CP_SWS_PortDriver
 *              (CAR-005 frontmatter records ASIL claim as FLAGGED — explicit
 *               ASIL classification sentence not retrievable via WebFetch;
 *               see CAR-005 §0 / §5 limitation flag #2)
 * Notice:      DEMO HEADER - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial (init-only 2-API slice
 *              per CAR-005 §4).
 *****************************************************************************/

#ifndef PORT_H
#define PORT_H

#include "Dio.h"  /* Re-use uint8/uint16/Std_VersionInfoType from Dio.h demo */

/*============================================================================*/
/* MODULE / VENDOR IDENTIFICATION (per SWS section 5.1; CAR-005 §0)            */
/*============================================================================*/
#define PORT_VENDOR_ID            0x002Bu  /* Demo vendor ID (matches Dio)     */
#define PORT_MODULE_ID            124u     /* AUTOSAR module ID for Port       */
#define PORT_SW_MAJOR_VERSION     4
#define PORT_SW_MINOR_VERSION     8
#define PORT_SW_PATCH_VERSION     0

/*============================================================================*/
/* DET ERROR CODES (per SWS section 7.6.1; CAR-005 §3)                         */
/*============================================================================*/
/* CAVEAT: Numeric values below are typical AUTOSAR R24-11 assignments.        */
/* CAR-005 §3 / §5 FLAGS these as unverified (PDF body text not parsable via   */
/* WebFetch). Manual cross-check against AUTOSAR_CP_SWS_PortDriver.pdf 7.6.1   */
/* is required before any safety-case freeze. Mnemonics ARE confirmed.        */
#define PORT_E_PARAM_PIN                  0x0Au  /* Pin ID not configured     */
#define PORT_E_DIRECTION_UNCHANGEABLE     0x0Bu  /* Direction not changeable  */
#define PORT_E_INIT_FAILED                0x0Cu  /* Bad config at Port_Init   */
#define PORT_E_PARAM_INVALID_MODE         0x0Du  /* Mode not in allowed set   */
#define PORT_E_MODE_UNCHANGEABLE          0x0Eu  /* Mode not changeable       */
#define PORT_E_UNINIT                     0x0Fu  /* API called before init    */
#define PORT_E_PARAM_POINTER              0x10u  /* NULL pointer arg          */

/* API service IDs (per SWS section 8.2 — demo APIs only) */
#define PORT_SID_INIT                     0x00u
#define PORT_SID_GET_VERSION_INFO         0x03u

/*============================================================================*/
/* TYPE DEFINITIONS (per SWS section 8.4; CAR-005 §2)                          */
/*============================================================================*/

/* Symbolic pin identifier (SWS 8.4 Port_PinType). 3 ports x 16 pins = 48.    */
typedef uint8 Port_PinType;

/* Pin direction (SWS 8.4 Port_PinDirectionType). */
typedef enum {
    PORT_PIN_IN  = 0,
    PORT_PIN_OUT = 1
} Port_PinDirectionType;

/* Pin mode (SWS 8.4 Port_PinModeType). Demo treats mode as opaque uint8.     */
typedef uint8 Port_PinModeType;

/* Per-pin configuration record (CAR-005 §2 PortPin container projection).    */
typedef struct {
    Port_PinType          PinId;
    Port_PinDirectionType Direction;
    Port_PinModeType      Mode;
} Port_PinConfig_t;

/* Top-level configuration set (CAR-005 §2 PortConfigSet projection).         */
typedef struct {
    uint16                   NumPins;
    const Port_PinConfig_t * Pins;
} Port_ConfigType;

/*============================================================================*/
/* PUBLIC API PROTOTYPES (per SWS section 8.3; CAR-005 §1 — demo 2-API slice)  */
/*============================================================================*/

/* SWS 8.3.1 - Service ID 0x00 - one-shot pin configuration (CAR-005 §4) */
extern void Port_Init(const Port_ConfigType * ConfigPtr);

/* SWS 8.3.4 - Service ID 0x03 - module version reporting (CAR-005 §4) */
extern void Port_GetVersionInfo(Std_VersionInfoType * versioninfo);

#endif /* PORT_H */
