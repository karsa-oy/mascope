"""KECU application

Connects to KECU and provides a graphical user interface to control and monitor
devices connected to it.
"""

import asyncio
import csv
import os

from datetime import datetime

from karsaecu.app import KarsaClient
from karsaecu.devices import DEVICES
from karsaecu.meas import KarsaMeasClient
from karsaecu.meas_udp import KarsaMeasClientUDP
from karsaecu.ui import App


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
        self.connected_callbacks = []
        self.nodes_callbacks = []

    @property
    def connected(self):
        return (self._app.connected and
                self._meas.connected and
                self._meas_udp.connected
                )

    @connected.setter
    def connected(self, connected: bool):
        self._connected = connected
        for callback in self.connected_callbacks:
            callback()

    @property
    def nodes(self):
        return self._app.nodes

    @nodes.setter
    def nodes(self, nodes: dict):
        self._nodes = nodes
        for callback in self.nodes_callbacks:
            callback(nodes)

    @property
    def version(self) -> str:
        return self._app._version

    async def connect(self):
        await self._app.connect()
        await self._meas.connect()
        await self._meas_udp.connect()
        for callback in self.connected_callbacks:
            callback()

    async def disconnect(self):
        print("Disconnecting...")
        for node_id, node in self.nodes.items():
            try:
                await node.stop_measurement()
            except Exception as e:
                print(e)
                pass
        await self._app.close()
        await self._meas.close()
        await self._meas_udp.close()

    async def initialize(self):
        self.connected = (
            self._app.connected and
            self._meas.connected and
            self._meas_udp.connected
            )
        await self._app.get_version()
        await self._app.get_node_list()
        self.nodes = self._app.nodes
        for node_id, node in self.nodes.items():
            await node.initialize()

    async def run(self):
        try:
            while True:
                if not self.connected:
                    # print(':')
                    await asyncio.sleep(1)
                    continue
                # print('.')
                try:
                    node_id, ntf, data = await asyncio.wait_for(
                        self.wait_for_notification(),
                        timeout=1
                        )
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print("Exception in KECU.run(): %s" %e)
                # print('..')
                try:
                    # Notify app
                    ntf_handler = getattr(self._app,
                                          'on_{}'.format(ntf.name)
                                          )
                    await ntf_handler(node_id, data)
                except AttributeError:
                    pass
                except Exception as e:
                    print(e)
                try:
                    # Notify node
                    # print('on_{}({})'.format(ntf.name, data))
                    ntf_handler = getattr(
                        self.nodes[node_id],
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
            if not os.path.exists('data'):
                os.mkdir('data')
            filename = os.path.join(
                'data',
                'KECU_' + datetime.now().strftime('%Y%m%d') + '.csv'
            )
            try:
                with open(filename, 'x') as f:
                    writer = csv.writer(f)
                    writer.writerow(field_names)
            except FileExistsError:
                pass
            return filename

        field_names = [
                'timestamp (UTC)',
                *[
                (node_id.name+'('+channel.description+')')
                for node_id, device in DEVICES.items()
                for _, channel in device.channels.items()
                ]
            ]
        
        date_now = datetime.utcnow()
        date_prev = date_now
        filename = new_file()
        
        while True:
            date_now = datetime.utcnow()
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
    while True:
        try:
            await asyncio.wait_for(
                kecu.connect(),
                timeout=2
                )
            break
        except asyncio.TimeoutError:
            print("Connection timed out")
            await asyncio.sleep(1)
            continue
    print("Initializing...")
    await asyncio.wait_for(kecu.initialize(), None)
    print("Initialized")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = []
    kecu = KECU()
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
    # KECU csv writer
    tasks.append(
        loop.create_task(kecu.writer())
        )
    app = App(loop, kecu, tasks=tasks)
    kecu.nodes_callbacks.append(app.update_fields)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        app.close()