from dataclasses import dataclass, field

from . import channels
from .nodes import NodeId, NodeType


@dataclass(frozen=True)
class Device:
    """Device base class

    Abstraction of a physical device with specified configuration
    at a certain node.
    Holds a number of channels, representing inputs and outputs 
    of the device.
    """
    node_id: NodeId
    description: str
    node_type: NodeType = field(default=NodeType.UNKNOWN, init=False)    


@dataclass(frozen=True)
class AiDevice(Device):
    channels: 'list[channels.AiChannel]'
    node_type = NodeType.AI
    

@dataclass(frozen=True)
class DioDevice(Device):
    channels: 'list[channels.DioChannel]'
    node_type = NodeType.DIO


@dataclass(frozen=True)
class MfcDevice(Device):
    flow_unit: str
    channels: 'dict[channels.MfcChannel]' = field(default=None)
    node_type = NodeType.MFC

@dataclass(frozen=True)
class ValveDevice(Device):
    channels: 'dict[channels.ValveChannel]' = field(default=None)
    node_type = NodeType.VALVE

@dataclass(frozen=True)
class HvDevice(Device):
    channels: 'dict[channels.HvChannel]' = field(default=None)
    node_type = NodeType.HV


DEVICE_CFG = [
    # MION1
    MfcDevice(
        NodeId.MION_MFC1_SRC1_EXH,
        "MION MFC1, Source 1 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION_MFC2_SRC1_CRR,
        "MION MFC2, Source 1 carrier, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION_MFC3_SRC2_EXH,
        "MION MFC3, Source 2 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION_MFC4_SRC2_CRR,
        "MION MFC4, Source 2 carrier, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION_MFC5_MAIN,
        "MION MFC5, Main flow, vacuum, 50lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    DioDevice(
        NodeId.MION_DIO,
        "MION digital I/O, 4ch in, 4ch out",
        channels.MION_DIO_CHANNELS()
        ),
    AiDevice(
        NodeId.MION_AI,
        "MION analog in, 6ch in",
        channels.MION_AI_CHANNELS()
        ),
    # //
    # Calibrator
    MfcDevice(
        NodeId.CALIB_MFC,
        "Calibrator sample flow, pressure, 5lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    # //
    # Flushplate
    MfcDevice(
        NodeId.FLSHP_MFC,
        "Flush plate counterflow, pressure, 5lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    # //
    # Scenthound
    MfcDevice(
        NodeId.SH_MFC1_SHT2,
        "SH MFC1, Sheath 2, pressure, 50lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.SH_MFC2_EXH,
        "SH MFC2, Exhaust, vacuum, 50lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.SH_MFC3_SMP,
        "SH MFC3, Sample, pressure, 5lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.SH_MFC4_SHT1,
        "SH MFC4, Sheath 1, pressure, 5lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.SH_MFC5_RGT,
        "SH MFC5, reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    DioDevice(
        NodeId.SH_DIO,
        "SH digital I/O, 4ch in, 4ch out",
        channels.SH_DIO_CHANNELS()
        ),
    AiDevice(
        NodeId.SH_AI,
        "SH analog in, 6ch in",
        channels.SH_AI_CHANNELS()
        ),
    # //
    # MION1v5
    DioDevice(
        NodeId.MION1v5_DIO,
        "MION1.5 digital I/O, 4ch in, 4ch out",
        channels.MION1v5_DIO_CHANNELS()
        ),
    # //
    # MION2
    MfcDevice(
        NodeId.MION2_MFC_MAIN,
        "MION2, Main flow, vacuum, 50lpm",
        flow_unit="lpm",
        channels=channels.MFC_CHANNELS()
        ),
    DioDevice(
        NodeId.MION2_DIO_XRAY_ON,
        "MION2 x-ray on input",
        channels.MION2_DIO_XRAY_ON_CHANNELS()
        ),
    DioDevice(
        NodeId.MION2_DIO_XRAY_ALERT,
        "MION2 x-ray alert input",
        channels.MION2_DIO_XRAY_ALERT_CHANNELS()
        ),
    DioDevice(
        NodeId.MION2_DIO_XRAY_CTRL,
        "MION2 x-ray on/off control",
        channels.MION2_DIO_XRAY_CTRL_CHANNELS()
        ),
    AiDevice(
        NodeId.MION2_AI,
        "MION2 analog in, 6ch in",
        channels.MION2_AI_CHANNELS()
        ),

    MfcDevice(
        NodeId.MION2_MFC_SRC1_PRG,
        "MION2, Source 1 purge, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC1_RGT,
        "MION2, Source 1 reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC1_EXH,
        "MION2, Source 1 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    ValveDevice(
        NodeId.MION2_SRC1_VALVE,
        "MION2, Source 1 reagent valve",
        channels=channels.VALVE_CHANNELS()
        ),

    MfcDevice(
        NodeId.MION2_MFC_SRC2_PRG,
        "MION2, Source 2 purge, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC2_RGT,
        "MION2, Source 2 reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC2_EXH,
        "MION2, Source 2 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    ValveDevice(
        NodeId.MION2_SRC2_VALVE,
        "MION2, Source 2 reagent valve",
        channels=channels.VALVE_CHANNELS()
        ),
    
    MfcDevice(
        NodeId.MION2_MFC_SRC3_PRG,
        "MION2, Source 3 purge, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC3_RGT,
        "MION2, Source 3 reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC3_EXH,
        "MION2, Source 3 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    ValveDevice(
        NodeId.MION2_SRC3_VALVE,
        "MION2, Source 3 reagent valve",
        channels=channels.VALVE_CHANNELS()
        ),
    
    MfcDevice(
        NodeId.MION2_MFC_SRC4_PRG,
        "MION2, Source 4 purge, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC4_RGT,
        "MION2, Source 4 reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC4_EXH,
        "MION2, Source 4 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    ValveDevice(
        NodeId.MION2_SRC4_VALVE,
        "MION2, Source 4 reagent valve",
        channels=channels.VALVE_CHANNELS()
        ),
    
    MfcDevice(
        NodeId.MION2_MFC_SRC5_PRG,
        "MION2, Source 5 purge, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC5_RGT,
        "MION2, Source 5 reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC5_EXH,
        "MION2, Source 5 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    ValveDevice(
        NodeId.MION2_SRC5_VALVE,
        "MION2, Source 5 reagent valve",
        channels=channels.VALVE_CHANNELS()
        ),
    
    MfcDevice(
        NodeId.MION2_MFC_SRC6_PRG,
        "MION2, Source 6 purge, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC6_RGT,
        "MION2, Source 6 reagent, pressure, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    MfcDevice(
        NodeId.MION2_MFC_SRC6_EXH,
        "MION2, Source 6 exhaust, vacuum, 100mlpm",
        flow_unit="mlpm",
        channels=channels.MFC_CHANNELS()
        ),
    ValveDevice(
        NodeId.MION2_SRC6_VALVE,
        "MION2, Source 6 reagent valve",
        channels=channels.VALVE_CHANNELS()
        ),

    HvDevice(
        NodeId.MION2_SRC1_HV,
        "MION2 Source 1 HV",
        channels=channels.HV_CHANNELS()
        ),
    HvDevice(
        NodeId.MION2_SRC2_HV,
        "MION2 Source 2 HV",
        channels=channels.HV_CHANNELS()
        ),
    HvDevice(
        NodeId.MION2_SRC3_HV,
        "MION2 Source 3 HV",
        channels=channels.HV_CHANNELS()
        ),
    HvDevice(
        NodeId.MION2_SRC4_HV,
        "MION2 Source 4 HV",
        channels=channels.HV_CHANNELS()
        ),
    HvDevice(
        NodeId.MION2_SRC5_HV,
        "MION2 Source 5 HV",
        channels=channels.HV_CHANNELS()
        ),
    HvDevice(
        NodeId.MION2_SRC6_HV,
        "MION2 Source 6 HV",
        channels=channels.HV_CHANNELS()
        ),
    # //
]

# Export
DEVICES = {
    device.node_id: device for device in DEVICE_CFG
}