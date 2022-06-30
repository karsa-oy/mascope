import asyncio

from karsaecu.client import AsyncTCPClient
from KECU import *

# test 1
async def connect_and_close():
    client = AsyncTCPClient(KECU_TCP_HOST, KRS_APP_PORT)
    await client.connect()
    await asyncio.sleep(20)
    await client.close()
    await asyncio.sleep(10)

def test_connect_and_close():
    parse_cmd_args()
    n = 1
    while True:
        print('Cycle #', n)
        asyncio.run(connect_and_close())
        n += 1
        print('... done')


# test 2
async def task_client_reconnect(client):
    n = 1
    while True:
        print('Cycle #', n)
        await asyncio.sleep(MIN_MODE_DURATION)
        await client.reconnect(RCP_RECONNECT_TIMEOUT)
        n += 1
        print('... done')

def test_client_reconnect():
    parse_cmd_args()
    loop = asyncio.get_event_loop()
    client = AsyncTCPClient(KECU_TCP_HOST, KRS_APP_PORT)
    asyncio.shield( client.connect())
    loop.create_task(task_client_reconnect(client))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


# test 3
async def task_toggle_channel(kecu):
    from karsaecu.nodes import NodeId
    i = 0
    j = 0
    while True:
        try:
            if not kecu.connected:
                print('Test main pending for kecu connection')
                await asyncio.sleep(2)
                continue
            print('step #%s.%s' %(j, i))
            print(1)
            await kecu.nodes[NodeId.MION1v5_DIO].set_channel(5, True)
            await asyncio.sleep(1)
            print(2)
            await kecu.nodes[NodeId.MION1v5_DIO].set_channel(5, False)
            await asyncio.sleep(1)
        except Exception as e:
            print(e.__class__.__name__, str(e))
            kecu._app.is_broken = True
            print("Test main marks client broken")
            j += 1
            await asyncio.sleep(1)
        i += 1

def test_toggle_channel():
    parse_cmd_args()
    loop = asyncio.get_event_loop()
    kecu = KECU()
    tasks = []
    # KECU initialization
    tasks.append(
        asyncio.shield(
            loop.create_task(initialize_kecu(kecu))
            )
    )
    # KECU main loop
    tasks.append(
        loop.create_task(kecu.run())
    )
    tasks.append(
        loop.create_task(task_toggle_channel(kecu))
    )
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    test_toggle_channel()
