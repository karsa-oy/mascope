import asyncio
import sys
import tkinter as tk

from collections import defaultdict

from karsaecu.nodes import DEVICES, NODES, NodeId, NodeType
from services.KECUService import KECU


class Field():
    def __init__(self, label, parent_frame, monitorable, settable, toggleable, row=None, column=None):
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
            self.set_value_callbacks = [print]
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

    def on_checkbox_toggled(self):
        print("Checbox toggled, new state: %s" %self.cb_value.get())
        for callback in self.cb_value_callbacks:
            callback(self.cb_value.get())

    def on_setpoint_changed(self, event):
        # TODO: Possibly add validation here
        self.set(self.set_value.get())
        for callback in self.set_value_callbacks:
            callback(self.set_value.get())

    def reset_setpoint(self, event):
        self.set_value.set(self.prev_set_value)

    def set(self, new_setpoint):
        if self.set_value is None:
            raise ValueError("Cannot set non-settable Field")
        self.prev_set_value = self.set_value.get()
        return self.set_value.set(new_setpoint)

    def update_monitor(self, new_value):
        self.mon_value.set(new_value)

class MfcField(Field):
    def __init__(self, label, parent_frame, **kwargs):
        super().__init__(label,
                            parent_frame,
                            monitorable=True,
                            settable=True,
                            toggleable=False,
                            **kwargs
                            )
class DoField(Field):
    def __init__(self, label, parent_frame, **kwargs):
        super().__init__(label,
                            parent_frame,
                            monitorable=False,
                            settable=False,
                            toggleable=True,
                            **kwargs
                            )
class VoltageField(Field):
    def __init__(self, label, parent_frame, **kwargs):
        super().__init__(label,
                            parent_frame,
                            monitorable=True,
                            settable=True,
                            toggleable=True,
                            **kwargs
                            )
class MonitorField(Field):
    def __init__(self, label, parent_frame, **kwargs):
        super().__init__(label,
                            parent_frame,
                            monitorable=True,
                            settable=False,
                            toggleable=False,
                            **kwargs
                            )
