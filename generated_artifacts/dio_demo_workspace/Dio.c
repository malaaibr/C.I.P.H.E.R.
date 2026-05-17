/******************************************************************************
 * File:        Dio.c
 * Module:      Dio (Digital I/O Driver) - Implementation
 * Standard:    AUTOSAR Classic Platform R24-11
 * SWS Ref:     CP_SWS_DIODriver_020 (AUTOSAR_CP_SWS_DIODriver)
 * Safety:      ASIL-B per AUTOSAR_CP_SWS_DIODriver
 * Notice:      DEMO SOURCE - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial. Implements the 4-API
 *              slice (WriteChannel / ReadChannel / FlipChannel / GetVersionInfo)
 *              over an in-memory shadow register set. No real hardware access.
 *****************************************************************************/

#include "Dio.h"

/*============================================================================*/
/* DEMO CONFIGURATION CONSTANTS                                                */
/*============================================================================*/
#define DIO_DEMO_NUM_PORTS         3u      /* PortA, PortB, PortC              */
#define DIO_DEMO_BITS_PER_PORT     16u
#define DIO_DEMO_MAX_CHANNEL_ID    ((Dio_ChannelType)(DIO_DEMO_NUM_PORTS \
                                    * DIO_DEMO_BITS_PER_PORT))

/*============================================================================*/
/* DET STUB - WIRED TO Det IN TARGET BUILD                                      */
/*============================================================================*/
/* Stubbed for demo - wired to Det in target build */
extern void Det_ReportError(uint16 ModuleId,
                            uint8  InstanceId,
                            uint8  ApiId,
                            uint8  ErrorId);

/*============================================================================*/
/* MODULE-INTERNAL STATE (file-scope, MISRA-C:2012 R8.7 single TU)             */
/*============================================================================*/

/* Shadow registers backing the demo "hardware". 3 ports x 16 bits each. */
static Dio_PortRegister_t Dio_PortShadow[DIO_DEMO_NUM_PORTS] = {
    { 0x0000u, 0u },   /* PortA */
    { 0x0000u, 1u },   /* PortB */
    { 0x0000u, 2u }    /* PortC */
};

/*============================================================================*/
/* INTERNAL HELPERS                                                            */
/*============================================================================*/

/**
 * @brief  Returns the current shadow value for a port.
 * @param  PortId  Port index (0..DIO_DEMO_NUM_PORTS-1). Caller guarantees range.
 * @return Latched port-level word.
 */
static Dio_PortLevelType Dio_GetPortBackingRef(Dio_PortType PortId)
{
    /* MISRA-C:2012 R15.5 - single exit point */
    Dio_PortLevelType retval = (Dio_PortLevelType)0u;

    if (PortId < (Dio_PortType)DIO_DEMO_NUM_PORTS)
    {
        retval = Dio_PortShadow[PortId].value;
    }

    return retval;
}

/*============================================================================*/
/* PUBLIC API - Dio_WriteChannel (SWS 8.3.2)                                   */
/*============================================================================*/
/**
 * @brief  Sets the level of a single Dio channel.
 * @param  ChannelId  Symbolic channel ID (0..DIO_DEMO_MAX_CHANNEL_ID-1).
 * @param  Level      STD_HIGH or STD_LOW.
 */
void Dio_WriteChannel(Dio_ChannelType ChannelId, Dio_LevelType Level)
{
    /* MISRA-C:2012 R15.5 - single exit via guard */
    if (ChannelId >= DIO_DEMO_MAX_CHANNEL_ID)
    {
        Det_ReportError((uint16)DIO_MODULE_ID,
                        (uint8)0u,
                        (uint8)DIO_SID_WRITE_CHANNEL,
                        (uint8)DIO_E_PARAM_INVALID_CHANNEL_ID);
    }
    else
    {
        const Dio_PortType  port_idx = (Dio_PortType)(ChannelId / DIO_DEMO_BITS_PER_PORT);
        const uint16        bit_mask = (uint16)((uint16)1u << (ChannelId % DIO_DEMO_BITS_PER_PORT));

        if (Level == STD_HIGH)
        {
            Dio_PortShadow[port_idx].value |= bit_mask;
        }
        else
        {
            Dio_PortShadow[port_idx].value &= (Dio_PortLevelType)(~bit_mask);
        }
    }
}

