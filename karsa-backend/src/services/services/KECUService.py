import asyncio
import csv

from datetime import datetime

from karsaecu.app import KarsaClient
from karsaecu.errors import ErrorCode
from karsaecu.meas import KarsaMeasClient
from karsaecu.nodes import NodeType, DEVICES

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args


kecu = None

class KECU():
    def __init__(self) -> None:
        self._app = KarsaClient()
        self._meas = KarsaMeasClient()
        self.nodes = {}

    async def connect(self):
        await self._app.connect()
        await self._meas.connect()

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
                print('..')
                try:
                    # Notify app
                    ntf_handler = getattr(self._app,
                                          'on_{}'.format(ntf.name)
                                          )
                    await ntf_handler(node_id)
                except AttributeError:
                    pass
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
        return await self._meas.get_data()

    async def writer(self, interval=1):
        def new_file():
            filename = datetime.now().strftime('%Y%m%d') + '_kecu.dat'
            with open(filename, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(field_names)
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
                    if node_id in self.nodes:
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


class KECUServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = []


class KECUServiceClient(BaseServiceClient):
    async def init_service(self):
        global kecu

        kecu = KECU()
        await kecu.connect()
        await kecu.initialize()

    async def service_main():
        global kecu

        while True:
            await asyncio.sleep(1)


def run():
    args = parse_cmd_args()
    client = KECUServiceClient(args['url'],
                               args['port'],
                               (args['ns'], KECUServiceNamespace)
                               )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Service stopped.')



if __name__=='__main__':
    run()