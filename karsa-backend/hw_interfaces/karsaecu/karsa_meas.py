import sys
import os
import socket
#import time

#from time import sleep
from timeit import default_timer as timer
#from datetime import timedelta

from karsaecu.karsa_client import TCPClient

KRS_MEAS_PORT = 65143            # The port used by the server

STX = 0x02
ETX = 0x03

# TODO: MIN_MEAS_MSG_SIZE should be 5 in FW 0.9
MIN_MEAS_MSG_SIZE = 6       # DIO Data : Header (4) + Node (1) + data (1)
MEAS_MSG_HEADER_LEN = 4     # STX (1) + CMD (1) + LEN (1) + ETX (1)

class KarsaMeasClient(TCPClient):
    def __init__(self):
        super().__init__(KRS_MEAS_PORT)

    def getData(self):
        try:
            nBytes = self.socket.recv_into(self._resp, MIN_MEAS_MSG_SIZE)
            if (nBytes == MIN_MEAS_MSG_SIZE):
                idx = 0
                while (self._resp[idx] != STX):
                    idx += 1
                if (idx < MIN_MEAS_MSG_SIZE):
                    if (idx > 0):
                        for i in range(MIN_MEAS_MSG_SIZE-idx):
                            self._resp[i] = self._resp[idx+i]
                        n = self.socket.recv_into(self._resp[MIN_MEAS_MSG_SIZE-idx:], idx)
                        nBytes += n
                        if (n != idx):
                            print("Error receiving rest of KRS Meas data (sync)")
                            return 0, None
                    if (self._resp[2] > (MIN_MEAS_MSG_SIZE-MEAS_MSG_HEADER_LEN)):
                        a = bytearray(self._resp[2]-(MIN_MEAS_MSG_SIZE-MEAS_MSG_HEADER_LEN))
                        # print("read {0} more bytes".format(self._resp[2]-2))
                        n = self.socket.recv_into(a)
                        if (n != self._resp[2]-(MIN_MEAS_MSG_SIZE-MEAS_MSG_HEADER_LEN)):
                            print("Error receiving rest of Meas data")
                            return 0, None
                        for i in range(n):
                            self._resp[MIN_MEAS_MSG_SIZE+i] = a[i]
                        nBytes += n
                    if (self._resp[nBytes-1] != ETX):
                        print("ETX not found")
                        return 0, None
            return nBytes, self._resp[:nBytes]
        except Exception:
            pass
        return 0, None

def main():
    '''Main program'''
    measTime = 10
    if (len(sys.argv) > 1):
        measTime = int(sys.argv[1])
    
    try:
        tcp = KarsaMeasClient()

        end_time = timer() + measTime
        while (timer() < end_time):
            nbytes, data = tcp.getData()
            if (nbytes > 0):
                print("RX :", end='')
                for i in range(nbytes):
                    print(" {0:02X}".format(data[i]), end='')
                print("")    

        if (tcp.connected() == True):
            tcp.close()

    except Exception:
        print("Connection to Karsa Measurement port failed")
    finally:
        print("exiting")

# Run main.
if __name__ == "__main__":
    sys.exit(main())
