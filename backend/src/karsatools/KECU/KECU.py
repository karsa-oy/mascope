"""KECU application

Connects to KECU and provides a graphical user interface to control and monitor
devices connected to it.
"""

import argparse
from yaml import safe_load
import asyncio
import csv
import os
from datetime import datetime
import logging

from karsaecu.app import KarsaClient
from karsaecu.devices import DEVICES
from karsaecu.meas import KarsaMeasClient
from karsaecu.meas_udp import KarsaMeasClientUDP
from karsaecu.ui import App


# KECU vars: can be overridden from cmd_line or yaml config file
# priority: cmd_line_value | config_file_value | defalt_value
KECU_TCP_HOST = '192.168.1.208' # KECU IP address
KRS_APP_PORT = 65142            # KECU command port
KRS_MEAS_PORT = 65143           # KECU notification port
KECU_UDP_HOST = '0.0.0.0'       # KECU UDP host
KECU_UDP_PORT = 65146           # KECU UDP port
INSTRUMENTS = 'kecu,mion,mion2,scenthound,calibrator,flushplate'
MION_MODES = {}                 # modes are defined in config file
MION_SEQUENCES = {}             # index of available sequences as mode:duration pair
MION_SEQUENCE = 'default'       # sequence to load; missing sequence goes as empty one
LOG_LEVEL = 'INFO'
MIN_MODE_DURATION = 20          # TODO: RCP bug workaround
RCP_RECONNECT_TIMEOUT = 15      # TODO: RCP bug workaround

default_config_fname = './config.yaml'
valid_instruments = INSTRUMENTS.split(',') + ['all']
valid_log_levels = list(logging._nameToLevel.keys())


