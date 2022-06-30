from multiprocessing import Event
from time import time_ns, sleep
import asyncio
import tkinter as tk
from tkinter import ttk
from collections import defaultdict, OrderedDict
from functools import reduce, partial

from .nodes import NodeId

import logging
logger = logging.getLogger(__name__)


class Field():
    def __init__(
            self,
            kecu,
            node_id,
            label,
            parent_frame,
            monitorable,
            settable,
            toggleable,
            row=None,
            column=None,
            sticky='E',
            padx=5,
            pady=1
            ):
        """Base class for a UI field

        There could be one field per device, or device channel.

        Parameters
        ----------
        kecu : KECU
            KECU class instance
        node_id : NodeId
            NodeId of the device to control/monitor
        label : str
            Label to display in the GUI
        parent_frame : Frame or LabelFrame
            Frame to attach the field onto
        monitorable : bool
            Show numeric monitor field
        settable : bool
            Show numeric entry field
        toggleable : bool
            Show checkbox
        row : int, optional
            Row index of the parent frame onto which attach the field,
            by default None. If None, do not grid.
        column : int, optional
            Column index of the parent frame onto which attach the field,
            by default None. If None, do not grid.
        sticky : str, optional
            Sticky attribute value for gridding onto parent frame, by default 'E'
        padx : int, optional
            Padx attribute value for gridding onto parent frame, by default 5
        pady : int, optional
            Pady value for gridding onto parent frame, by default 1
        """
        self.kecu = kecu
        self.node_id = node_id
        self.channel = None
        self.label_text = label
        self.parent_frame = parent_frame
        self.frame = ttk.Frame(parent_frame)
        if row is not None and column is not None:
            self.frame.grid(
                row=row,
                column=column,
                sticky=sticky,
                padx=padx,
                pady=pady
                )
        self.label = ttk.Label(self.frame, text=label).grid(row=0, column=0)
        if monitorable:
            self.mon_value = tk.DoubleVar()
            self.mon_entry = ttk.Entry(self.frame,
                                      textvariable=self.mon_value,
                                      state='disabled'
                                      )
            self.mon_entry.grid(row=0, column=2)
        else:
            self.mon_value = None
        if settable:
            self.set_value = tk.DoubleVar()
            self.set_value_callbacks = []
            self.prev_set_value = self.set_value.get()
            self.set_entry = ttk.Entry(self.frame,
                                      textvariable=self.set_value,
                                      )
            self.set_entry.bind('<Key-Return>', self.on_setpoint_changed)
            self.set_entry.bind('<FocusOut>', self.reset_setpoint)
            self.set_entry.grid(row=0, column=1)
        else:
            self.set_value = None
            self.prev_set_value = None
        if toggleable:
            self.cb_value = tk.BooleanVar()
            self.cb_value_callbacks = []
            self.checkbox = ttk.Checkbutton(self.frame,
                                           variable=self.cb_value,
                                           command=self.on_checkbox_toggled
                                           )
            self.checkbox.grid(row=0, column=3)
        else:
            self.cb_value = None

        self.disable()

    @property
    def monitor(self):
        if self.mon_value is None:
            raise ValueError("Cannot monitor non-monitorable Field")
        return self.mon_value.get()

    @property
    def setpoint(self):
        if self.set_value is None:
            raise ValueError("Non-settable Field has no setpoint")
        return self.set_value.get()

    def disable(self):
        try:
            self.set_entry.configure(state=tk.DISABLED)
        except AttributeError:
            pass
        try:
            self.checkbox.configure(state=tk.DISABLED)
        except AttributeError:
            pass

    def enable(self):
        try:
            self.set_entry.configure(state=tk.NORMAL)
        except AttributeError:
            pass
        try:
            self.checkbox.configure(state=tk.NORMAL)
        except AttributeError:
            pass

    def on_checkbox_toggled(self):
        for callback in self.cb_value_callbacks:
            logger.debug(f'on_checkbox_toggled {callback.__name__}, {self.channel}, {self.cb_value.get()}')
            asyncio.create_task(
                callback(self.channel, self.cb_value.get())
            )

    def on_setpoint_changed(self, event):
        # TODO: Possibly add validation here
        self.set(self.set_value.get())
        for callback in self.set_value_callbacks:
            asyncio.create_task(
                callback(self.set_value.get())
            )

    def reset_setpoint(self, event):
        self.set_value.set(self.prev_set_value)

    def set(self, new_setpoint):
        if self.set_value is None:
            raise ValueError("Cannot set non-settable Field")
        self.prev_set_value = self.set_value.get()
        return self.set_value.set(new_setpoint)

    def update_checkbox(self, new_value):
        logger.debug(f'update_checkbox {new_value}')
        self.cb_value.set(bool(new_value))

    def update_monitor(self, new_value):
        self.mon_value.set(round(new_value, 2))
        
    def update_setpoint(self, new_value):
        if self.frame.focus_get() == self.set_entry:
            # Avoid resetting setpoint while trying to adjust it
            return
        self.set(new_value)


