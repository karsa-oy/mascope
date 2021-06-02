import asyncio

KRS_HOST = '192.168.1.200'  # The server's hostname or IP address

BUFFER_SIZE = 256

APP_CMD_MIN_LEN = 4       # STX (1) + CMD (1) + LEN (1) + ETX (1)
APP_RSP_MIN_LEN = 5       # STX (1) + CMD (1) + LEN (1) + STATUS (1) + ETX (1)
STX = 0x02
ETX = 0x03

class AsyncTCPClient():
    def __init__(self, port):
        self._port = port
        self._reader = None
        self._writer = None
        self._connected = False

    async def connect(self):
        print("Connecting")
        self._reader, self._writer = await asyncio.open_connection(
                                                    KRS_HOST,
                                                    self._port,
                                                    limit=BUFFER_SIZE
                                                    )
        print("Connected")
        self._connected = True

    async def sendCmd(self, command, payload):
        l = len(payload)
        c = bytearray(APP_CMD_MIN_LEN + l)
        c[0] = STX
        c[1] = command
        c[2] = (l & 0xFF)
        for i in range(0, l):
            c[3+i] = payload[i]
        c[3+l] = ETX
        try:
            # print("sendCmd: %s" %c)
            self._writer.write(c)
            await self._writer.drain()
            return False
        except Exception as e:
            print(e)
            return True
        
    async def getResp(self, command):
        r1 = await self._reader.read(3)
        stx, cmd, length = r1
        r2 = await self._reader.read(length + 1)
        payload = r2[:-1]
        etx = r2[-1]
        nBytes = len(r1) + len(r2)
        if ( (nBytes >= APP_RSP_MIN_LEN) and
                (stx == STX) and
                (cmd == command) and
                (nBytes-4 == length) and
                (etx == ETX) ):
            # print(nBytes-4, payload)
            return nBytes-4, payload
        return 0, None
        
    async def sendCmdWaitResp(self, command, payload):
        err = await self.sendCmd(command, payload)
        if (not err):
            nBytes, resp = await self.getResp(command)
            if (resp[0] == 0x00):
                if (nBytes == 1):
                    return 0, resp[0:1]
                else:
                    return nBytes-1, resp[1:nBytes]
            else:
                print("Cmd 0x{0:02X} failed, status = 0x{1:02X}".format(command, resp[0]))
                return 0, resp[0:1]
        else:
            print("err")
            return 0, None # internal error

    @property
    def connected(self):
        return self._connected

    def close(self):
        print("closing the socket")
        # close the socket
        self._writer.close()
        # no longer connected
        self._connected = False
        # make sure other routines know the socket is closed
        self._reader = self._writer = None