class InstrumentValidator(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        instruments = values.split(',')
        for instr in instruments:
            if instr not in valid_instruments:
                raise ValueError(f"Invalid instrument: {instr}. Should be one of {valid_instruments}")
        setattr(namespace, self.dest, values)

class LogLevelValidator(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if value.upper() not in valid_log_levels:
            raise ValueError(f"Invalid log_level: {value}. Should be one of {valid_log_levels}")
        setattr(namespace, self.dest, value.upper())

def parse_cmd_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="path to yaml config file", type=str, required=False)
    parser.add_argument("--INSTRUMENTS", help="comma separated list of instruments",
                        type=str, required=False, action=InstrumentValidator)
    parser.add_argument("--KECU_TCP_HOST", help="KECU IP address", type=str, required=False)
    parser.add_argument("--KRS_APP_PORT", help="KECU command port", type=int, required=False)
    parser.add_argument("--KRS_MEAS_PORT", help="KECU notification port", type=int, required=False)
    parser.add_argument("--KECU_UDP_HOST", help="KECU UDP host", type=str, required=False)
    parser.add_argument("--KECU_UDP_PORT", help="KECU UDP port", type=int, required=False)
    parser.add_argument("--MION_SEQUENCE", help="MION sequence to load", type=str, required=False)
    parser.add_argument("--MIN_MODE_DURATION", help="RCP bug workaround: Minimal duration for a mode in seconds",
                        type=int, required=False)
    parser.add_argument("--RCP_RECONNECT_TIMEOUT", help="RCP bug workaround: TCP client reconnect timeout in seconds",
                        type=int, required=False)
    parser.add_argument("--LOG_LEVEL", help="Log level", type=str, required=False, action=LogLevelValidator)

    cmd_line_args = parser.parse_args()
    cmd_line_args = dict( filter(lambda i: i[1] is not None, vars(cmd_line_args).items()) )
    config_fname = cmd_line_args.pop('config', None)
    file_args = {}
    # KECU vars may also be defined in yaml file
    read_from = 'defaults'
    if config_fname:
        with open(config_fname, 'r') as f:
            read_from = config_fname
            file_args = safe_load(f) or {}
    else:
        # try default config file, if available
        try:
            with open(default_config_fname, 'r') as f:
                read_from = default_config_fname
                file_args = safe_load(f) or {}
        except FileNotFoundError:
            pass
    # cmd_line args have a priority over config_file args
    args = {**file_args, **cmd_line_args}
    # replace default KECU vars with those specified in cmd args
    for key, value in args.items():
        globals()[key] = value
    return read_from

read_from = parse_cmd_args()
logging.basicConfig(filename=f'{os.path.splitext(os.path.basename(__file__))[0]}.log',
                    format='%(asctime)s %(module)s %(message)s', datefmt='%H:%M:%S',
                    filemode='w',
                    level=logging._nameToLevel[LOG_LEVEL])
logger = logging.getLogger(__name__)
logger.info(f"Loading KECU parameters from {read_from} [{LOG_LEVEL}]")


class KECU():
    def __init__(self) -> None:
        self.instruments = INSTRUMENTS  # instruments to show in ui
        self.mion_modes = MION_MODES    # mion modes setpoints config
        self.mion_sequence = self.parse_mion_sequence()
        self.sequencer_mode = None      # currently running mode
        self.min_mode_duration = MIN_MODE_DURATION
        self.rcp_reconnect_timeout = RCP_RECONNECT_TIMEOUT
        self.rcp_reconnect_in_progress = False

        self.lock = asyncio.Lock()
        self._app = KarsaClient(KECU_TCP_HOST, KRS_APP_PORT, self)
        # self._meas = KarsaMeasClient(KECU_TCP_HOST, KRS_MEAS_PORT, self)
        self._meas_udp = KarsaMeasClientUDP(KECU_UDP_HOST, KECU_UDP_PORT)
        self.connected_callbacks = []
        self.nodes_callbacks = []

    def parse_mion_sequence(self):
        tokens = MION_SEQUENCES.get(MION_SEQUENCE, [])
        sequence = []
        # decode (mode, duration) from config
        for token in tokens:
            mode, duration = token.split(',')
            sequence.append((mode.strip(), int(duration.strip())))
        # validate mode names
        valid_modes = list(self.mion_modes.keys())
        for mode, _ in sequence:
            if mode not in valid_modes:
                raise Exception(f'Invalid mode {mode}; must be one of the {valid_modes}')
        return sequence

    @property
    def connected(self):
        return (self._app != None and
                self._app.connected and
                # self._meas.connected and
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
        # await self._meas.connect()
        await self._meas_udp.connect()
        for callback in self.connected_callbacks:
            callback()

    async def init_nodes(self):
        await self._app.init_nodes()
        self.nodes = self._app.nodes

    # RCP bug workaround
    async def RCP_reconnect_app(self):
        self.rcp_reconnect_in_progress = True
        logger.info("Reconnecting KarsaClient...")
        await self._app.reconnect(self.rcp_reconnect_timeout)
        await self.init_nodes()
        self.rcp_reconnect_in_progress = False

    async def disconnect(self):
        logger.info("Disconnecting...")
        for node_id, node in self.nodes.items():
            try:
                await node.stop_measurement()
            except Exception as e:
                logger.error(f'{e.__class__.__name__} : {str(e)}')
                pass
        await self._app.close()
        # await self._meas.close()
        await self._meas_udp.close()

    async def initialize(self):
        self.connected = (
            self._app != None and
            self._app.connected and
            # self._meas.connected and
            self._meas_udp.connected
            )
        await self._app.get_version()
        await self._app.get_node_list()
        await self.init_nodes()

    async def run(self):
        def RCP_bug_here():
            return self._app.is_broken
        try:
            while True:
                if not self.connected:
                    await asyncio.sleep(1)
                    continue
                elif RCP_bug_here():     # RCP bug workaround
                    await self.RCP_reconnect_app()
                    continue
                try:
                    node_id, ntf, data = await asyncio.wait_for(
                        self.wait_for_notification(),
                        timeout=1
                        )
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.exception('Exception')
                try:
                    # Notify app
                    ntf_handler = getattr(self._app,
                                          'on_{}'.format(ntf.name)
                                          )
                    await ntf_handler(node_id, data)
                except AttributeError:
                    pass
                except Exception as e:
                    logger.exception('Exception')
                try:
                    # Notify node
                    logger.debug('on_{}({})'.format(ntf.name, data))
                    ntf_handler = getattr(
                        self.nodes[node_id],
                        'on_{}'.format(ntf.name)
                        )
                    await ntf_handler(data)
                except Exception as e:
                    logger.exception('Exception')
        except asyncio.CancelledError:
            logger.info("KECU.run() task cancelled")
        except Exception as e:
            logger.exception('Exception')
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
                'mode',
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
            values = [timestamp, self.sequencer_mode]
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
            logger.error("Connection timed out")
            await asyncio.sleep(1)
            continue
    logger.info("Initializing...")
    await asyncio.wait_for(kecu.initialize(), None)
    logger.info("Initialized")


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