class DiField(Field):
    def __init__(self, kecu, node_id, channel, label, parent_frame, **kwargs):
        """Field for digital input channel

        Show checkbox disabled, indicating the value of the input.
        """
        super().__init__(kecu,
                         node_id,
                         label,
                         parent_frame,
                         monitorable=False,
                         settable=False,
                         toggleable=True,
                         **kwargs
                         )
        self.checkbox.configure(state=tk.DISABLED)
        self.channel = channel
        self.update()

    def update(self):
        if self.kecu:
            node = self.kecu.nodes.get(self.node_id, None)
            if node:
                device = node._device

                # TODO: review callbacks reinitialization
                device.channels[self.channel].callbacks = []

                device.channels[self.channel].callbacks.append(
                    self.update_checkbox
                    )

    def enable(self):
        try:
            self.set_entry.configure(state=tk.NORMAL)
        except AttributeError:
            pass

class DoField(Field):
    def __init__(self, kecu, node_id, channel, label, parent_frame, **kwargs):
        """Digital output field

        Show checkbox to allow toggling the output.
        """
        super().__init__(kecu,
                         node_id,
                         label,
                         parent_frame,
                         monitorable=False,
                         settable=False,
                         toggleable=True,
                         **kwargs
                         )
        self.channel = channel
        self.update()

    def update(self):
        if self.kecu:
            node = self.kecu.nodes.get(self.node_id, None)
            if node:
                device = node._device

                # TODO: review callbacks reinitialization
                device.channels[self.channel].callbacks = []
                self.cb_value_callbacks = []

                device.channels[self.channel].callbacks.append(
                    self.update_checkbox
                    )
                self.cb_value_callbacks.append(node.set_channel)

class MfcField(Field):
    def __init__(self, kecu, node_id, label, parent_frame, **kwargs):
        """Mass flow controller field

        Show numeric entry and monitor fields to allow setting
        and monitoring the mfc flow setpoint.
        """
        super().__init__(kecu,
                         node_id,
                         label,
                         parent_frame,
                         monitorable=True,
                         settable=True,
                         toggleable=False,
                         **kwargs
                         )
        self.channel = (0x2F00, 0x01)
        self.monitor_channel = (0x2C00, 0x01)
        self.update()

    def update(self):
        if self.kecu:
            node = self.kecu.nodes.get(self.node_id, None)
            if node:
                device = node._device

                # TODO: review callbacks reinitialization
                device.channels[self.channel].callbacks = []
                self.set_value_callbacks = []

                device.channels[self.channel].callbacks.append(
                    self.update_setpoint
                ) # On read setpoint
                device.channels[self.monitor_channel].callbacks.append(
                    self.update_monitor
                ) # On read actual flow
                self.set_value_callbacks.append(node.set_flow)

class MonitorField(Field):
    def __init__(self, kecu, node_id, channel, label, parent_frame, **kwargs):
        """Monitor field

        Show numeric monitor field displaying a value to be monitored,
        e.g. analog input channel.
        """
        super().__init__(kecu,
                         node_id,
                         label,
                         parent_frame,
                         monitorable=True,
                         settable=False,
                         toggleable=False,
                         **kwargs
                         )
        self.channel = channel
        self.update()

    def update(self):                         
        if self.kecu:
            node = self.kecu.nodes.get(self.node_id, None)
            if node:
                device = node._device

                # TODO: review callbacks reinitialization
                device.channels[self.channel].callbacks = []

                device.channels[self.channel].callbacks.append(
                    self.update_monitor
                    )

class VoltageField(Field):
    def __init__(self, kecu, node_id, channel, label, parent_frame, **kwargs):
        """Voltage field

        Show numeric entry and monitor fields, and a checkbox to toggle between
        0 and the setpoint. 
        """
        super().__init__(kecu,
                         node_id,
                         label,
                         parent_frame,
                         monitorable=True,
                         settable=True,
                         toggleable=True,
                         **kwargs
                         )
        self.channel = channel
        self.update()

    def update(self):
        if self.kecu:
            node = self.kecu.nodes.get(self.node_id, None)
            if node:
                device = node._device

                # TODO: review callbacks reinitialization
                device.channels[(0x7300, self.channel)].callbacks = []
                device.channels[(0x7130, self.channel)].callbacks = []
                self.set_value_callbacks = []

                device.channels[(0x7300, self.channel)].callbacks.append(
                    self.update_setpoint
                ) # On read setpoint
                device.channels[(0x7130, self.channel)].callbacks.append(
                    self.update_monitor
                ) # On read monitor value
                self.set_value_callbacks.append(
                    node.set_voltage
                )
                self.cb_value.set(True)

    def on_checkbox_toggled(self):
        """Override parent class method"""
        if self.cb_value.get():
            self.set_entry.configure(state=tk.NORMAL)
        else:
            self.set_entry.configure(state=tk.DISABLED)
        self.on_setpoint_changed(None)

    def on_setpoint_changed(self, event):
        """Override parent class method"""
        self.set(self.set_value.get())
        # Send 0 when checkbox not ticked, setpoint otherwise
        value_to_send = self.cb_value.get() * self.set_value.get()
        for callback in self.set_value_callbacks:
            asyncio.create_task(
                callback(self.channel, value_to_send)
            )

    def update_setpoint(self, new_value):
        if self.frame.focus_get() == self.set_entry:
            # Avoid resetting setpoint while trying to adjust it
            return
        if self.cb_value.get():
            self.set(new_value)


