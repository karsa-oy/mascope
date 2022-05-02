import asyncio

from .errors import ErrorCode
from .messages import APP_CMD_MIN_LEN, APP_RSP_MIN_LEN, ETX, STX


BUFFER_SIZE = 256   # TCP socket reader buffer size limit


class AsyncTCPClient():
    def __init__(self, host: str, port: int) -> None:
        """Asynchronous TCP client

        Client used to transmit
        command messages to KECU.

        Parameters
        ----------
        host : str
            KECU IP address
        port : int
            KECU TCP port
        """
        self._host = host
        self._port = port
        self._reader = None
        self._writer = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def close(self) -> None:
        print("closing the socket")
        # close the socket
        self._writer.close()
        await self._writer.wait_closed()
        # read everything from buffer
        await self._reader.read(-1)
        # no longer connected
        self._connected = False
        # make sure other routines know the socket is closed
        self._reader = self._writer = None

    async def connect(self) -> None:
        print("Connecting to %s:%s..." %(self._host, self._port))
        self._reader, self._writer = await asyncio.open_connection(
                                                    self._host,
                                                    self._port,
                                                    limit=BUFFER_SIZE
                                                    )
        print("Connected!")
        self._connected = True

    async def get_response(self, command: bytes) -> bytes:
        """Read response to command message from the socket.

        Refer to interface specifications for message format.
        """
        # Read response message header, to get payload length
        header = await self._reader.readexactly(3)
        stx, cmd, length = header
        # Read rest of the response message
        status_payload_etx = await self._reader.readexactly(length + 1)
        status = status_payload_etx[0]
        payload = status_payload_etx[1:-1]
        etx = status_payload_etx[-1]
        nbytes = len(header) + len(status_payload_etx)
        # Validate response message format
        if ((nbytes >= APP_RSP_MIN_LEN) and
            (stx == STX) and
            (cmd == command) and
            (nbytes-4 == length) and
            (etx == ETX) and
            (not status)
            ):
            return payload
        # Check for error code
        if status:
            raise Exception( ErrorCode(status) )
        raise Exception
        
    async def send_cmd(self, command: bytes, payload: bytes) -> None:
        """Send command to KECU.

        Refer to interface specifications for message format.
        """
        l = len(payload)
        c = bytearray(APP_CMD_MIN_LEN + l)
        c[0] = STX
        c[1] = command
        c[2] = (l & 0xFF)
        for i in range(0, l):
            c[3+i] = payload[i]
        c[3+l] = ETX

        self._writer.write(c)
        await self._writer.drain()
        
    async def send_cmd_wait_resp(self, command: bytes, payload: bytes) -> str:
        """Send a command message to KECU and wait for response.

        Refer to interface specifications for message formats.
        """
        await self.send_cmd(command, payload)
        return await self.get_response(command)