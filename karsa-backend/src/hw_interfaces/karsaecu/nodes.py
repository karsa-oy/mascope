import struct

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .client import AsyncTCPClient
from .messages import Command


class NodeId(Enum):
    # Node IDs
    ALL_NODES = 0x00
    # MION
    MION_MFC1_SRC1_EXH = 0x03
    MION_MFC2_SRC1_CRR = 0x04
    MION_MFC3_SRC2_EXH = 0x05
    MION_MFC4_SRC2_CRR = 0x06
    MION_MFC5_MAIN = 0x07
    MION_DIO = 0x09
    MION_AI = 0x0A
    # //
    # Calibrator
    CALIB_MFC = 0x0D
    # //
    # Flushplate
    FLSHP_MFC = 0x0E
    # //
    # Scenthound
    SH_MFC1_SHT2 = 0x10
    SH_MFC2_EXH = 0x11
    SH_MFC3_SMP = 0x12
    SH_MFC4_SHT1 = 0x13
    SH_MFC5_RGT = 0x14
    SH_DIO = 0x15
    SH_AI = 0x16
    # //
    # //


class NodeType(Enum):
    # Node types
    MFC = 0
    DIO = 1
    AI = 2
    UNKNOWN = 255
    # //


@dataclass
class Channel:
    description: str
    callbacks: 'list[Callable]' = field(default_factory=list, init=False)
    value: float = field(default=None, init=False)
    _value: float = field(init=False, repr=False)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        for cb in self.callbacks:
            cb(self.value)


@dataclass
class AiChannel(Channel):
    unit: str = ""
    conversion: Callable[[float], float] = lambda x : x

    voltage: float = field(default=None, init=False)
    _voltage: float = field(init=False, repr=False)

    @property
    def voltage(self) -> float:
        return self._voltage

    @voltage.setter
    def voltage(self, voltage: float):
        self._voltage = voltage
        self.value = self.conversion(voltage)

MION_AI_CHANNELS = [
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x)
]

SH_AI_CHANNELS = [
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x),
    AiChannel("", unit="", conversion=lambda x: x)
]

@dataclass
class DioChannel(Channel):
    io: bool

    value: bool = field(default=None, init=False)
    _value: bool = field(init=False, repr=False)

MION_DIO_CHANNELS = [
    DioChannel("", io=1),
    DioChannel("", io=1),
    DioChannel("", io=1),
    DioChannel("", io=1),
    DioChannel("", io=0),
    DioChannel("", io=0),
    DioChannel("", io=0),
    DioChannel("", io=0),
]

SH_DIO_CHANNELS = [
    DioChannel("", io=1),
    DioChannel("", io=1),
    DioChannel("", io=1),
    DioChannel("", io=1),
    DioChannel("", io=0),
    DioChannel("", io=0),
    DioChannel("", io=0),
    DioChannel("", io=0),
]

@dataclass
class MfcChannel(Channel):
    index: int = None
    subindex: int = None
    settable: bool = None
    unit: str = ""


MFC_CHANNEL_CFG = [
    MfcChannel("Flow setpoint", 0x2F00, 0x01, settable=True),
    MfcChannel("Flow monitor value", 0x2C00, 0x01, settable=False),
    MfcChannel("Medium temperature", 0x2503, 0x01, settable=False, unit="C"),
    MfcChannel("Device status, temperature", 0x2004, 0x02, settable=False, unit="C"),
    MfcChannel("Device status, voltage", 0x2004, 0x03, settable=False, unit="V"),
]

MFC_CHANNELS = dict()
for par in MFC_CHANNEL_CFG:
    MFC_CHANNELS.update({ (par.index, par.subindex): par })



@dataclass(frozen=True)
class Device:
    node_id: NodeId
    description: str

    node_type: NodeId = field(default=NodeType.UNKNOWN, init=False)    


@dataclass(frozen=True)
class AiDevice(Device):
    channels: 'list[AiChannel]'

    node_type = NodeType.AI
    

@dataclass(frozen=True)
class DioDevice(Device):
    channels: 'list[DioChannel]'

    node_type = NodeType.DIO


@dataclass(frozen=True)
class MfcDevice(Device):
    flow_unit: str

    node_type = NodeType.MFC
    parameters = MFC_CHANNELS