class MionModesTable:
    def __init__(self, parent, master, on_click_row):
        self.parent = parent
        self.rows = OrderedDict()
        mode_names = parent.modes.keys()
        self.field_size = reduce(lambda m, l: max(m, l), [len(m) for m in mode_names], 0) + 4
        for i, mode in enumerate(mode_names):
            btn = ttk.Button(master=master, text=mode, width=self.field_size, command=partial(on_click_row, mode))
            btn.grid(row=i, column=0)
            self.rows[mode] = btn


class MionSequenceTable:
    DEFAULT_DURATION = 60

    def __init__(self, parent, master, processor=None):
        self.parent = parent
        self.master = master
        self.field_size = parent.table_modes.field_size
        self.processor = processor
        self.rows = OrderedDict()
        for mode, duration in parent.sequence:
            self.add_row(mode, duration)
            sleep(.001)     # rows are indexed by timestamp - make it different


    def build(self):
        for slave in self.master.grid_slaves():
            slave.destroy()
        for i, row_id in enumerate(self.rows):
            btn_mode = ttk.Button(master=self.master,
                             text=self.rows[row_id]['mode'],
                             width=self.field_size,
                             command=partial(self.remove_row, row_id))
            btn_mode.grid(row=i, column=0)
            entry_countdown = ttk.Entry(self.master,
                             textvariable=self.rows[row_id]['countdown'],
                             width=5,
                             justify='center')

            vcmd = (self.master.register(self.validate_duration), '%P')
            entry_countdown.config(validate='key', validatecommand=vcmd)

            entry_countdown.grid(row=i, column=1, padx=5)
            self.rows[row_id].update({'btn_mode': btn_mode, 'entry_countdown': entry_countdown})

    def add_row(self, mode, duration=None):
        row_id = time_ns()
        duration = duration or self.DEFAULT_DURATION
        self.rows[row_id] = {'mode': mode, 'duration': duration, 'countdown': tk.DoubleVar()}
        self.rows[row_id]['countdown'].set(duration)
        self.build()
        self.parent.on_table_sequence_updated()
        return row_id

    def remove_row(self, row_id):
        row = self.rows.pop(row_id)
        self.build()
        self.parent.on_table_sequence_updated()
        return row

    def validate_duration(self, value):
        return value == '' or value.isnumeric()


from re import findall
class MionSequenceProcessor:
    def __init__(self, ui):
        self.ui = ui

    def convert_port_token(self, port_token):
        # input: decimal, hex, (dec, dec) of (hex, hex) strings
        port = None
        if isinstance(port_token, int):
            return port_token
        port_token = port_token.replace(' ', '').lower()
        hex_ptn = r'^\((0x[0-9a-fA-F]+)\,(0x[0-9a-fA-F]+)\)$'
        dec_ptn = r'^\((\d+)\,(\d+)\)$'
        for ptn in [hex_ptn, dec_ptn]:
            try:
                port = findall(ptn, port_token)[0]
            except IndexError:
                pass
        if port is None:
            return port
        for ord in [10, 16]:
            try:
                port = (int(port[0], ord), int(port[1], ord))
            except ValueError:
                pass
        return port

    def fetch_setpoints(self, config):
        setpoints = {}
        for node_id_token, port_map in config.items():
            node_id = NodeId[node_id_token]
            setpoints[node_id] = {}
            for port_token, setpoint in port_map.items():
                port = self.convert_port_token(port_token)
                setpoints[node_id][port] = setpoint
        return setpoints

    def load_job_config(self, mode):
        config = self.ui.app.kecu.mion_modes[mode]
        setpoints = self.fetch_setpoints(config)
        return setpoints

    async def update_setpoints(self, job, setpoints):
        def RCP_bug_here():
            return self.ui.app.kecu._app.is_broken
        for node_id in setpoints:
            for field in self.ui.app.fields[node_id]:
                value = setpoints[node_id].get(field.channel)
                if value is not None:
                    while not self.ui.stop_event.is_set():
                        if RCP_bug_here():  # RCP bug workaround: wait to reconnect and repeat
                            await asyncio.sleep(2)
                            continue
                        logger.debug(f"-'{field.parent_frame['text']}'/'{field.label_text}' = {value}")
                        if field.cb_value is not None:
                            field.update_checkbox(value)
                            field.on_checkbox_toggled()
                        if field.set_value is not None:
                            field.set(value)
                            field.on_setpoint_changed(None)
                        if RCP_bug_here():  # RCP bug manifests on updating setpoint
                            continue
                        else:
                            break


    async def run_job(self, job):
        # setpoints = self.load_job_config(job['mode'] + '.yaml')
        setpoints = self.load_job_config(job['mode'])
        await self.update_setpoints(job, setpoints)
        while not self.ui.stop_event.is_set() and job['countdown'].get() > 0:
            await asyncio.sleep(1)


