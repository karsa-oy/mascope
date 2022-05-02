import asyncio
import tkinter as tk

from collections import defaultdict

from .nodes import NodeId

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
        self.frame = tk.Frame(parent_frame)
        if row is not None and column is not None:
            self.frame.grid(
                row=row,
                column=column,
                sticky=sticky,
                padx=padx,
                pady=pady
                )
        self.label = tk.Label(self.frame, text=label).grid(row=0, column=0)
        if monitorable:
            self.mon_value = tk.DoubleVar()
            self.mon_entry = tk.Entry(self.frame,
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
            self.set_entry = tk.Entry(self.frame,
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
            self.checkbox = tk.Checkbutton(self.frame,
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
        self.update()

    def update(self):
        if self.kecu:
            node = self.kecu.nodes.get(self.node_id, None)
            if node:
                device = node._device
                device.channels[(0x2F00, 0x01)].callbacks.append(
                    self.update_setpoint
                ) # On read setpoint
                device.channels[(0x2C00, 0x01)].callbacks.append(
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
        

class App(tk.Tk):
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
        self.loop = loop
        self.kecu = kecu
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
            kecu_frame = tk.LabelFrame(text="KECU", bd=1)
            kecu_frame.grid(row=0, column=0, columnspan=4)
            connected_str = tk.StringVar()
            connected_str.set("Connecting...")
            connected_label = tk.Label(
                kecu_frame,
                textvariable=connected_str
                )
            connected_label.grid(row=0, column=0)

            version_label_str = tk.StringVar()
            version_label_str.set("FW version")
            version_label = tk.Label(
                kecu_frame,
                textvariable=version_label_str
                )
            version_label.grid(row=1, column=0)

            version_str = tk.StringVar()
            version_str.set("unknown")
            version_value = tk.Entry(
                kecu_frame,
                textvariable=version_str,
                state='disabled'
                )
            version_value.grid(row=1, column=1)

            self.status_fields.update({'connected': connected_str})
            self.status_fields.update({'version': version_str})


        def build_mion2_frame():
            # MION2 frame
            mion2_frame = tk.LabelFrame(text="MION2", bd=1)
            mion2_frame.grid(row=1, column=0, rowspan=3, sticky='N', padx=10)

            mion2_common_frame = tk.LabelFrame(
                mion2_frame,
                text="Common",
                bd=1
            )
            mion2_is1_frame = tk.LabelFrame(
                mion2_frame,
                text="Ion source 1",
                bd=1
            )
            mion2_is2_frame = tk.LabelFrame(
                mion2_frame,
                text="Ion source 2",
                bd=1
            )
            mion2_xray_frame = tk.LabelFrame(
                mion2_common_frame,
                text="X-ray",
                bd=1
            )
            mion2_if_frame = tk.LabelFrame(
                mion2_common_frame,
                text="Ion filter",
                bd=1
            )
            mion2_sensor_frame = tk.LabelFrame(
                mion2_common_frame,
                text="Sensors",
                bd=1
            )

            mion2_common_frame.grid(row=0, column=0, padx=10, pady=10)
            mion2_xray_frame.grid(row=1, column=0, padx=10, pady=10)
            mion2_if_frame.grid(row=2, column=0, padx=10, pady=10)
            mion2_sensor_frame.grid(row=3, column=0, padx=10, pady=10)
            
            mion2_is1_frame.grid(row=1, column=0, padx=10, pady=10)
            mion2_is2_frame.grid(row=2, column=0, padx=10, pady=10)

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
            mion_frame = tk.LabelFrame(text="MION", bd=1)
            mion_frame.grid(row=1, column=1, rowspan=3, sticky='N', padx=10)

            mion_common_frame = tk.LabelFrame(
                mion_frame,
                text="Common",
                bd=1
            )
            mion_is1_frame = tk.LabelFrame(
                mion_frame,
                text="Ion source 1",
                bd=1
            )
            mion_is2_frame = tk.LabelFrame(
                mion_frame,
                text="Ion source 2",
                bd=1
            )
            mion_xray_frame = tk.LabelFrame(
                mion_common_frame,
                text="X-ray",
                bd=1
            )
            mion_if_frame = tk.LabelFrame(
                mion_common_frame,
                text="Ion filter",
                bd=1
            )
            mion_sensor_frame = tk.LabelFrame(
                mion_common_frame,
                text="Sensors",
                bd=1
            )

            mion_common_frame.grid(row=0, column=0, padx=10, pady=10)
            mion_xray_frame.grid(row=1, column=0, padx=10, pady=10)
            mion_if_frame.grid(row=2, column=0, padx=10, pady=10)
            mion_sensor_frame.grid(row=3, column=0, padx=10, pady=10)
            mion_is1_frame.grid(row=1, column=0, padx=10, pady=10)
            mion_is2_frame.grid(row=2, column=0, padx=10, pady=10)

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
            sh_frame = tk.LabelFrame(text="Scenthound", bd=1)
            sh_frame.grid(row=1, column=2, rowspan=1, sticky='N', padx=10)

            sh_mfc_frame = tk.LabelFrame(
                sh_frame,
                text="Mass flow controllers",
                bd=1
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
            cal_frame = tk.LabelFrame(text="Calibrator", bd=1)
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
            fp_frame = tk.LabelFrame(text="Flushplate", bd=1)
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

        build_kecu_frame()
        build_mion2_frame()
        build_mion_frame()
        build_scenthound_frame()
        build_calibrator_frame()
        build_flushplate_frame()

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
        self.title("KECU")
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

    def update_status(self):
        if self.kecu.connected:
            self.status_fields['connected'].set("Connected")
            self.status_fields['version'].set(self.kecu.version)
        else:
            self.status_fields['connected'].set("Connecting...")
            self.status_fields['version'].set("unknown")

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