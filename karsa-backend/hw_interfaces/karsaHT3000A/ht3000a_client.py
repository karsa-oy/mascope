import asyncio
import struct

HTA_HOST = '192.168.1.207'  # The server's hostname or IP address
HTA_PORT = 20101

STX = 0x24  # start frame byte ($)
ETX = 0x0D  # end frame byte (CR)

CMD_MIN_LEN = 18 # STX (1) + op-code (2) + error (4) + status (4) + length (4) + checksum (2) + ETX (1)
RSP_MIN_LEN = 20 # STX (1) + op-code (2) + error (4) + status (4) + length (4) + payload (>=2) + checksum (2) + ETX (1)


class AsyncTCPClient():
    def __init__(self):
        self._reader = None
        self._writer = None
        self._connected = False

    @property
    def connected(self):
        return self._connected

    def _calc_checksum(self, cmd):
        check_val = ord(cmd[1])
        for c in cmd[2:]:
            check_val = check_val ^ ord(c)
        return check_val

    async def connect(self):
        print("Connecting")
        self._reader, self._writer = await asyncio.open_connection(
                                                    HTA_HOST,
                                                    HTA_PORT,
                                                    )
        print("Connected")
        self._connected = True

    async def sendCmd(self, command, payload=[]):
        c = chr(STX)
        cmd_str = hex(command)[2:] # strip 0x
        if len(cmd_str) == 1:
            cmd_str = '0' + cmd_str
        for i in range(2):
            c += cmd_str[i].upper()
        for i in range(3, 11):
            c += '0'
        length = len(payload) + CMD_MIN_LEN - 2
        if length >= 26:
            raise NotImplementedError("Bug for payloads longer than 16 bytes")
        length_str = '00' + hex(length)[2:]
        c += length_str
        for p in payload:
            c += p
        cs = self._calc_checksum(c)
        cs_str = '%02d' % int( hex(cs)[2:] )
        for i in range(2):
            c += cs_str[i]
        c += chr(ETX)
        print("sendCmd: %s" %c.encode())
        self._writer.write(c.encode())
        await self._writer.drain()
        
    async def getResp(self):
        r = await self._reader.readuntil(chr(ETX).encode())
        print("getResp: %s" %r)
        stx = r[0]
        cmd = r[1:3]
        error = r[3:7]      # TODO: handle
        status = r[7:11]    # TODO: handle
        length = r[11:15]   # TODO: handle
        payload = r[15:-3]
        cs = r[-3:-1]       # TODO: handle
        etx = r[-1]

        if ( (stx == STX) and
             (etx == ETX) ):
            # print(nBytes-4, payload)
            return cmd, payload
        return None, None
        
    async def sendCmdWaitResp(self, command, payload=[]):
        await self.sendCmd(command, payload)
        resp_cmd, resp = await self.getResp()
        if int(resp_cmd, 16) == command:
            return resp
        else:
            raise ValueError("Received response for wrong command")

    def close(self):
        print("closing the socket")
        # close the socket
        self._writer.close()
        # no longer connected
        self._connected = False
        # make sure other routines know the socket is closed
        self._reader = self._writer = None