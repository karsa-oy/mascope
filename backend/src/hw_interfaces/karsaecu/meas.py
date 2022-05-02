from .client import AsyncTCPClient
from .messages import ETX, MIN_MEAS_MSG_SIZE, STX, Notification
from .nodes import NodeId


class KarsaMeasClient(AsyncTCPClient):
    def __init__(self, host, port):
        """TCP measurement client

        Currently no measurement data is transmitted via TCP.
        """
        super().__init__(host, port)

    async def get_data(self) -> bytes:
        # Read start header
        header = await self._reader.readexactly(3)
        stx, type_, length = header
        # Read rest of the msg
        payload_etx = await self._reader.readexactly(length + 1)
        payload = payload_etx[:-1]
        etx = payload_etx[-1]
        nbytes = len(header) + len(payload_etx)
        # Validate message format
        if ((nbytes >= MIN_MEAS_MSG_SIZE) and
            (stx == STX) and
            (nbytes-4 == length) and
            (etx == ETX)
            ):
            node_id = NodeId(payload[0])
            ntf = Notification(type_)
            data = payload[1:]
            return node_id, ntf, data
        print("Failed to read data")