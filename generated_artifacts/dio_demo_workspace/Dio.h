/******************************************************************************
 * File:        Dio.h
 * Module:      Dio (Digital I/O Driver) - Public Interface
 * Standard:    AUTOSAR Classic Platform R24-11
 * SWS Ref:     CP_SWS_DIODriver_020 (AUTOSAR_CP_SWS_DIODriver, sections 8.3.x)
 * Safety:      ASIL-B per AUTOSAR_CP_SWS_DIODriver
 * Notice:      DEMO HEADER - NOT FOR PRODUCTION USE.
 *              Generated for CIPHER ASDLC demo trial (4-API slice).
 *****************************************************************************/

#ifndef DIO_H
#define DIO_H

/*============================================================================*/
/* MODULE / VENDOR IDENTIFICATION (per SWS section 5.1)                        */
/*============================================================================*/
#define DIO_VENDOR_ID            0x002Bu  /* Demo vendor ID                   */
#define DIO_MODULE_ID            120u     /* AUTOSAR module ID for Dio        */
#define DIO_SW_MAJOR_VERSION     4
#define DIO_SW_MINOR_VERSION     8
#define DIO_SW_PATCH_VERSION     0

/*============================================================================*/
/* DET ERROR CODES (per SWS section 7.6.1, CAR-004 section 3)                  */
/*============================================================================*/
#define DIO_E_PARAM_INVALID_CHANNEL_ID   0x0Au  /* Bad channel ID              */
#define DIO_E_PARAM_INVALID_PORT_ID      0x14u  /* Bad port ID                 */
#define DIO_E_PARAM_INVALID_GROUP        0x1Fu  /* Bad channel-group pointer   */
#define DIO_E_PARAM_POINTER              0x20u  /* NULL pointer where invalid  */
#define DIO_E_PARAM_CONFIG               0x30u  /* Invalid config set at init  */

/* API service IDs (per SWS section 8.2) */
#define DIO_SID_READ_CHANNEL             0x00u
#define DIO_SID_WRITE_CHANNEL            0x01u
#define DIO_SID_FLIP_CHANNEL             0x11u
#define DIO_SID_GET_VERSION_INFO         0x12u

/*============================================================================*/
/* TYPE DEFINITIONS (per SWS section 8.4)                                      */
/*============================================================================*/

/* Std_ReturnType / Std_VersionInfoType stand-ins (normally from Std_Types.h)  */
#ifndef STD_TYPES_INCLUDED
typedef unsigned char  uint8;
typedef unsigned short uint16;
typedef unsigned long  uint32;

typedef struct {
    uint16 vendorID;
    uint16 moduleID;
    uint8  sw_major_version;
    uint8  sw_minor_version;
    uint8  sw_patch_version;
} Std_VersionInfoType;
#endif /* STD_TYPES_INCLUDED */

/* Dio channel ID - symbolic identifier of a single pin (SWS 8.4.1) */
typedef uint16 Dio_ChannelType;

/* Dio port ID - symbolic identifier of an MCU port (SWS 8.4.2) */
typedef uint8  Dio_PortType;

/* Dio level - electrical signal level (SWS 8.4.3) */
typedef enum {
    STD_LOW  = 0,
    STD_HIGH = 1
} Dio_LevelType;

/* Dio port level - bit-aggregate of all channels on a port (SWS 8.4.4) */
typedef uint16 Dio_PortLevelType;

/* Internal stub: hardware port shadow register (demo only) */
typedef struct {
    Dio_PortLevelType value;
    Dio_PortType      port_id;
} Dio_PortRegister_t;

/*============================================================================*/
/* PUBLIC API PROTOTYPES (per SWS section 8.3 - demo 4-API slice)              */
/*============================================================================*/

/* SWS 8.3.2 - Service ID 0x01 */
extern void Dio_WriteChannel(Dio_ChannelType ChannelId, Dio_LevelType Level);

/* SWS 8.3.1 - Service ID 0x00 */
extern Dio_LevelType Dio_ReadChannel(Dio_ChannelType ChannelId);

/* SWS 8.3.8 - Service ID 0x11 (AUTOSAR 4.x) */
extern Dio_LevelType Dio_FlipChannel(Dio_ChannelType ChannelId);

/* SWS 8.3.7 - Service ID 0x12 */
extern void Dio_GetVersionInfo(Std_VersionInfoType* VersionInfo);

#endif /* DIO_H */
