import asyncio
import sys
import tkinter as tk

from collections import defaultdict

from karsaecu.nodes import NodeId
from services.KECUService import KECU, initialize_kecu


kecu = None


class Field():
    def __init__(self, node_id, label, parent_frame, monitorable, settable, toggleable, row=None, column=None):
        self.node_id = node_id
        self.frame = tk.Frame(parent_frame)
        if row is not None and column is not None:
            self.frame.grid(row=row, column=column)
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
        for cb in self.cb_value_callbacks:
            asyncio.create_task( cb(self.channel, self.cb_value.get()) )

    def on_setpoint_changed(self, event):
        # TODO: Possibly add validation here
        self.set(self.set_value.get())
        for cb in self.set_value_callbacks:
            asyncio.create_task( cb(self.set_value.get()) )

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
    def __init__(self, node_id, channel, label, parent_frame, **kwargs):
        super().__init__(node_id,
                         label,
                         parent_frame,
                         monitorable=False,
                         settable=False,
                         toggleable=True,
                         **kwargs
                         )
        self.checkbox.configure(state=tk.DISABLED)
        global kecu
        if kecu:
            node = kecu.nodes.get(node_id, None)
            if node:
                device = node._device
                device.channels[channel].callbacks.append(self.update_checkbox)

    def enable(self):
        try:
            self.set_entry.configure(state=tk.NORMAL)
        except AttributeError:
            pass

class DoField(Field):
    def __init__(self, node_id, channel, label, parent_frame, **kwargs):
        super().__init__(node_id,
                         label,
                         parent_frame,
                         monitorable=False,
                         settable=False,
                         toggleable=True,
                         **kwargs
                         )
        global kecu
        self.channel = channel
        if kecu:
            node = kecu.nodes.get(node_id, None)
            if node:
                device = node._device
                device.channels[channel].callbacks.append(self.update_checkbox)
                self.cb_value_callbacks.append(node.set_channel)

class MfcField(Field):
    def __init__(self, node_id, label, parent_frame, **kwargs):
        super().__init__(node_id,
                         label,
                         parent_frame,
                         monitorable=True,
                         settable=True,
                         toggleable=False,
                         **kwargs
                         )
        global kecu
        if kecu:
            node = kecu.nodes.get(node_id, None)
            if node:
                device = node._device
                device.channels[(0x2F00, 0x01)].callbacks.append(self.update_setpoint) # On read setpoint
                device.channels[(0x2C00, 0x01)].callbacks.append(self.update_monitor) # On read actual flow
                self.set_value_callbacks.append(node.set_flow)

class MonitorField(Field):
    def __init__(self, node_id, channel, label, parent_frame, **kwargs):
        super().__init__(node_id,
                         label,
                         parent_frame,
                         monitorable=True,
                         settable=False,
                         toggleable=False,
                         **kwargs
                         )
        global kecu
        if kecu:
            node = kecu.nodes.get(node_id, None)
            if node:
                device = node._device
                device.channels[channel].callbacks.append(self.update_monitor)

class VoltageField(Field):
    def __init__(self, node_id, label, parent_frame, **kwargs):
        super().__init__(node_id,
                         label,
                         parent_frame,
                         monitorable=True,
                         settable=True,
                         toggleable=True,
                         **kwargs
                         )


