import asyncio

from .errors import ErrorCode
from .messages import APP_CMD_MIN_LEN, APP_RSP_MIN_LEN, ETX, STX

KRS_HOST = '192.168.1.200'  # KECU IP

BUFFER_SIZE = 256   # TCP socket reader buffer size limit


class AsyncTCPClient():
    def __init__(self, port: int) -> None:
        self._port = port
        self._reader = None
        self._writer = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def close(self) -> None:
        print("closing the socket")
        # close the socket
        self._writer.close()
        # no longer connected
        self._connected = False
        # make sure other routines know the socket is closed
        self._reader = self._writer = None

    async def connect(self) -> None:
        print("Connecting to %s:%s..." %(KRS_HOST, self._port))
        self._reader, self._writer = await asyncio.open_connection(
                                                    KRS_HOST,
                                                    self._port,
                                                    limit=BUFFER_SIZE
                                                    )
        print("Connected!")
        self._connected = True

    async def get_response(self, command: bytes) -> str:
        """Read response to command message from the socket.

        Parameters
        ----------
        command : bytes
            Command to which expecting response

        Returns
        -------
        str
            Response message payload converted to string
        """
        # Read response message header, to get payload length
        header = await self._reader.read(3)
        stx, cmd, length = header
        # Read rest of the response message
        status_payload_etx = await self._reader.read(length + 1)
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
            return payload.decode('utf-8')
        # Check for error code
        if status:
            raise Exception( ErrorCode(status) )
        raise Exception
        
    async def send_cmd(self, command: bytes, payload: bytes) -> None:
        """[summary]

        Parameters
        ----------
        command : bytes
            [description]
        payload : bytes
            [description]
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
        """[summary]

        Parameters
        ----------
        command : bytes
            [description]
        payload : bytes
            [description]

        Returns
        -------
        str
            [description]
        """
        await self.send_cmd(command, payload)
        return await self.get_response(command)
