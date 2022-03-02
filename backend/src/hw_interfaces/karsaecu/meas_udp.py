import asyncio
import asyncio_dgram

from messages import ETX, MIN_MEAS_MSG_SIZE, STX, Notification
from nodes import NodeId


class KarsaMeasClientUDP():
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._stream = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self):
        self._stream = await asyncio_dgram.bind(
                            (self._host, self._port)
                            )
        self._connected = True

    async def close(self):
        self._stream.close()
        self._stream = None
        self._connected = False

    async def get_data(self) -> bytes:
        data, remote_addr = await self._stream.recv()
        stx = data[0]
        type_ = data[1]
        length = data[2]
        payload = data[3:-1]
        etx = data[-1]
        # Validate message format
        if ((len(data) >= MIN_MEAS_MSG_SIZE) and
            (stx == STX) and
            (len(payload) == length) and
            (etx == ETX)
            ):
            node_id = NodeId(payload[0])
            ntf = Notification(type_)
            data = payload[1:]
            print(node_id, ntf, data)
            return node_id, ntf, data
        raise Exception("Failed to read data")