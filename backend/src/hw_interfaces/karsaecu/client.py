import asyncio

from .errors import ErrorCode
from .messages import APP_CMD_MIN_LEN, APP_RSP_MIN_LEN, ETX, STX

import logging
logger = logging.getLogger(__name__)

BUFFER_SIZE = 256   # TCP socket reader buffer size limit


class AsyncTCPClient():
    def __init__(self, host: str, port: int, parent=None) -> None:
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
        self.kecu = parent
        self._reader = None
        self._writer = None
        self._connected = False
        self.is_broken = False      # TODO: for RCP bug workaround
        self._lock = parent and parent.lock or asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    async def close(self) -> None:
        # no longer connected
        self._connected = False
        # close the socket
        self._writer.close()
        await self._writer.wait_closed()
        # read everything from buffer
        await self._reader.read(-1)
        # make sure other routines know the socket is closed
        self._reader = None
        self._writer = None
        logger.info('Client was closed')

    async def connect(self) -> None:
        logger.info("Connecting to %s:%s..." %(self._host, self._port))
        try:
            self._reader, self._writer = await asyncio.open_connection(
                                                        self._host,
                                                        self._port,
                                                        limit=BUFFER_SIZE
                                                        )
        except Exception as e:
            logger.error(f'{e.__class__.__name__} : {str(e)}')
        if not self._reader or not self._writer:
            logger.error('Connection failed!')
            self._connected = False
        else:
            logger.info("Connected!")
            self.is_broken = False
            self._connected = True

    # TODO: RCP bug workaround
    async def simulate_RCP_bug(self):
        async with self._lock:
            self.is_broken = True

    async def reconnect(self, timeout):
        await self.close()
        await asyncio.sleep(timeout)
        await self.connect()


    async def get_response(self, command: bytes) -> bytes:
        """Read response to command message from the socket.

        Refer to interface specifications for message format.
        """
        # Read response message header, to get payload length

        # workaround for RCP bug
        try:
            if self.is_broken:
                logger.info(f'- get_response {command} was dropped: client not ready')
                return b''
            header = await asyncio.wait_for(self._reader.readexactly(3), 2)
            stx, cmd, length = header
            # Read rest of the response message
            status_payload_etx = await asyncio.wait_for(self._reader.readexactly(length + 1), 2)
        except Exception as e:
            logger.exception('get_response exception: RCP bug?')
            self.is_broken = True
            return b''

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
        logger.error(f"get_response malformed data: status {status and ErrorCode(status)}", exc_info=1)
        return b''
        
    async def send_cmd(self, command: bytes, payload: bytes) -> None:
        """Send command to KECU.

        Refer to interface specifications for message format.
        """

        # TODO: RCP bug workaround
        if self.is_broken:
            logger.info(f'- send_cmd {command} was dropped: client not ready')
            return False

        logger.debug(f'- send_cmd {command}')
        l = len(payload)
        c = bytearray(APP_CMD_MIN_LEN + l)
        c[0] = STX
        c[1] = command
        c[2] = (l & 0xFF)
        for i in range(0, l):
            c[3+i] = payload[i]
        c[3+l] = ETX

        try:
            self._writer.write(c)
            await self._writer.drain()
        except Exception as e:
            logger.exception(f'- send_cmd {command} was dropped:')
            return False
        logger.debug(f'- send_cmd {command} done')
        return True


    async def send_cmd_wait_resp(self, command: bytes, payload: bytes) -> str:
        """Send a command message to KECU and wait for response.

        Refer to interface specifications for message formats.
        """
        async with self._lock:
            if await self.send_cmd(command, payload):
                return await self.get_response(command)
            else:
                return b''
