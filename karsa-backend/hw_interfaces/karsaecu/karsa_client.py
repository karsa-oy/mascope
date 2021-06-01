import socket

KRS_HOST = '192.168.1.200'  # The server's hostname or IP address

BUFFER_SIZE = 256

APP_CMD_MIN_LEN = 4       # STX (1) + CMD (1) + LEN (1) + ETX (1)
APP_RSP_MIN_LEN = 5       # STX (1) + CMD (1) + LEN (1) + STATUS (1) + ETX (1)
STX = 0x02
ETX = 0x03

class TCPClient():
    def __init__(self,port,timeout=10):
        self._connected = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self._resp = bytearray(BUFFER_SIZE)

        # try to connect
        try:
            self.socket.connect((KRS_HOST, port))
            print("Connected")
            self._connected = True
        except socket.error as err:
            print("Cannot connect to the Karsa Socker Server. IP = {0}, Port = {1}".format(KRS_HOST,port))
            raise

    def sendCmd(self,command,payload):
        l = len(payload)
        c = bytearray(APP_CMD_MIN_LEN + l)
        c[0] = STX
        c[1] = command
        c[2] = (l & 0xFF)
        for i in range(0, l):
            c[3+i] = payload[i]
        c[3+l] = ETX
        try:
            self.socket.sendall(c)
            return False
        except Exception:
            pass
        return True
        
    def getResp(self,command):
        try:
            nBytes = self.socket.recv_into(self._resp)
            if ( (nBytes >= APP_RSP_MIN_LEN) and \
                 (self._resp[0] == STX) and \
                 (self._resp[1] == command) and \
                 (nBytes-4 == self._resp[2]) and \
                 (self._resp[self._resp[2]+3] == ETX) ):
                return nBytes-4,self._resp[3:nBytes-1]
        except Exception:
            pass
        return 0, None
        
    def sendCmdWaitResp(self,command,payload):
        err = self.sendCmd(command,payload)
        if (not err):
            nBytes, resp = self.getResp(command)
            if (resp[0] == 0x00):
                if (nBytes == 1):
                    return 0,resp[0:1]
                else:
                    return nBytes-1,resp[1:nBytes]
            else:
                print("Cmd 0x{0:02X} failed, status = 0x{1:02X}".format(command,resp[0]))
                return 0, resp[0:1]
        else:
            return 0, None # internal error

    def connected(self):
        return self._connected

    def close(self):
        print("closing the socket")
        # close the socket
        self.socket.close()
        # no longer connected
        self._connected = False
        # make sure other routines know the socket is closed
        self.socket = None