class App(tk.Tk):
    def __init__(self, loop, kecu, tasks=[], interval=.1):
        super().__init__()
        self.loop = loop
        self.kecu = kecu
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.tasks = tasks
        self.tasks.append(loop.create_task(self.updater(interval)))
        self.fields = defaultdict(list)
        self.build()
        self.style()
        self.update_fields()

    def build(self):
        global kecu
        # Main frame components
        mion_frame = tk.LabelFrame(text="MION", bd=1)
        sh_frame = tk.LabelFrame(text="Scenthound", bd=1)
        cal_frame = tk.LabelFrame(text="Calibrator", bd=1)
        fp_frame = tk.LabelFrame(text="Flushplate", bd=1)
        # Grid 'em
        mion_frame.grid(row=0, column=0, sticky='EW')
        sh_frame.grid(row=1, column=0, sticky='EW')
        cal_frame.grid(row=2, column=0, sticky='EW')
        fp_frame.grid(row=3, column=0, sticky='EW')

        # MION frame
        mion_common_frame = tk.LabelFrame(mion_frame, text="Common", bd=1)
        mion_is1_frame = tk.LabelFrame(mion_frame, text="Ion source 1", bd=1)
        mion_is2_frame = tk.LabelFrame(mion_frame, text="Ion source 2", bd=1)
        mion_xray_frame = tk.LabelFrame(mion_frame, text="X-ray", bd=1)
        mion_if_frame = tk.LabelFrame(mion_frame, text="Ion filter", bd=1)
        mion_sensor_frame = tk.LabelFrame(mion_frame, text="Sensors", bd=1)

        mion_common_frame.grid(row=0, column=0)
        mion_is1_frame.grid(row=1, column=0)
        mion_is2_frame.grid(row=2, column=0)
        mion_xray_frame.grid(row=3, column=0)
        mion_if_frame.grid(row=4, column=0)
        mion_sensor_frame.grid(row=5, column=0)

        # MION:Common
        self.fields[NodeId.MION_MFC5_MAIN].append(MfcField(NodeId.MION_MFC5_MAIN, "Main flow", mion_common_frame, row=0, column=0))
        VoltageField(NodeId.ALL_NODES, "Accelerator voltage", mion_common_frame, row=1, column=0)
        # /
        # MION:IS1
        self.fields[NodeId.MION_MFC2_SRC1_CRR].append(MfcField(NodeId.MION_MFC2_SRC1_CRR, "Carrier flow", mion_is1_frame, row=0, column=0))
        self.fields[NodeId.MION_MFC1_SRC1_EXH].append(MfcField(NodeId.MION_MFC1_SRC1_EXH, "Exhaust flow", mion_is1_frame, row=1, column=0))
        VoltageField(NodeId.ALL_NODES, "Deflector voltage", mion_is1_frame, row=2, column=0)
        # /
        # MION:IS2
        self.fields[NodeId.MION_MFC4_SRC2_CRR].append(MfcField(NodeId.MION_MFC4_SRC2_CRR, "Carrier flow", mion_is2_frame, row=0, column=0))
        self.fields[NodeId.MION_MFC3_SRC2_EXH].append(MfcField(NodeId.MION_MFC3_SRC2_EXH, "Exhaust flow", parent_frame=mion_is2_frame, row=1, column=0))
        VoltageField(NodeId.ALL_NODES, "Deflector voltage", mion_is2_frame, row=2, column=0)
        # /
        # MION:X-ray
        self.fields[NodeId.MION_DIO].append(DoField(NodeId.MION_DIO, 4, "Emission", mion_xray_frame, row=0, column=0))
        self.fields[NodeId.MION_DIO].append(DiField(NodeId.MION_DIO, 3, "Active", mion_xray_frame, row=1, column=0))
        self.fields[NodeId.MION_DIO].append(DiField(NodeId.MION_DIO, 1, "Enabled", mion_xray_frame, row=2, column=0))
        self.fields[NodeId.MION_DIO].append(DiField(NodeId.MION_DIO, 2, "Interlock", mion_xray_frame, row=3, column=0))
        self.fields[NodeId.MION_DIO].append(DiField(NodeId.MION_DIO, 0, "Alert", mion_xray_frame, row=4, column=0))
        # /
        # MION:Ion filter
        self.fields[NodeId.MION_DIO].append(DoField(NodeId.MION_DIO, 5, "Power", mion_if_frame, row=0, column=0))   
        self.fields[NodeId.MION_AI].append(MonitorField(NodeId.MION_AI, 4, "HV+", mion_if_frame, row=1, column=0))
        self.fields[NodeId.MION_AI].append(MonitorField(NodeId.MION_AI, 5, "HV-", mion_if_frame, row=2, column=0))
        # /
        # MION:Sensors
        self.fields[NodeId.MION_AI].append(MonitorField(NodeId.MION_AI, 0, "Humidity", mion_sensor_frame, row=0, column=0))
        self.fields[NodeId.MION_AI].append(MonitorField(NodeId.MION_AI, 1, "Temperature", mion_sensor_frame, row=1, column=0))
        self.fields[NodeId.MION_AI].append(MonitorField(NodeId.MION_AI, 2, "Pressure", mion_sensor_frame, row=2, column=0))
        # /
        # //

        # # Scenthound
        sh_mfc_frame = tk.LabelFrame(sh_frame, text="Mass flow controllers", bd=1)
        sh_mfc_frame.grid(row=0, column=0)
        # SH:Flows
        self.fields[NodeId.SH_MFC5_RGT].append(MfcField(NodeId.SH_MFC5_RGT, "Reagent flow", sh_mfc_frame, row=0, column=0))
        self.fields[NodeId.SH_MFC3_SMP].append(MfcField(NodeId.SH_MFC3_SMP, "Sample flow", sh_mfc_frame, row=1, column=0))
        self.fields[NodeId.SH_MFC2_EXH].append(MfcField(NodeId.SH_MFC2_EXH, "Exhaust flow", sh_mfc_frame, row=2, column=0))
        self.fields[NodeId.SH_MFC4_SHT1].append(MfcField(NodeId.SH_MFC4_SHT1, "Sheath 1 flow", sh_mfc_frame, row=3, column=0))
        self.fields[NodeId.SH_MFC1_SHT2].append(MfcField(NodeId.SH_MFC1_SHT2, "Sheath 2 flow", sh_mfc_frame, row=4, column=0))
        # /
        # //

        # # Calibrator
        self.fields[NodeId.CALIB_MFC].append(MfcField(NodeId.CALIB_MFC, "Carrier flow", cal_frame, row=0, column=0))
        # # //

        # # Flushplate
        self.fields[NodeId.FLSHP_MFC].append(MfcField(NodeId.FLSHP_MFC, "Counter flow", fp_frame, row=0, column=0))
        # # //

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()

    def style(self):
        self.title("KECU")
        # self.geometry('400x400')
        # self.configure(background='grey')

    def update_fields(self):
        global kecu
        for node, node_fields in self.fields.items():
            for field in node_fields:
                field.enable()
                if kecu and node in kecu.nodes:
                    field.enable()
                else:
                    field.disable()

    async def updater(self, interval):
        while True:
            self.update()
            await asyncio.sleep(interval)



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = []
    
    if len(sys.argv) > 1 and 'kecu' in sys.argv:
        kecu = KECU()
        loop.run_until_complete(initialize_kecu(kecu))
        # KECU main loop
        tasks.append( loop.create_task(kecu.run()) )
        if 'csv' in sys.argv:
            # KECU csv writer
            tasks.append( loop.create_task(kecu.writer()) )

    app = App(loop, kecu, tasks=tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        app.close()