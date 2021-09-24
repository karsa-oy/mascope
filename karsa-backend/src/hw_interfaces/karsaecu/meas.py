import asyncio
import sys
import os
import socket
#import time

#from time import sleep
from timeit import default_timer as timer
#from datetime import timedelta

from .client import AsyncTCPClient
from .messages import ETX, MIN_MEAS_MSG_SIZE, STX


KRS_MEAS_PORT = 65143           # KECU notification port


class KarsaMeasClient(AsyncTCPClient):
    def __init__(self):
        super().__init__(KRS_MEAS_PORT)

    async def getData(self):
        # Read start header
        r1 = await self._reader.readexactly(3)
        stx, cmd, length = r1
        # Read rest of the msg
        r2 = await self._reader.readexactly(length + 1)
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
    
    try:
        tcp = KarsaMeasClient()
        await tcp.connect()

        while True:
            nbytes, data = await tcp.getData()
            if (nbytes > 0):
                print("RX :", end='')
                for i in range(nbytes):
                    print(" {0:02X}".format(data[i]), end='')
                print("")    

    except Exception as e:
        print("Connection to Karsa Measurement port failed: %s" %e)
    finally:
        if tcp.connected:
            tcp.close()
        print("exiting")

# Run main.
if __name__ == "__main__":
    asyncio.run(main())