class DiField(DoField):
    def __init__(self, label, parent_frame, **kwargs):
        super().__init__(label, parent_frame, **kwargs)
        self.checkbox.configure(state=tk.DISABLED)



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

    def build(self):
        global kecu
        # Main frame components
        mion_frame = tk.LabelFrame(text="MION", bd=1)
        sh_frame = tk.LabelFrame(text="Scenthound", bd=1)
        cal_frame = tk.LabelFrame(text="Calibrator", bd=1)
        fp_frame = tk.LabelFrame(text="Flushplate", bd=1)
        # Grid 'em
        mion_frame.grid(row=0, column=0)
        sh_frame.grid(row=1, column=0)
        cal_frame.grid(row=2, column=0)
        fp_frame.grid(row=3, column=0)

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
        self.fields[NodeId.MION_MFC5_MAIN] = MfcField("Main flow", mion_common_frame, row=0, column=0)
        VoltageField("Accelerator voltage", mion_common_frame, row=1, column=0)
        # /
        # MION:IS1
        self.fields[NodeId.MION_MFC2_SRC1_CRR] = MfcField("Carrier flow", mion_is1_frame, row=0, column=0)
        self.fields[NodeId.MION_MFC1_SRC1_EXH] = MfcField("Exhaust flow", mion_is1_frame, row=1, column=0)
        VoltageField("Deflector voltage", mion_is1_frame, row=2, column=0)
        # /
        # MION:IS2
        self.fields[NodeId.MION_MFC4_SRC2_CRR] = MfcField("Carrier flow", mion_is2_frame, row=0, column=0)

        field = MfcField("Exhaust flow", mion_is2_frame, row=1, column=0)
        self.fields[NodeId.MION_MFC3_SRC2_EXH] = field
        node = kecu.nodes.get(NodeId.MION_MFC3_SRC2_EXH, None)
        if node:
            device = node._device
            print("Device: %s Channels: %s" %(device, device.channels))
            device.channels[(0x2F00, 0x01)].callbacks.append(field.set)
            device.channels[(0x2C00, 0x01)].callbacks.append(field.update_monitor)
            field.set_value_callbacks.append(device.set_flow)
        VoltageField("Deflector voltage", mion_is2_frame, row=2, column=0)
        # /
        # MION:X-ray
        self.fields[NodeId.MION_DIO].append(
            DoField("Emission", mion_xray_frame, row=0, column=0)
            )
        self.fields[NodeId.MION_DIO].append(
            DiField("Enabled", mion_xray_frame, row=1, column=0)
            )
        self.fields[NodeId.MION_DIO].append(
            DiField("Interlock", mion_xray_frame, row=2, column=0)
            )
        self.fields[NodeId.MION_DIO].append(
            DiField("Tube life", mion_xray_frame, row=3, column=0)
        )
        # /
        # MION:Ion filter
        DoField("Power", mion_if_frame, row=0, column=0)
        MonitorField("HV+", mion_if_frame, row=1, column=0)
        MonitorField("HV-", mion_if_frame, row=2, column=0)
        # /
        # MION:Sensors
        self.fields[NodeId.MION_AI].append(
            MonitorField("Humidity", mion_sensor_frame, row=0, column=0)
            )
        self.fields[NodeId.MION_AI].append(
            MonitorField("Temperature", mion_sensor_frame, row=1, column=0)
            )
        self.fields[NodeId.MION_AI].append(
            MonitorField("Pressure", mion_sensor_frame, row=2, column=0)
            )
        # /
        # //

        # # Scenthound
        sh_mfc_frame = tk.LabelFrame(sh_frame, text="Mass flow controllers", bd=1)
        
        sh_mfc_frame.grid(row=0, column=0)
        # SH:Flows
        self.fields[NodeId.SH_MFC5_RGT] = MfcField("Reagent flow", sh_mfc_frame, row=0, column=0)
        self.fields[NodeId.SH_MFC3_SMP] = MfcField("Sample flow", sh_mfc_frame, row=1, column=0)
        self.fields[NodeId.SH_MFC2_EXH] = MfcField("Exhaust flow", sh_mfc_frame, row=2, column=0)
        self.fields[NodeId.SH_MFC4_SHT1] = MfcField("Sheath 1 flow", sh_mfc_frame, row=3, column=0)
        self.fields[NodeId.SH_MFC1_SHT2] = MfcField("Sheath 2 flow", sh_mfc_frame, row=4, column=0)
        # /
        # //

        # # Calibrator
        self.fields[NodeId.CALIB_MFC] = MfcField("Carrier flow", cal_frame, row=0, column=0)
        # # //

        # # Flushplate
        self.fields[NodeId.FLSHP_MFC] = MfcField("Counter flow", fp_frame, row=0, column=0)
        # # //

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()

    def style(self):
        self.title("KECU")
        # self.geometry('400x400')
        self.configure(background='grey')

    async def updater(self, interval):
        while True:
            self.update()
            await asyncio.sleep(interval)


kecu = KECU()

async def initialize_kecu():
    global kecu
    await kecu.connect()
    await kecu.initialize()
    for node_id, node in kecu._app._node_dict.items():
        if node._device.node_type == NodeType.MFC:
            await node.start_measurement(index=0x2F00, subindex=0x01, interval=100)
            await node.start_measurement(index=0x2C00, subindex=0x01, interval=100)
        # else:
        #     resp = await node.start_measurement(interval=100)


async def measure():
    global kecu
    try:
        while True:
            print('.')
            node_id, ntf, data = await kecu.wait_for_notification()
            print('..')
            try:
                # Notify app
                ntf_handler = getattr(kecu._app, 'on_{}'.format(ntf.name))
                # print("Notify app")
                await ntf_handler(node_id)
            except AttributeError:
                pass
            try:
                # Notify node
                print('on_{}({})'.format(ntf.name, data))
                ntf_handler = getattr(kecu.nodes[node_id], 'on_{}'.format(ntf.name))
                print("Notify node")
                await ntf_handler(data)
                print("Notified")
            except Exception as e:
                print(e)
    except asyncio.CancelledError:
        print("measure task cancelled")
        await kecu.disconnect()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = []
    if len(sys.argv) > 1 and sys.argv[1] == 'kecu':
        loop.run_until_complete(initialize_kecu())
        tasks.append( loop.create_task(measure()) )
    app = App(loop, kecu, tasks=tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        app.close()