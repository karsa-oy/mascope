from collections import namedtuple
from enum import Enum

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


Device = namedtuple('Device', ['node_id', 'node_type', 'description'])

DEVICE_CFG = [
    # MION
    Device(NodeId.MION_MFC1_SRC1_EXH, NodeType.MFC, "MION MFC1, Source 1 exhaust, vacuum, 100mlpm"),
    Device(NodeId.MION_MFC2_SRC1_CRR, NodeType.MFC, "MION MFC2, Source 1 carrier, pressure, 100mlpm"),
    Device(NodeId.MION_MFC3_SRC2_EXH, NodeType.MFC, "MION MFC3, Source 2 exhaust, vacuum, 100mlpm"),
    Device(NodeId.MION_MFC4_SRC2_CRR, NodeType.MFC, "MION MFC4, Source 2 carrier, pressure, 100mlpm"),
    Device(NodeId.MION_MFC5_MAIN, NodeType.MFC, "MION MFC5, Main flow, vacuum, 50lpm"),
    Device(NodeId.MION_DIO, NodeType.DIO, "MION digital I/O, 4ch in, 4ch out"),
    Device(NodeId.MION_AI, NodeType.AI, "MION analog in, 6ch in"),
    # //
    # Calibrator
    Device(NodeId.CALIB_MFC, NodeType.MFC, "Calibrator sample flow, pressure, 5lpm"),
    # //
    # Flushplate
    Device(NodeId.FLSHP_MFC, NodeType.MFC, "Flush plate counterflow, pressure, 5lpm"),
    # //
    # Scenthound
    Device(NodeId.SH_MFC1_SHT2, NodeType.MFC, "SH MFC1, Sheath 2, pressure, 50lpm"),
    Device(NodeId.SH_MFC2_EXH, NodeType.MFC, "SH MFC2, Exhaust, vacuum, 50lpm"),
    Device(NodeId.SH_MFC3_SMP, NodeType.MFC, "SH MFC3, Sample, pressure, 5lpm"),
    Device(NodeId.SH_MFC4_SHT1, NodeType.MFC, "SH MFC4, Sheath 1, pressure, 5lpm"),
    Device(NodeId.SH_MFC5_RGT, NodeType.MFC, "SH MFC5, reagent, pressure, 100mlpm"),
    Device(NodeId.SH_DIO, NodeType.DIO, "SH digital I/O, 4ch in, 4ch out"),
    Device(NodeId.SH_AI, NodeType.AI, "SH analog in, 6ch in"),
    # //
]

DEVICES = {
    device.node_id: device for device in DEVICE_CFG
}

class BaseNode():
    def __init__(self, client: AsyncTCPClient, device: Device):
        self._client = client
        self._id = device.node_id.value
        self._type = device.node_type.value
        self.__dict__.update(device._asdict())

    async def _start_measurement(self, *args, **kwargs):
        raise NotImplementedError("Subclasses of BaseNode should implement _start_measurement method")

    async def _stop_measurement(self, *args, **kwargs):
        raise NotImplementedError("Subclasses of BaseNode should implement _stop_measurement method")

    async def get_data(self, index, subindex):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(Command.CMD_GET_NODE_DATA.value, payload)

    async def get_device_name(self):
        return await self.get_data(0x1008,
                                   0x00
                                   )

    async def get_hw_version(self):
        return await self.get_data(0x1009,
                                   0x00
                                   )
 
    async def get_sw_version(self):
        return await self.get_data(0x100A,
                                   0x00
                                   )

    async def reset(self):
        payload = bytearray(1)
        payload[0] = self._id
        return await self.send_cmd_wait_resp(Command.CMD_RESET_NODE.value, payload)

    async def set_data(self, index, subindex, data):
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

    async def start_measurement(self, *args, **kwargs):
        return await self._start_measurement(*args, **kwargs)

    async def stop_measurement(self, *args, **kwargs):
        return await self._stop_measurement(*args, **kwargs)


class AiNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device: Device):
        if device.node_type != NodeType.AI:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)
        
    async def _start_measurement(self, channel_mask, interval):
        payload = bytearray(3)
        payload[0] = self._id
        payload[1] = channel_mask
        payload[2] = interval
        return await self._client.send_cmd_wait_resp(Command.CMD_START_AI_MEAS.value, payload)

    async def _stop_measurement(self, channel_mask):
        payload = bytearray(2)
        payload[0] = self._id
        payload[1] = channel_mask
        return await self._client.send_cmd_wait_resp(Command.CMD_STOP_AI_MEAS.value, payload)


class DioNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device: Device):
        if device.node_type != NodeType.DIO:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)

    async def _start_measurement(self, interval):
        payload = bytearray(2)
        payload[0] = self._id
        payload[1] = interval
        return await self._client.send_cmd_wait_resp(Command.CMD_START_DIO_MEAS.value, payload)

    async def _stop_measurement(self):
        payload = bytearray(1)
        payload[0] = self._id
        return await self._client.send_cmd_wait_resp(Command.CMD_STOP_DIO_MEAS.value, payload)


class MfcNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device: Device):
        if device.node_type != NodeType.MFC:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)

    async def _start_measurement(self, index, subindex, interval):
        payload = bytearray(5)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        payload[4] = interval
        return await self._client.send_cmd_wait_resp(Command.CMD_START_MFC_MEAS.value, payload)

    async def _stop_measurement(self, index, subindex):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(Command.CMD_STOP_MFC_MEAS.value, payload)


NODES = {
    NodeType.AI: AiNode,
    NodeType.DIO: DioNode,
    NodeType.MFC: MfcNode,
}