class MionSequencerUI:
    def __init__(self, app, master_frame):
        self.app = app
        self.master_frame = master_frame
        self.modes = app.kecu.mion_modes
        self.sequence = app.kecu.mion_sequence
        self.processor = MionSequenceProcessor(self)
        self.btn_run = None
        self.table_modes = None
        self.table_sequence = None
        self.rcp_reconnect_shift = 4    # TODO: RCP bug workaround
        self.stop_event = Event()

    def build(self):
        def update_sequence(mode):
            self.table_sequence.add_row(mode)

        frame_switch = ttk.LabelFrame(self.master_frame, text="MION sequencer")
        frame_switch.grid(row=0, column=1, sticky='N', padx=10, pady=5)

        self.btn_run = ttk.Button(frame_switch, text='Start', command=self.trigger_sequence)
        self.btn_run.grid(row=0, column=1, pady=5)

        frame_modes = ttk.LabelFrame(frame_switch, text="Modes", height=55, width=120)
        frame_modes.grid(row=1, column=0, padx=10, pady=10)
        self.table_modes = MionModesTable(self, frame_modes, update_sequence)

        frame_sequence = ttk.LabelFrame(frame_switch, text="Sequence", height=55, width=120)
        frame_sequence.grid(row=1, column=1, sticky='N', padx=10, pady=10)

        self.table_sequence = MionSequenceTable(self, frame_sequence,
                                                processor=self.processor)
        self.on_table_sequence_updated()

    def _get_job(self, index):
        job_ids = list(self.table_sequence.rows)
        njobs = len(job_ids)
        job_id = job_ids[index % njobs]
        job = self.table_sequence.rows[job_id]
        return job_id, job

    def set_ui_mode(self, running=True):
        if running:
            self.btn_run['text'] = 'Stop'
        else:
            self.btn_run['text'] = 'Start'
        for row in self.table_modes.rows.values():
            row['state'] = 'disabled' if running else 'enabled'
        for row in self.table_sequence.rows.values():
            row['btn_mode']['state'] = 'disabled' if running else 'enabled'
            row['entry_countdown']['state'] = 'disabled' if running else 'enabled'

    def restore_countdown(self, job):
        job['countdown'].set(job['duration'])

    def highlight_row(self, job, running=True):
        if running:
            job['btn_mode']['text'] = '* ' + job['mode']
            job['entry_countdown'].focus_set()
        else:
            job['btn_mode']['text'] = job['mode']


    def trigger_sequence(self, index=0):
        def stop_clicked():
            return index == 0 and self.btn_run['text'] == 'Stop'
        def rcp_bug_adjust_job_duration():
            min_mode_duration = self.app.kecu.min_mode_duration
            rcp_reconnect_timeout = self.app.kecu.rcp_reconnect_timeout + self.rcp_reconnect_shift
            jobs = list(self.table_sequence.rows.values())
            for i, job in enumerate(jobs):
                new_duration = rcp_reconnect_timeout if i==len(jobs)-1 else min_mode_duration
                job_duration = job['countdown'].get()
                if job_duration < new_duration:
                    job['countdown'].set(new_duration)
        def set_job_durations_from_ui():
            for job in self.table_sequence.rows.values():
                job['duration'] = job['countdown'].get()

        if stop_clicked():
            self.stop_event.set()
            return
        if index == 0:
            rcp_bug_adjust_job_duration()
            set_job_durations_from_ui()     # save user input if any
        if not self.app.kecu.connected:
            logger.error("No go: KECU is not connected.")
            return

        self.app.loop.create_task(
            self.countdown(index)
        )
        self.app.loop.create_task(
            self.run_job(index)
        )


    async def on_job_started(self, index):
        if index == 0:
            self.set_ui_mode(running=True)
        _, job = self._get_job(index)
        self.highlight_row(job)
        self.app.kecu.sequencer_mode = job['mode']


    async def on_job_finished(self, index):
        def RCP_bug_here():
            return self.app.kecu._app.is_broken

        _, job = self._get_job(index)
        self.restore_countdown(job)
        self.highlight_row(job, False)
        self.app.kecu.sequencer_mode = None

        while not self.stop_event.is_set():
            if self.app.kecu.rcp_reconnect_in_progress:
                logger.info('RCP reconnect in progress...')
                await asyncio.sleep(1)
                continue
            if not RCP_bug_here():
                break
            logger.info('TCP Client not ready...')
            await asyncio.sleep(1)

        if not self.stop_event.is_set():
            self.trigger_sequence(index + 1)
        else:
            self.stop_event.clear()
            self.set_ui_mode(running=False)


    def on_table_sequence_updated(self):
        if self.table_sequence and len(self.table_sequence.rows) > 1:
            self.btn_run.state(['!disabled'])
        else:
            self.btn_run.state(['disabled'])


    async def countdown(self, index):
        sequence_lenth = len(list(self.table_sequence.rows))
        index_for_rcp_reconnect = index % sequence_lenth == sequence_lenth - 1
        def time_for_rcp_reconnect(count):
            return index_for_rcp_reconnect and count == self.app.kecu.rcp_reconnect_timeout

        _, job = self._get_job(index)
        count = job['countdown'].get()
        while not self.stop_event.is_set() and count > 0:
            if time_for_rcp_reconnect(count):
                await self.app.kecu._app.simulate_RCP_bug()
            await asyncio.sleep(1)
            count -= 1
            job['countdown'].set(count)


    async def run_job(self, index):
        sequence_lenth = len(list(self.table_sequence.rows))
        if index % sequence_lenth == 0:
            logger.info(f'Sequence cycle #{index // sequence_lenth}')

        await self.on_job_started(index)

        _, job = self._get_job(index)
        await self.processor.run_job(job)

        if self.stop_event.is_set():    # let countdown loop finishes
            await asyncio.sleep(1.5)
        await self.on_job_finished(index)