DEVICE_CFG = [
    # MION
    MfcDevice(NodeId.MION_MFC1_SRC1_EXH, "MION MFC1, Source 1 exhaust, vacuum, 100mlpm", flow_unit="mlpm"),
    MfcDevice(NodeId.MION_MFC2_SRC1_CRR, "MION MFC2, Source 1 carrier, pressure, 100mlpm", flow_unit="mlpm"),
    MfcDevice(NodeId.MION_MFC3_SRC2_EXH, "MION MFC3, Source 2 exhaust, vacuum, 100mlpm", flow_unit="mlpm"),
    MfcDevice(NodeId.MION_MFC4_SRC2_CRR, "MION MFC4, Source 2 carrier, pressure, 100mlpm", flow_unit="mlpm"),
    MfcDevice(NodeId.MION_MFC5_MAIN, "MION MFC5, Main flow, vacuum, 50lpm", flow_unit="lpm"),
    DioDevice(NodeId.MION_DIO, "MION digital I/O, 4ch in, 4ch out", MION_DIO_CHANNELS),
    AiDevice(NodeId.MION_AI, "MION analog in, 6ch in", MION_AI_CHANNELS),
    # //
    # Calibrator
    MfcDevice(NodeId.CALIB_MFC, "Calibrator sample flow, pressure, 5lpm", flow_unit="lpm"),
    # //
    # Flushplate
    MfcDevice(NodeId.FLSHP_MFC, "Flush plate counterflow, pressure, 5lpm", flow_unit="lpm"),
    # //
    # Scenthound
    MfcDevice(NodeId.SH_MFC1_SHT2, "SH MFC1, Sheath 2, pressure, 50lpm", flow_unit="lpm"),
    MfcDevice(NodeId.SH_MFC2_EXH, "SH MFC2, Exhaust, vacuum, 50lpm", flow_unit="lpm"),
    MfcDevice(NodeId.SH_MFC3_SMP, "SH MFC3, Sample, pressure, 5lpm", flow_unit="lpm"),
    MfcDevice(NodeId.SH_MFC4_SHT1, "SH MFC4, Sheath 1, pressure, 5lpm", flow_unit="lpm"),
    MfcDevice(NodeId.SH_MFC5_RGT, "SH MFC5, reagent, pressure, 100mlpm", flow_unit="mlpm"),
    DioDevice(NodeId.SH_DIO, "SH digital I/O, 4ch in, 4ch out", SH_DIO_CHANNELS),
    AiDevice(NodeId.SH_AI, "SH analog in, 6ch in", SH_AI_CHANNELS),
    # //
]

DEVICES = {
    device.node_id: device for device in DEVICE_CFG
}


class BaseNode():
    def __init__(self, client: AsyncTCPClient, device: Device):
        self._client = client
        self._device = device
        self._id = device.node_id.value
        self._type = device.node_type.value

    async def _get_data(self, index: int, subindex: int):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(Command.CMD_GET_NODE_DATA.value, payload)

    async def _set_data(self, index: int, subindex: int, data):
        l = len(data)
        payload = bytearray(4+l)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        for i in range(0, l):
            payload[4+i] = data & 0xFF
            data >>= 8
        return await self._client.send_cmd_wait_resp(Command.CMD_SET_NODE_DATA.value, payload)

    async def _start_measurement(self, *args, **kwargs):
        raise NotImplementedError("Subclasses of BaseNode should implement _start_measurement method")

    async def _stop_measurement(self, *args, **kwargs):
        raise NotImplementedError("Subclasses of BaseNode should implement _stop_measurement method")

    async def get_device_name(self):
        return await self._get_data(0x1008,
                                    0x00
                                    )

    async def get_hw_version(self):
        return await self._get_data(0x1009,
                                    0x00
                                    )
 
    async def get_sw_version(self):
        return await self._get_data(0x100A,
                                    0x00
                                    )

    async def reset(self):
        payload = bytearray(1)
        payload[0] = self._id
        return await self._client.send_cmd_wait_resp(Command.CMD_RESET_NODE.value, payload)

    async def start_measurement(self, *args, **kwargs):
        return await self._start_measurement(*args, **kwargs)

    async def stop_measurement(self, *args, **kwargs):
        return await self._stop_measurement(*args, **kwargs)


class AiNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device: AiDevice):
        if device.node_type != NodeType.AI:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)
        
    async def _start_measurement(self, interval: int):
        payload = bytearray(3)
        payload[0] = self._id
        payload[1] = 0x03 # Channel mask, start measurement on all channels
        payload[2] = interval
        return await self._client.send_cmd_wait_resp(Command.CMD_START_AI_MEAS.value, payload)

    async def _stop_measurement(self):
        payload = bytearray(2)
        payload[0] = self._id
        payload[1] = 0x03 # Channel mask, stop measurement on all channels
        return await self._client.send_cmd_wait_resp(Command.CMD_STOP_AI_MEAS.value, payload)

    async def on_NTF_AI_MEAS_DATA_CH_1_4(self, data):
        if len(data) != 8:
            raise Exception("Invalid payload")
        for i, d in enumerate( range(0, len(data), 2) ):
            ch_index = i
            ch_value_b = data[d:d+1]
            value = struct.unpack('h', ch_value_b) # Signed16
            self._device.channels[ch_index].voltage = value
            print("AI Channel %s: %.4f" %(ch_index, value))

    async def on_NTF_AI_MEAS_DATA_CH_5_6(self, data):
        if len(data) != 4:
            raise Exception("Invalid payload")
        for i, d in enumerate( range(0, len(data), 2) ):
            ch_index = i + 4
            ch_value_b = data[d:d+1]
            value = struct.unpack('h', ch_value_b) # Signed16
            self._device.channels[ch_index].voltage = value
            print("AI Channel %s: %.4f" %(ch_index, value))


class DioNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device: DioDevice):
        if device.node_type != NodeType.DIO:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)

    async def _start_measurement(self, interval: int):
        payload = bytearray(2)
        payload[0] = self._id
        payload[1] = interval
        return await self._client.send_cmd_wait_resp(Command.CMD_START_DIO_MEAS.value, payload)

    async def _stop_measurement(self):
        payload = bytearray(1)
        payload[0] = self._id
        return await self._client.send_cmd_wait_resp(Command.CMD_STOP_DIO_MEAS.value, payload)

    async def on_NTF_DIO_MEAS_DATA(self, data):
        if len(data) != 1:
            raise Exception("Invalid payload")
        # Convert byte to int
        data_int = int.from_bytes(data, byteorder='little')
        # Unpack byte into bit string
        bit_string = format(data_int, '08b')
        for i, bit in enumerate(bit_string):
            self._device.channels[i].value = bool(int(bit))


class MfcNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device: MfcDevice):
        if device.node_type != NodeType.MFC:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)

    async def _start_measurement(self, index: int, subindex: int, interval: int):
        payload = bytearray(5)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        payload[4] = interval
        return await self._client.send_cmd_wait_resp(Command.CMD_START_MFC_MEAS.value, payload)

    async def _stop_measurement(self, index=0x0000, subindex=0x00):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(Command.CMD_STOP_MFC_MEAS.value, payload)

    async def on_NTF_MFC_MEAS_DATA(self, data):
        if len(data) < 4 or len(data) > 8:
            raise Exception("Invalid payload")
        index_b = data[0:2]
        index_int = int.from_bytes(index_b, byteorder='little', signed=False)
        subindex_b = data[2]
        subindex_int = int.from_bytes(subindex_b, byteorder='little', signed=False)
        value_b = data[3:]
        if len(value_b) == 1:
            raise NotImplementedError("on_NTF_MFC_MEAS_DATA: length 1 not supported")
        elif len(value_b) == 2:
            # Unsigned16
            dtype = 'H'
        elif len(value_b) == 3:
            raise NotImplementedError("on_NTF_MFC_MEAS_DATA: length 3 not supported")
        elif len(value_b) == 4:
            # Real32
            dtype = 'f'
        value = struct.unpack(dtype, value_b)
        self._device.parameters[(index_int, subindex_int)].value = value
        print("MFC Parameter %s: %.4f" %(self._device.parameters[index_int][subindex_int].description, value))



NODES = {
    NodeType.AI: AiNode,
    NodeType.DIO: DioNode,
    NodeType.MFC: MfcNode,
}