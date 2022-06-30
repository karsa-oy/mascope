import struct
from enum import Enum

from .client import AsyncTCPClient
from .messages import Command

import logging
logger = logging.getLogger(__name__)


class NodeId(Enum):
    """CAN node IDs

    Refer to interface specifications
    """
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
    # MION1v5
    MION1v5_DIO = 0x0F
    # //
    # MION2
    # Core
    MION2_MFC_MAIN = 0x17
    MION2_DIO_XRAY_ON = 0x18
    MION2_DIO_XRAY_ALERT = 0x19
    MION2_DIO_XRAY_CTRL = 0x1A
    MION2_AI = 0x1B
    # //
    # Flows & valves
    MION2_MFC_SRC1_PRG = 0x1C
    MION2_MFC_SRC1_RGT = 0x1D
    MION2_MFC_SRC1_EXH = 0x1E
    MION2_SRC1_VALVE = 0x1F

    MION2_MFC_SRC2_PRG = 0x20
    MION2_MFC_SRC2_RGT = 0x21
    MION2_MFC_SRC2_EXH = 0x22
    MION2_SRC2_VALVE = 0x23

    MION2_MFC_SRC3_PRG = 0x24
    MION2_MFC_SRC3_RGT = 0x25
    MION2_MFC_SRC3_EXH = 0x26
    MION2_SRC3_VALVE = 0x27

    MION2_MFC_SRC4_PRG = 0x28
    MION2_MFC_SRC4_RGT = 0x29
    MION2_MFC_SRC4_EXH = 0x2A
    MION2_SRC4_VALVE = 0x2B

    MION2_MFC_SRC5_PRG = 0x2C
    MION2_MFC_SRC5_RGT = 0x2D
    MION2_MFC_SRC5_EXH = 0x2E
    MION2_SRC5_VALVE = 0x2F

    MION2_MFC_SRC6_PRG = 0x30
    MION2_MFC_SRC6_RGT = 0x31
    MION2_MFC_SRC6_EXH = 0x32
    MION2_SRC6_VALVE = 0x33
    # //
    # HV
    MION2_SRC1_HV = 0x34
    MION2_SRC2_HV = 0x35
    MION2_SRC3_HV = 0x36
    MION2_SRC4_HV = 0x37
    MION2_SRC5_HV = 0x38
    MION2_SRC6_HV = 0x39
    # //
    # ESI
    MION2_SRC1_ESIP = 0x3A
    MION2_SRC2_ESIP = 0x3B
    MION2_SRC3_ESIP = 0x3C
    MION2_SRC4_ESIP = 0x3D
    MION2_SRC5_ESIP = 0x3E
    MION2_SRC6_ESIP = 0x3F
    # //
    # //


class NodeType(Enum):
    """CAN node types

    Refer to interface specifications
    """
    MFC = 0
    DIO = 1
    AI = 2
    VALVE = 3
    HV = 4
    UNKNOWN = 255


class BaseNode():
    def __init__(self, client: AsyncTCPClient, device):
        """Base class for a CAN node for connecting with a device

        Implements methods for reading and sending commands, as well as
        convenience methods for common operations.

        Parameters
        ----------
        client : AsyncTCPClient
            Kecu client
        device : Device
            Device object for which the node is to be created
        """
        self._client = client
        self._device = device
        self._id = device.node_id.value

    @property
    def node_id(self):
        return self._device.node_id.value

    @property
    def node_type(self):
        return self._device.node_type.value

    async def _get_data(self, index: int, subindex: int):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(
            Command.CMD_GET_NODE_DATA.value,
            payload
            )

    async def _initialize(self):
        raise NotImplementedError(
            "Subclasses of BaseNode should implement _initialize method"
            )

    async def _set_data(self, index: int, subindex: int, data):

        logger.debug(f'- set_data {index}, {subindex}, {data}')

        l = len(data)
        payload = bytearray(4+l)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        # for i in range(0, l):
        #     payload[4+i] = data & 0xFF
        #     data >>= 8
        payload[4:] = data
        return await self._client.send_cmd_wait_resp(
            Command.CMD_SET_NODE_DATA.value,
            payload
            )

    async def _start_measurement(self, *args, **kwargs):
        raise NotImplementedError(
            "Subclasses of BaseNode should implement _start_measurement method"
            )

    async def _stop_measurement(self, *args, **kwargs):
        raise NotImplementedError(
            "Subclasses of BaseNode should implement _stop_measurement method"
            )

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

    async def initialize(self, *args, **kwargs):
        logger.info("Initializing node %s" %self._device.description)
        return await self._initialize(*args, **kwargs)

    async def reset(self):
        payload = bytearray(1)
        payload[0] = self._id
        return await self._client.send_cmd_wait_resp(
            Command.CMD_RESET_NODE.value,
            payload
            )

    async def start_measurement(self, *args, **kwargs):
        return await self._start_measurement(*args, **kwargs)

    async def stop_measurement(self, *args, **kwargs):
        return await self._stop_measurement(*args, **kwargs)


class AiNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device):
        """Analog input node
        """
        if device.node_type != NodeType.AI:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)
        
    async def _initialize(self):
        await self.start_measurement(
            interval=10
            )

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
        """Handler for measurement data notification

        Refer to interface specifications
        """
        if len(data) != 8:
            raise Exception("Invalid payload")
        for i, d in enumerate( range(0, len(data), 2) ):
            ch_index = i
            ch_value_b = data[d:d+2]
            value_int = struct.unpack('h', ch_value_b)[0] # Signed16
            value = value_int * 1e-3
            self._device.channels[ch_index].voltage = value

    async def on_NTF_AI_MEAS_DATA_CH_5_6(self, data):
        """Handler for measurement data notification

        Refer to interface specifications
        """
        if len(data) != 4:
            raise Exception("Invalid payload")
        for i, d in enumerate( range(0, len(data), 2) ):
            ch_index = i + 4
            ch_value_b = data[d:d+2]
            value_int = struct.unpack('h', ch_value_b)[0] # Signed16
            value = value_int * 1e-3
            self._device.channels[ch_index].voltage = value

class DioNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device):
        """Digital in/out node
        """
        if device.node_type != NodeType.DIO:
            raise TypeError("Tried to initialize %s for device of type %s" %(self, device.node_type))
        super().__init__(client, device)

    async def _initialize(self):
        await self.start_measurement(
            interval=10
            )

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
        """Handler for measurement data notification

        Refer to interface specifications
        """
        if len(data) != 1:
            raise Exception("Invalid payload")
        # Convert byte to int
        data_int = int.from_bytes(data, byteorder='little')
        # Unpack byte into bit string
        bit_string = format(data_int, '08b')[::-1] # Reverse bit order
        for i, bit in enumerate(bit_string):
            self._device.channels[i].state = bool(int(bit))

    async def set_channel(self, channel_index, value):
        self._device.channels[channel_index].value = value
        binary_string = ''.join([
            '%i' %ch.value
            for _, ch in self._device.channels.items()
            ])[::-1]
        payload = int(binary_string, 2).to_bytes(len(binary_string) // 8, byteorder='little')
        return await self._set_data(0x6200, 0x01, payload) # Flow setpoint

class MfcNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device):
        """Mass flow controller node
        """
        if device.node_type != NodeType.MFC:
            raise TypeError(
                "Tried to initialize %s for device of type %s"
                %(self, device.node_type)
                )
        super().__init__(client, device)

    async def _initialize(self):
        await self.start_measurement(
            index=0x2F00,
            subindex=0x01,
            interval=10
            ) # Flow setpoint
        await self.start_measurement(
            index=0x2C00,
            subindex=0x01,
            interval=10
            ) # Flow monitor

    async def _start_measurement(self, index: int, subindex: int, interval: int):
        payload = bytearray(5)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        payload[4] = interval
        return await self._client.send_cmd_wait_resp(
            Command.CMD_START_MFC_MEAS.value,
            payload
            )

    async def _stop_measurement(self, index=0x0000, subindex=0x00):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(
            Command.CMD_STOP_MFC_MEAS.value,
            payload
            )

    async def on_NTF_MFC_MEAS_DATA(self, data):
        """Handler for measurement data notification

        Refer to interface specifications
        """
        if len(data) < 4 or len(data) > 8:
            raise Exception("Invalid payload")
        index_b = data[0:2]
        index_int = int.from_bytes(
            index_b,
            byteorder='little',
            signed=False
            )
        subindex_b = data[2:3]
        subindex_int = int.from_bytes(
            subindex_b,
            byteorder='little',
            signed=False
            )
        value_b = data[3:]
        if len(value_b) == 1:
            raise NotImplementedError(
                "on_NTF_MFC_MEAS_DATA: length 1 not supported"
                )
        elif len(value_b) == 2:
            # Unsigned16
            dtype = 'H'
        elif len(value_b) == 3:
            raise NotImplementedError(
                "on_NTF_MFC_MEAS_DATA: length 3 not supported"
                )
        elif len(value_b) == 4:
            # Real32
            dtype = 'f'
        value = struct.unpack(dtype, value_b)[0]
        self._device.channels[(index_int, subindex_int)].value = value

    async def set_flow(self, value):
        payload = struct.pack('f', value) # Real32
        return await self._set_data(0x2F00, 0x01, payload) # Flow setpoint

class ValveNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device):
        """Valve node"""
        if device.node_type != NodeType.VALVE:
            raise TypeError(
                "Tried to initialize %s for device of type %s"
                %(self, device.node_type)
                )
        super().__init__(client, device)

    async def _initialize(self):
        await self.start_measurement(
            index=0x2500,
            interval=10
            ) # Valve output
        await self.start_measurement(
            index=0x2540,
            interval=10
            ) # Valve input

    async def _start_measurement(self, index: int, interval: int):
        subindex = 0x01
        payload = bytearray(5)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        payload[4] = interval
        return await self._client.send_cmd_wait_resp(
            Command.CMD_START_VALVE_MEAS.value,
            payload
            )

    async def _stop_measurement(self, index=0x0000, subindex=0x00):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(
            Command.CMD_STOP_VALVE_MEAS.value,
            payload
            )

    async def set_channel(self, channel, state):
        payload = struct.pack('B', state) # Uint32
        return await self._set_data(0x2540, 0x01, payload) # Valve state

    async def on_NTF_VALVE_MEAS_DATA(self, data):
        """Handler for measurement data notification

        Refer to interface specifications
        """
        if len(data) < 4 or len(data) > 7:
            raise Exception("Invalid payload")
        index_b = data[0:2]
        index_int = int.from_bytes(
            index_b,
            byteorder='little',
            signed=False
            )
        subindex_b = data[2:3]
        subindex_int = int.from_bytes(
            subindex_b,
            byteorder='little',
            signed=False
            )
        value_b = data[3:]
        if len(value_b) > 1 and len(value_b) < 4:
            raise ValueError("on_NTF_VALVE_MEAS_DATA: invalid data")
        elif len(value_b) == 1:
            # Uint8
            dtype = 'B'
        elif len(value_b) == 4:
            # Real32
            dtype = 'f'
        value = struct.unpack(dtype, value_b)[0]
        self._device.channels[(index_int, subindex_int)].value = value

class HvNode(BaseNode):
    def __init__(self, client: AsyncTCPClient, device):
        """High-voltage supply node"""
        if device.node_type != NodeType.HV:
            raise TypeError(
                "Tried to initialize %s for device of type %s"
                %(self, device.node_type)
                )
        super().__init__(client, device)

    async def _initialize(self):
        await self.get_voltage_scale()
        await self.start_measurement(
            index=0x7130,
            interval=10
            ) # Voltage monitor
        await self.start_measurement(
            index=0x7300,
            interval=10
            ) # Voltage setpoint

    async def _start_measurement(self, index: int, interval: int):
        payload = bytearray(5)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = 0x07 # Channel mask, start measurement on all channels
        payload[4] = interval
        return await self._client.send_cmd_wait_resp(
            Command.CMD_START_HV_MEAS.value,
            payload
            )

    async def _stop_measurement(self, index=0x0000, subindex=0x07):
        payload = bytearray(4)
        payload[0] = self._id
        payload[1] = (index & 0xFF)
        payload[2] = (index >> 8)
        payload[3] = subindex
        return await self._client.send_cmd_wait_resp(
            Command.CMD_STOP_HV_MEAS.value,
            payload
            )

    async def get_voltage_scale(self):
        for channel in range(1, 4):
            value_b = await self._get_data(0x2000, channel)
            value = struct.unpack('h', value_b)[0] # unsigned short
            self._device.channels[(0x7300, channel)].scaling_factor = (
                value/1000.0
                ) # [V]
            self._device.channels[(0x7130, channel)].scaling_factor = (
                value/1000.0
                ) # [V]

    async def set_voltage(self, channel, value):
        # Scale value given in [V] correctly
        value /= self._device.channels[(0x7130, channel)].scaling_factor
        payload = struct.pack('h', int(value)) # unsigned short
        return await self._set_data(0x7300, channel, payload) # Voltage setpoint

    async def on_NTF_HV_MEAS_DATA(self, data):
        """Handler for measurement data notification

        Refer to interface specifications
        """
        if len(data) != 5:
            raise Exception("Invalid payload")
        index_b = data[0:2]
        index_int = int.from_bytes(
            index_b,
            byteorder='little',
            signed=False
            )
        channel_b = data[2:3]
        subindex_int = int.from_bytes(
            channel_b,
            byteorder='little',
            signed=False
            )
        value_b = data[3:]
        if len(value_b) != 2:
            raise ValueError("on_NTF_HV_MEAS_DATA: invalid value")
        value = struct.unpack('h', value_b)[0]
        self._device.channels[(index_int, subindex_int)].voltage = value


# Export
NODES = {
    NodeType.AI: AiNode,
    NodeType.DIO: DioNode,
    NodeType.MFC: MfcNode,
    NodeType.VALVE: ValveNode,
    NodeType.HV: HvNode,
}