/*============================================================================*/
/* PUBLIC API - Dio_ReadChannel (SWS 8.3.1)                                    */
/*============================================================================*/
/**
 * @brief  Returns the current level of a single Dio channel.
 * @param  ChannelId  Symbolic channel ID (0..DIO_DEMO_MAX_CHANNEL_ID-1).
 * @return STD_HIGH if the channel bit is set, STD_LOW otherwise.
 */
Dio_LevelType Dio_ReadChannel(Dio_ChannelType ChannelId)
{
    /* MISRA-C:2012 R15.5 - single exit point */
    Dio_LevelType retval = STD_LOW;

    if (ChannelId >= DIO_DEMO_MAX_CHANNEL_ID)
    {
        Det_ReportError((uint16)DIO_MODULE_ID,
                        (uint8)0u,
                        (uint8)DIO_SID_READ_CHANNEL,
                        (uint8)DIO_E_PARAM_INVALID_CHANNEL_ID);
    }
    else
    {
        const Dio_PortType      port_idx = (Dio_PortType)(ChannelId / DIO_DEMO_BITS_PER_PORT);
        const uint16            bit_mask = (uint16)((uint16)1u << (ChannelId % DIO_DEMO_BITS_PER_PORT));
        const Dio_PortLevelType port_val = Dio_GetPortBackingRef(port_idx);

        if ((port_val & bit_mask) != (uint16)0u)
        {
            retval = STD_HIGH;
        }
    }

    return retval;
}

/*============================================================================*/
/* PUBLIC API - Dio_FlipChannel (SWS 8.3.8, AUTOSAR 4.x)                       */
/*============================================================================*/
/**
 * @brief  Inverts the level of a single Dio channel (read-modify-write).
 * @param  ChannelId  Symbolic channel ID (0..DIO_DEMO_MAX_CHANNEL_ID-1).
 * @return The NEW level after the flip (STD_HIGH or STD_LOW).
 */
Dio_LevelType Dio_FlipChannel(Dio_ChannelType ChannelId)
{
    /* MISRA-C:2012 R15.5 - single exit point */
    Dio_LevelType retval = STD_LOW;

    if (ChannelId >= DIO_DEMO_MAX_CHANNEL_ID)
    {
        Det_ReportError((uint16)DIO_MODULE_ID,
                        (uint8)0u,
                        (uint8)DIO_SID_FLIP_CHANNEL,
                        (uint8)DIO_E_PARAM_INVALID_CHANNEL_ID);
    }
    else
    {
        const Dio_PortType port_idx = (Dio_PortType)(ChannelId / DIO_DEMO_BITS_PER_PORT);
        const uint16       bit_mask = (uint16)((uint16)1u << (ChannelId % DIO_DEMO_BITS_PER_PORT));

        Dio_PortShadow[port_idx].value ^= bit_mask;

        if ((Dio_PortShadow[port_idx].value & bit_mask) != (uint16)0u)
        {
            retval = STD_HIGH;
        }
    }

    return retval;
}

/*============================================================================*/
/* PUBLIC API - Dio_GetVersionInfo (SWS 8.3.7)                                 */
/*============================================================================*/
/**
 * @brief  Populates a Std_VersionInfoType with the Dio module version.
 * @param  VersionInfo  Output pointer. Must be non-NULL.
 */
void Dio_GetVersionInfo(Std_VersionInfoType* VersionInfo)
{
    /* MISRA-C:2012 R15.5 - single exit via guard */
    if (VersionInfo == ((Std_VersionInfoType*)0))
    {
        Det_ReportError((uint16)DIO_MODULE_ID,
                        (uint8)0u,
                        (uint8)DIO_SID_GET_VERSION_INFO,
                        (uint8)DIO_E_PARAM_POINTER);
    }
    else
    {
        VersionInfo->vendorID         = (uint16)DIO_VENDOR_ID;
        VersionInfo->moduleID         = (uint16)DIO_MODULE_ID;
        VersionInfo->sw_major_version = (uint8)DIO_SW_MAJOR_VERSION;
        VersionInfo->sw_minor_version = (uint8)DIO_SW_MINOR_VERSION;
        VersionInfo->sw_patch_version = (uint8)DIO_SW_PATCH_VERSION;
    }
}

/* End of file: Dio.c */