class App(tk.Tk):
    version = '1.0.4'

    def __init__(self, loop, kecu, tasks=[], interval=.1):
        """UI

        Tkinter application

        Parameters
        ----------
        loop : loop
            asyncio event loop
        kecu : KECU
            KECU instance
        tasks : list, optional
            list of asyncio tasks, by default []
        interval : float, optional
            UI update interval (seconds), by default .1
        """
        super().__init__()
        logger.info(f"version: {self.version}")
        self.loop = loop
        self.kecu = kecu
        self.instruments = kecu.instruments
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.tasks = tasks
        self.tasks.append(loop.create_task(self.updater(interval)))
        self.fields = defaultdict(list)
        self.status_fields = {}

        self.build()
        self.style()
        self.update_fields(self.kecu.nodes)

    def build(self):
        """Build UI
        """
        def build_kecu_frame():
            kecu_frame = ttk.LabelFrame(self, text="KECU")
            kecu_frame.grid(row=0, column=0, columnspan=4)

            connected_str = tk.StringVar()
            connected_str.set(f"Connecting to {self.kecu._app._host} : {self.kecu._app._port}...")
            connected_label = ttk.Label(
                kecu_frame,
                textvariable=connected_str
                )
            connected_label.grid(row=0, column=0, columnspan=2)

            version_label_str = tk.StringVar()
            version_label_str.set("FW version")
            version_label = ttk.Label(
                kecu_frame,
                textvariable=version_label_str
                )
            version_label.grid(row=1, column=0)

            version_str = tk.StringVar()
            version_str.set("unknown")
            version_value = ttk.Entry(
                kecu_frame,
                textvariable=version_str,
                state='disabled'
                )
            version_value.grid(row=1, column=1)

            self.status_fields.update({'connected': connected_str})
            self.status_fields.update({'version_label': version_label_str})
            self.status_fields.update({'version': version_str})

        def build_mion2_frame():
            # MION2 frame
            mion2_frame = ttk.LabelFrame(self, text="MION2")
            mion2_frame.grid(row=1, column=0, rowspan=3, sticky='N', padx=10, pady=10)

            mion2_common_frame = ttk.LabelFrame(
                mion2_frame,
                text="Common",
            )
            mion2_is1_frame = ttk.LabelFrame(
                mion2_frame,
                text="Ion source 1",
            )
            mion2_is2_frame = ttk.LabelFrame(
                mion2_frame,
                text="Ion source 2",
            )
            mion2_xray_frame = ttk.LabelFrame(
                mion2_common_frame,
                text="X-ray",
            )
            mion2_if_frame = ttk.LabelFrame(
                mion2_common_frame,
                text="Ion filter",
            )
            mion2_sensor_frame = ttk.LabelFrame(
                mion2_common_frame,
                text="Sensors",
            )

            mion2_common_frame.grid(row=0, column=0, padx=10, pady=10)
            mion2_xray_frame.grid(row=1, column=0, padx=10, pady=10)
            mion2_if_frame.grid(row=2, column=0, padx=10, pady=10)
            mion2_sensor_frame.grid(row=3, column=0, padx=10, pady=10)
            
            mion2_is1_frame.grid(row=1, column=0, padx=10, pady=10)
            mion2_is2_frame.grid(row=2, column=0, padx=10, pady=10)

            self.build_mion_sequencer(mion2_frame)

            # MION2:Common
            self.fields[NodeId.MION2_MFC_MAIN].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_MAIN,
                    "Main flow",
                    mion2_common_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION1v5_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    1,
                    "X-ray enabled",
                    mion2_xray_frame,
                    row=2,
                    column=0
                )
            )
            self.fields[NodeId.MION1v5_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    0,
                    "X-ray alert",
                    mion2_xray_frame,
                    row=4,
                    column=0
                )
            )
            # /
            # MION2:Ion filter
            self.fields[NodeId.MION1v5_DIO].append(
                DoField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    5,
                    "Power",
                    mion2_if_frame,
                    row=0,
                    column=0
                )
            )   
            self.fields[NodeId.MION2_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION2_AI,
                    4,
                    "HV-",
                    mion2_if_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION2_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION2_AI,
                    5,
                    "HV+",
                    mion2_if_frame,
                    row=2,
                    column=0
                )
            )
            # /
            # MION2:Sensors
            self.fields[NodeId.MION2_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION2_AI,
                    0,
                    "Humidity",
                    mion2_sensor_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION2_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION2_AI,
                    1,
                    "Temperature",
                    mion2_sensor_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION2_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION2_AI,
                    2,
                    "Pressure",
                    mion2_sensor_frame,
                    row=2,
                    column=0
                )
            )
            # /
            # MION2:IS1
            self.fields[NodeId.MION2_MFC_SRC1_PRG].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_SRC1_PRG,
                    "Purge flow",
                    mion2_is1_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION2_MFC_SRC1_RGT].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_SRC1_RGT,
                    "Reagent flow",
                    mion2_is1_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION2_MFC_SRC1_EXH].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_SRC1_EXH,
                    "Exhaust flow",
                    mion2_is1_frame,
                    row=2,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC1_VALVE].append(
                DoField(
                    self.kecu,
                    NodeId.MION2_SRC1_VALVE,
                    (0x2540, 0x01),
                    "Reagent valve toggle",
                    mion2_is1_frame,
                    row=3,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC1_VALVE].append(
                DiField(
                    self.kecu,
                    NodeId.MION2_SRC1_VALVE,
                    (0x2500, 0x01),
                    "Reagent valve open",
                    mion2_is1_frame,
                    row=4,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC1_HV].append(
                VoltageField(
                    self.kecu,
                    NodeId.MION2_SRC1_HV,
                    1,
                    "Accelerator (HV1)",
                    mion2_is1_frame,
                    row=5,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC1_HV].append(
                VoltageField(
                    self.kecu,
                    NodeId.MION2_SRC1_HV,
                    2,
                    "Deflector (HV2)",
                    mion2_is1_frame,
                    row=6,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC1_HV].append(
                VoltageField(
                    self.kecu,
                    NodeId.MION2_SRC1_HV,
                    3,
                    "HV3",
                    mion2_is1_frame,
                    row=7,
                    column=0
                )
            )
            self.fields[NodeId.MION1v5_DIO].append(
                DoField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    4,
                    "X-ray toggle",
                    mion2_is1_frame,
                    row=8,
                    column=0
                )
            )
            self.fields[NodeId.MION1v5_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    2,
                    "X-ray active",
                    mion2_is1_frame,
                    row=9,
                    column=0
                )
            )
            # /
            # MION2:IS2
            self.fields[NodeId.MION2_MFC_SRC2_PRG].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_SRC2_PRG,
                    "Purge flow",
                    mion2_is2_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION2_MFC_SRC2_RGT].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_SRC2_RGT,
                    "Reagent flow",
                    mion2_is2_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION2_MFC_SRC2_EXH].append(
                MfcField(
                    self.kecu,
                    NodeId.MION2_MFC_SRC2_EXH,
                    "Exhaust flow",
                    mion2_is2_frame,
                    row=2,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC2_VALVE].append(
                DoField(
                    self.kecu,
                    NodeId.MION2_SRC2_VALVE,
                    (0x2540, 0x01),
                    "Reagent valve toggle",
                    mion2_is2_frame,
                    row=3,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC2_VALVE].append(
                DiField(
                    self.kecu,
                    NodeId.MION2_SRC2_VALVE,
                    (0x2500, 0x01),
                    "Reagent valve open",
                    mion2_is2_frame,
                    row=4,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC2_HV].append(
                VoltageField(
                    self.kecu,
                    NodeId.MION2_SRC2_HV,
                    1,
                    "Accelerator (HV1)",
                    mion2_is2_frame,
                    row=5,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC2_HV].append(
                VoltageField(
                    self.kecu,
                    NodeId.MION2_SRC2_HV,
                    2,
                    "Deflector (HV2)",
                    mion2_is2_frame,
                    row=6,
                    column=0
                )
            )
            self.fields[NodeId.MION2_SRC2_HV].append(
                VoltageField(
                    self.kecu,
                    NodeId.MION2_SRC2_HV,
                    3,
                    "HV3",
                    mion2_is2_frame,
                    row=7,
                    column=0
                )
            )
            self.fields[NodeId.MION1v5_DIO].append(
                DoField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    7,
                    "X-ray toggle",
                    mion2_is2_frame,
                    row=8,
                    column=0
                )
            )
            self.fields[NodeId.MION1v5_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION1v5_DIO,
                    3,
                    "X-ray active",
                    mion2_is2_frame,
                    row=9,
                    column=0
                )
            )

        def build_mion_frame():
            # MION frame
            mion_frame = ttk.LabelFrame(self, text="MION")
            mion_frame.grid(row=1, column=1, rowspan=3, sticky='N', padx=10, pady=10)

            mion_common_frame = ttk.LabelFrame(
                mion_frame,
                text="Common",
            )
            mion_is1_frame = ttk.LabelFrame(
                mion_frame,
                text="Ion source 1",
            )
            mion_is2_frame = ttk.LabelFrame(
                mion_frame,
                text="Ion source 2",
            )
            mion_xray_frame = ttk.LabelFrame(
                mion_common_frame,
                text="X-ray",
            )
            mion_if_frame = ttk.LabelFrame(
                mion_common_frame,
                text="Ion filter",
            )
            mion_sensor_frame = ttk.LabelFrame(
                mion_common_frame,
                text="Sensors",
            )

            mion_common_frame.grid(row=0, column=0, padx=10, pady=10)
            mion_xray_frame.grid(row=1, column=0, padx=10, pady=10)
            mion_if_frame.grid(row=2, column=0, padx=10, pady=10)
            mion_sensor_frame.grid(row=3, column=0, padx=10, pady=10)
            mion_is1_frame.grid(row=1, column=0, padx=10, pady=10)
            mion_is2_frame.grid(row=2, column=0, padx=10, pady=10)

            self.build_mion_sequencer(mion_frame)

            # MION:Common
            self.fields[NodeId.MION_MFC5_MAIN].append(
                MfcField(
                    self.kecu,
                    NodeId.MION_MFC5_MAIN,
                    "Main flow",
                    mion_common_frame,
                    row=0,
                    column=0
                )
            )
            # /
            # MION:IS1
            self.fields[NodeId.MION_MFC2_SRC1_CRR].append(
                MfcField(
                    self.kecu,
                    NodeId.MION_MFC2_SRC1_CRR,
                    "Carrier flow",
                    mion_is1_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION_MFC1_SRC1_EXH].append(
                MfcField(
                    self.kecu,
                    NodeId.MION_MFC1_SRC1_EXH,
                    "Exhaust flow",
                    mion_is1_frame,
                    row=1,
                    column=0
                )
            )
            # /
            # MION:IS2
            self.fields[NodeId.MION_MFC4_SRC2_CRR].append(
                MfcField(
                    self.kecu, 
                    NodeId.MION_MFC4_SRC2_CRR,
                    "Carrier flow",
                    mion_is2_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION_MFC3_SRC2_EXH].append(
                MfcField(
                    self.kecu,
                    NodeId.MION_MFC3_SRC2_EXH,
                    "Exhaust flow",
                    parent_frame=mion_is2_frame,
                    row=1,
                    column=0
                )
            )
            # /
            # MION:X-ray
            self.fields[NodeId.MION_DIO].append(
                DoField(
                    self.kecu,
                    NodeId.MION_DIO,
                    4,
                    "Emission",
                    mion_xray_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION_DIO,
                    3,
                    "Active",
                    mion_xray_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION_DIO,
                    1,
                    "Enabled",
                    mion_xray_frame,
                    row=2, 
                    column=0
                )
            )
            self.fields[NodeId.MION_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION_DIO,
                    2,
                    "Interlock",
                    mion_xray_frame,
                    row=3,
                    column=0
                )
            )
            self.fields[NodeId.MION_DIO].append(
                DiField(
                    self.kecu,
                    NodeId.MION_DIO,
                    0,
                    "Alert",
                    mion_xray_frame,
                    row=4,
                    column=0
                )
            )
            # /
            # MION:Ion filter
            self.fields[NodeId.MION_DIO].append(
                DoField(
                    self.kecu,
                    NodeId.MION_DIO,
                    5,
                    "Toggle",
                    mion_if_frame,
                    row=0,
                    column=0
                )
            )   
            self.fields[NodeId.MION_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION_AI,
                    4,
                    "HV-",
                    mion_if_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION_AI,
                    5,
                    "HV+",
                    mion_if_frame,
                    row=2,
                    column=0
                )
            )
            # /
            # MION:Sensors
            self.fields[NodeId.MION_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION_AI,
                    0,
                    "Humidity",
                    mion_sensor_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.MION_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION_AI,
                    1,
                    "Temperature",
                    mion_sensor_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.MION_AI].append(
                MonitorField(
                    self.kecu,
                    NodeId.MION_AI,
                    2,
                    "Pressure",
                    mion_sensor_frame,
                    row=2,
                    column=0
                )
            )

        def build_scenthound_frame():
            # Scenthound
            sh_frame = ttk.LabelFrame(self, text="Scenthound")
            sh_frame.grid(row=1, column=2, rowspan=1, sticky='N', padx=10)

            sh_mfc_frame = ttk.LabelFrame(
                sh_frame,
                text="Mass flow controllers",
            )
            sh_mfc_frame.grid(row=0, column=0, padx=10, pady=10)
            # SH:Flows
            self.fields[NodeId.SH_MFC5_RGT].append(
                MfcField(
                    self.kecu,
                    NodeId.SH_MFC5_RGT,
                    "Reagent flow",
                    sh_mfc_frame,
                    row=0,
                    column=0
                )
            )
            self.fields[NodeId.SH_MFC3_SMP].append(
                MfcField(
                    self.kecu,
                    NodeId.SH_MFC3_SMP,
                    "Sample flow",
                    sh_mfc_frame,
                    row=1,
                    column=0
                )
            )
            self.fields[NodeId.SH_MFC2_EXH].append(
                MfcField(
                    self.kecu,
                    NodeId.SH_MFC2_EXH,
                    "Exhaust flow",
                    sh_mfc_frame,
                    row=2,
                    column=0
                )
            )
            self.fields[NodeId.SH_MFC4_SHT1].append(
                MfcField(
                    self.kecu,
                    NodeId.SH_MFC4_SHT1,
                    "Sheath 1 flow",
                    sh_mfc_frame,
                    row=3,
                    column=0
                )
            )
            self.fields[NodeId.SH_MFC1_SHT2].append(
                MfcField(
                    self.kecu,
                    NodeId.SH_MFC1_SHT2,
                    "Sheath 2 flow",
                    sh_mfc_frame,
                    row=4,
                    column=0
                )
            )

        def build_calibrator_frame():
            # Calibrator
            cal_frame = ttk.LabelFrame(self, text="Calibrator")
            cal_frame.grid(row=1, column=3, sticky='N', padx=10)

            self.fields[NodeId.CALIB_MFC].append(
                MfcField(
                    self.kecu,
                    NodeId.CALIB_MFC,
                    "Carrier flow",
                    cal_frame,
                    row=0,
                    column=0,
                    padx=10,
                    pady=10
                )
            )

        def build_flushplate_frame():
            # Flushplate
            fp_frame = ttk.LabelFrame(self, text="Flushplate")
            fp_frame.grid(row=2, column=3, sticky='N', padx=10)

            self.fields[NodeId.FLSHP_MFC].append(
                MfcField(
                    self.kecu,
                    NodeId.FLSHP_MFC,
                    "Counter flow",
                    fp_frame,
                    row=0,
                    column=0,
                    padx=10,
                    pady=10
                )
            )

        if self.instruments == 'all':
            build_kecu_frame()
            build_mion2_frame()
            build_mion_frame()
            build_scenthound_frame()
            build_calibrator_frame()
            build_flushplate_frame()
        else:
            build_kecu_frame()
            instruments = self.instruments.split(',')
            for instr in instruments:
                build_frame = locals()[f"build_{instr}_frame"]
                build_frame()


    def build_mion_sequencer(self, master_frame=None):
        mion_sequencer = MionSequencerUI(self, master_frame or self)
        mion_sequencer.build()


    def close(self):
        self.loop.create_task(
            asyncio.wait_for(
                self.kecu.disconnect(),
                timeout=None
            )
        )
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()

    def style(self):
        self.title(f"KECU UI v.{self.version}")
        style = ttk.Style(self)
        style.theme_use('clam')
        self.configure(background='gainsboro')
        # self.geometry('400x400')
        # self.configure(background='grey')

    def update_fields(self, nodes):
        """Enable UI fields whose node is present
        """
        for node, node_fields in self.fields.items():
            for field in node_fields:
                field.update()
                field.enable()
                if self.kecu and node in nodes:
                    field.enable()
                else:
                    field.disable()
        self.status_fields['version'].set("unknown")

    def update_status(self):
        if self.kecu.connected:
            self.status_fields['connected'].set(f"Connected to {self.kecu._app._host} : {self.kecu._app._port}")
            if self.status_fields['version'].get() == "unknown":
                self.status_fields['version'].set(self.kecu.version)
        else:
            self.status_fields['connected'].set(f"Connecting to {self.kecu._app._host} : {self.kecu._app._port}...")

    async def updater(self, interval):
        """Updater task to handle UI as an asyncio task
        """
        while True:
            self.update()
            self.update_status()
            await asyncio.sleep(interval)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = []
    kecu = None
    app = App(loop, kecu, tasks=tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        app.close()
