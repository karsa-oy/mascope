import asyncio
from karsaHT3000A.ht3000a_client import AsyncTCPClient

CMD_READ_SAMPLER_STATUS = 0x1D

class KarsaClient(AsyncTCPClient):
    def __init__(self):
        super().__init__()

async def main():
    '''Main program'''
    tcp = KarsaClient()
    await tcp.connect()

    resp = await tcp.sendCmdWaitResp(CMD_READ_SAMPLER_STATUS)

    if (tcp.connected):
        tcp.close()

    print("exiting")

if __name__ == "__main__":
    asyncio.run(main())
