/******************************************************************************
 * File:        Port.c
 * Module:      Port (AUTOSAR Port Driver) - Implementation
 * Standard:    AUTOSAR Classic Platform R24-11
 * SWS Ref:     CP_SWS_PortDriver_040 (AUTOSAR_CP_SWS_PortDriver)
 * Safety:      ASIL-B per AUTOSAR_CP_SWS_PortDriver
 *              (CAR-005 §0 FLAGS the explicit ASIL classification sentence as
 *               not retrievable via WebFetch — see CAR-005 §5 limitation #2.)
 * Notice:      DEMO SOURCE - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial. Implements the init-only
 *              2-API slice (Port_Init / Port_GetVersionInfo) per CAR-005 §4
 *              over an in-memory pin-shadow array. No real hardware access.
 *****************************************************************************/

#include "Port.h"

/*============================================================================*/
/* DEMO CONFIGURATION CONSTANTS                                                */
/*============================================================================*/
#define PORT_DEMO_NUM_PORTS         3u      /* PortA, PortB, PortC             */
#define PORT_DEMO_PINS_PER_PORT     16u
#define PORT_DEMO_MAX_PIN_ID        ((Port_PinType)(PORT_DEMO_NUM_PORTS \
                                     * PORT_DEMO_PINS_PER_PORT))   /* = 48u   */

/*============================================================================*/
/* DET STUB - WIRED TO Det IN TARGET BUILD                                     */
/*============================================================================*/
/* Stubbed for demo - wired to Det in target build */
extern void Det_ReportError(uint16 ModuleId,
                            uint8  InstanceId,
                            uint8  ApiId,
                            uint8  ErrorId);

/* TRUE / FALSE for the demo (Std_Types.h boolean stand-in). */
#ifndef TRUE
#define TRUE  1u
#endif
#ifndef FALSE
#define FALSE 0u
#endif
typedef uint8 boolean;

/*============================================================================*/
/* MODULE-INTERNAL STATE (file-scope, MISRA-C:2012 R8.7 single TU)             */
/*============================================================================*/

/* Pin-shadow: one Port_PinConfig_t slot per addressable pin.                  */
/* 3 ports x 16 pins each = 48 entries. Initialised to {0, PORT_PIN_IN, 0}.    */
static Port_PinConfig_t Port_PinShadow[PORT_DEMO_NUM_PORTS
                                       * PORT_DEMO_PINS_PER_PORT] = { 0 };

/* Module initialisation flag. Set TRUE after a successful Port_Init pass.     */
static boolean Port_Initialized = FALSE;

/*============================================================================*/
/* INTERNAL HELPERS                                                            */
/*============================================================================*/

/**
 * @brief  Range-checks a Port_PinType against the demo pin-ID domain.
 * @param  PinId  Pin identifier under test.
 * @return TRUE when PinId is in [0, 48); FALSE otherwise.
 */
static boolean Port_IsValidPinId(Port_PinType PinId)
{
    /* MISRA-C:2012 R15.5 - single exit point */
    boolean retval = FALSE;

    if (PinId < PORT_DEMO_MAX_PIN_ID)
    {
        retval = TRUE;
    }

    return retval;
}

/*============================================================================*/
/* PUBLIC API - Port_Init (SWS 8.3.1)                                          */
/*============================================================================*/
/**
 * @brief  Configures all pins listed in *ConfigPtr into the pin shadow table.
 * @param  ConfigPtr  Pointer to the active Port_ConfigType set. Must be non-NULL.
 *
 * NULL ConfigPtr -> DET PORT_E_PARAM_CONFIG (mapped to PORT_E_INIT_FAILED per
 * CAR-005 §3 row "Port_Init"), no shadow mutation, Port_Initialized stays FALSE.
 */
void Port_Init(const Port_ConfigType * ConfigPtr)
{
    /* MISRA-C:2012 R15.5 - single exit via guard */
    if (ConfigPtr == ((const Port_ConfigType *)0))
    {
        Det_ReportError((uint16)PORT_MODULE_ID,
                        (uint8)0u,
                        (uint8)PORT_SID_INIT,
                        (uint8)PORT_E_INIT_FAILED);
    }
    else
    {
        uint16 idx;

        for (idx = 0u; idx < ConfigPtr->NumPins; ++idx)
        {
            const Port_PinConfig_t * const pin_cfg = &ConfigPtr->Pins[idx];

            if (Port_IsValidPinId(pin_cfg->PinId) == TRUE)
            {
                Port_PinShadow[pin_cfg->PinId].PinId     = pin_cfg->PinId;
                Port_PinShadow[pin_cfg->PinId].Direction = pin_cfg->Direction;
                Port_PinShadow[pin_cfg->PinId].Mode      = pin_cfg->Mode;
            }
            else
            {
                /* Out-of-range pin entry in config set: DET-flag, skip. */
                Det_ReportError((uint16)PORT_MODULE_ID,
                                (uint8)0u,
                                (uint8)PORT_SID_INIT,
                                (uint8)PORT_E_PARAM_PIN);
            }
        }

        Port_Initialized = TRUE;
    }
}

/*============================================================================*/
/* PUBLIC API - Port_GetVersionInfo (SWS 8.3.4)                                */
/*============================================================================*/
/**
 * @brief  Populates a Std_VersionInfoType with the Port module version.
 * @param  versioninfo  Output pointer. Must be non-NULL.
 */
void Port_GetVersionInfo(Std_VersionInfoType * versioninfo)
{
    /* MISRA-C:2012 R15.5 - single exit via guard */
    if (versioninfo == ((Std_VersionInfoType *)0))
    {
        Det_ReportError((uint16)PORT_MODULE_ID,
                        (uint8)0u,
                        (uint8)PORT_SID_GET_VERSION_INFO,
                        (uint8)PORT_E_PARAM_POINTER);
    }
    else
    {
        versioninfo->vendorID         = (uint16)PORT_VENDOR_ID;
        versioninfo->moduleID         = (uint16)PORT_MODULE_ID;
        versioninfo->sw_major_version = (uint8)PORT_SW_MAJOR_VERSION;
        versioninfo->sw_minor_version = (uint8)PORT_SW_MINOR_VERSION;
        versioninfo->sw_patch_version = (uint8)PORT_SW_PATCH_VERSION;
    }
}

/* End of file: Port.c */
