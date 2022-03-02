import asyncio
import csv
import sys

from datetime import datetime

from app import KarsaClient
from meas import KarsaMeasClient
from meas_udp import KarsaMeasClientUDP
from nodes import NodeType, DEVICES
from udp import KarsaMeasProtocol
from ui import App


KECU_TCP_HOST = '192.168.1.200' # KECU IP address
KRS_APP_PORT = 65142            # KECU command port
KRS_MEAS_PORT = 65143           # KECU notification port

KECU_UDP_HOST = '0.0.0.0'       # KECU UDP host
KECU_UDP_PORT = 65146           # KECU UDP port


class KECU():
    def __init__(self) -> None:
        self._app = KarsaClient(KECU_TCP_HOST, KRS_APP_PORT)
        self._meas = KarsaMeasClient(KECU_TCP_HOST, KRS_MEAS_PORT)
        self._meas_udp = KarsaMeasClientUDP(KECU_UDP_HOST, KECU_UDP_PORT)
        self.nodes = {}

    async def connect(self):
        await self._app.connect()
        await self._meas.connect()
        await self._meas_udp.connect()

    async def disconnect(self):
        # TODO: Stop all measurements
        for node_id, node in self._app._node_dict.items():
            try:
                await node.stop_measurement()
            except Exception as e:
                print(e)
                pass
        await self._app.close()
        await self._meas.close()
        await self._meas_udp.close()

    async def initialize(self):
        await self._app.get_node_list()
        self.nodes = self._app._node_dict

    async def run(self):
        try:
            while True:
                print('.')
                try:
                    node_id, ntf, data = await asyncio.wait_for(
                                            self.wait_for_notification(),
                                            timeout=1
                                            )
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print("Exception in KECU.run(): %s" %e)
                print('..')
                try:
                    # Notify app
                    ntf_handler = getattr(self._app,
                                          'on_{}'.format(ntf.name)
                                          )
                    await ntf_handler(node_id)
                except AttributeError:
                    pass
                except Exception as e:
                    print(e)
                try:
                    # Notify node
                    # print('on_{}({})'.format(ntf.name, data))
                    ntf_handler = getattr(self.nodes[node_id],
                                          'on_{}'.format(ntf.name)
                                          )
                    await ntf_handler(data)
                except Exception as e:
                    print(e)
        except asyncio.CancelledError:
            print("KECU.run() task cancelled")
        finally:
            await self.disconnect()

    async def wait_for_notification(self):
        # return await self._meas.get_data()
        return await self._meas_udp.get_data()

    async def writer(self, interval=1):
        def new_file():
            filename = datetime.now().strftime('%Y%m%d') + '_kecu.dat'
            try:
                with open(filename, 'x') as f:
                    writer = csv.writer(f)
                    writer.writerow(field_names)
            except FileExistsError:
                pass
            return filename

        field_names = ['timestamp',
                       *[(node_id.name+'('+channel.description+')')
                         for node_id, device in DEVICES.items() for _, channel in device.channels.items()
                         ]
                       ]
        
        date_now = datetime.now()
        date_prev = date_now
        filename = new_file()
        
        while True:
            date_now = datetime.now()
            if date_now.day != date_prev.day:
                # New file per day
                filename = new_file()
            date_prev = date_now
            # Write values
            timestamp = date_now.isoformat()
            values = [timestamp]
            for node_id, device in DEVICES.items():
                for _, channel in device.channels.items():
                    if (node_id in self.nodes and
                        not isinstance(channel.value, property)
                        ):
                        values.append(channel.value)
                    else:
                        values.append(None)

            with open(filename, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(values)

            # Wait for interval
            await asyncio.sleep(interval)


async def initialize_kecu(kecu):
    await kecu.connect()
    await kecu.initialize()
    for node_id, node in kecu._app._node_dict.items():
        if node._device.node_type == NodeType.MFC:
            await node.start_measurement(index=0x2F00, subindex=0x01, interval=10) # Flow setpoint
            await node.start_measurement(index=0x2C00, subindex=0x01, interval=10) # Flow monitor
        elif node._device.node_type == NodeType.AI:
            await node.start_measurement(interval=10)
        elif node._device.node_type == NodeType.DIO:
            await node.start_measurement(interval=10)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = []
    
    kecu = KECU()
    loop.run_until_complete(initialize_kecu(kecu))
    # KECU main loop
    tasks.append(loop.create_task(kecu.run()))

    if len(sys.argv) > 1 and 'csv' in sys.argv:
        # KECU csv writer
        tasks.append( loop.create_task(kecu.writer()) )

    app = App(loop, kecu, tasks=tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        app.close()