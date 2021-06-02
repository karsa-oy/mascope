import asyncio
import sys
import os
import socket
#import time

#from time import sleep
from timeit import default_timer as timer
#from datetime import timedelta

from karsaecu.karsa_async_client import AsyncTCPClient

KRS_MEAS_PORT = 65143            # The port used by the server

STX = 0x02
ETX = 0x03

MIN_MEAS_MSG_SIZE = 6       # DIO Data : Header (4) + Node (1) + data (1)
MEAS_MSG_HEADER_LEN = 4     # STX (1) + CMD (1) + LEN (1) + ETX (1)

class KarsaMeasClient(AsyncTCPClient):
    def __init__(self):
        super().__init__(KRS_MEAS_PORT)

    async def getData(self):
        # Read start header
        r1 = await self._reader.read(3)
        stx, cmd, length = r1
        # Read rest of the msg
        r2 = await self._reader.read(length + 1)
        payload = r2[:-1]
        etx = r2[-1]
        nBytes = len(r1) + len(r2)
        if ( (nBytes >= MIN_MEAS_MSG_SIZE) and
             (stx == STX) and
             (nBytes-4 == length) and
             (etx == ETX) ):
            # print(nBytes-4, payload)
            return nBytes-4, payload
        return 0, None


async def main():
    '''Main program'''
    measTime = 10
    if (len(sys.argv) > 1):
        measTime = int(sys.argv[1])
    
    try:
        tcp = KarsaMeasClient()
        await tcp.connect()

        end_time = timer() + measTime
        while (timer() < end_time):
            nbytes, data = await tcp.getData()
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
    asyncio.run(main())