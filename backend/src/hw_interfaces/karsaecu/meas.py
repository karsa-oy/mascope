import asyncio
import sys
import os
import socket
#import time

#from time import sleep
from timeit import default_timer as timer
#from datetime import timedelta

from .client import AsyncTCPClient
from .messages import ETX, MIN_MEAS_MSG_SIZE, STX, Notification
from .nodes import NodeId


KRS_MEAS_PORT = 65143           # KECU notification port


class KarsaMeasClient(AsyncTCPClient):
    def __init__(self):
        super().__init__(KRS_MEAS_PORT)

    async def get_data(self) -> bytes:
        # Read start header
        print("get_data(): read header")
        header = await self._reader.readexactly(3)
        stx, type_, length = header
        # Read rest of the msg
        print("get_data(): read payload")
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
        print("get_data(): Something went wrong with msg: %s" %(header+payload_etx))
        raise Exception("Failed to read data")


async def main():
    '''Main program'''
    
    try:
        tcp = KarsaMeasClient()
        await tcp.connect()

        while True:
            ntf, node_id, data = await tcp.get_data()
            # if len(data):
            #     print("RX :", end='')
            #     for d in data:
            #         print(" {0:02X}".format(d), end='')
            #     print("")    

    except Exception as e:
        print("Connection to Karsa Measurement port failed: %s" %e)
    finally:
        if tcp.connected:
            tcp.close()
        print("exiting")

# Run main.
if __name__ == "__main__":
    asyncio.run(main())