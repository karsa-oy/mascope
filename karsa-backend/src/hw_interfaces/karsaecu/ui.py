import asyncio
import tkinter as tk

# from .nodes import DEVICES


class App(tk.Tk):
    def __init__(self, loop, interval=.1):
        super().__init__()
        self.loop = loop
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.tasks = []
        self.tasks.append(loop.create_task(self.data_getter()))
        self.tasks.append(loop.create_task(self.updater(interval)))
        self.build()
        self.style()

    def build(self):
        
        class Field():
            def __init__(self, label, parent_frame, monitorable, settable, toggleable):
                self.frame = tk.Frame(parent_frame)
                self.label = tk.Label(self.frame, text=label).grid(row=0, column=0)
                if monitorable:
                    self.mon_value = tk.DoubleVar()
                    self.mon_entry = tk.Entry(self.frame, textvariable=self.mon_value, state='disabled')
                    self.mon_entry.grid(row=0, column=2)
                else:
                    self.mon_value = None
                if settable:
                    self.set_value = tk.DoubleVar()
                    self.set_entry = tk.Entry(self.frame, textvariable=self.set_value)
                    self.set_entry.grid(row=0, column=1)
                else:
                    self.set_value = None
                if toggleable:
                    self.cb_value = tk.BooleanVar()
                    self.checkbox = tk.Checkbutton(self.frame, variable=self.cb_value)
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

            def set(self, new_setpoint):
                if self.set_value is None:
                    raise ValueError("Cannot set non-settable Field")
                return self.set_value.set(new_setpoint)

            def toggle(self, new_state=None):
                if self.cb_value is None:
                    raise ValueError("Cannot toggle non-toggleable Field")
             
        class MfcField(Field):
            def __init__(self, label, parent_frame):
                super().__init__(label,
                                 parent_frame,
                                 monitorable=True,
                                 settable=True,
                                 toggleable=False
                                 )
        class ToggleField(Field):
            def __init__(self, label, parent_frame):
                super().__init__(label,
                                 parent_frame,
                                 monitorable=False,
                                 settable=False,
                                 toggleable=True
                                 )
        class VoltageField(Field):
            def __init__(self, label, parent_frame):
                super().__init__(label,
                                 parent_frame,
                                 monitorable=True,
                                 settable=True,
                                 toggleable=True
                                 )
        class ValueField(Field):
            def __init__(self, label, parent_frame):
                super().__init__(label,
                                 parent_frame,
                                 monitorable=True,
                                 settable=False,
                                 toggleable=False
                                 )
        class IndicatorField(ToggleField):
            def __init__(self, label, parent_frame):
                super().__init__(label, parent_frame)
                self.checkbox.configure(state=tk.DISABLED)

        # Main frame
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
        MfcField("Main flow", mion_common_frame).frame.grid(row=0, column=0)
        VoltageField("Accelerator voltage", mion_common_frame).frame.grid(row=1, column=0)
        # /
        # MION:IS1
        MfcField("Carrier flow", mion_is1_frame).frame.grid(row=0, column=0)
        MfcField("Exhaust flow", mion_is1_frame).frame.grid(row=1, column=0)
        VoltageField("Deflector voltage", mion_is1_frame).frame.grid(row=2, column=0)
        # /
        # MION:IS2
        MfcField("Carrier flow", mion_is2_frame).frame.grid(row=0, column=0)
        MfcField("Exhaust flow", mion_is2_frame).frame.grid(row=1, column=0)
        VoltageField("Deflector voltage", mion_is2_frame).frame.grid(row=2, column=0)
        # /
        # MION:X-ray
        ToggleField("Emission", mion_xray_frame).frame.grid(row=0, column=0)            
        IndicatorField("Enabled", mion_xray_frame).frame.grid(row=1, column=0)
        IndicatorField("Interlock", mion_xray_frame).frame.grid(row=2, column=0)    
        IndicatorField("Tube life", mion_xray_frame).frame.grid(row=3, column=0)    
        # /
        # MION:Ion filter
        ToggleField("Power", mion_if_frame).frame.grid(row=0, column=0)
        ValueField("HV+", mion_if_frame).frame.grid(row=1, column=0)
        ValueField("HV-", mion_if_frame).frame.grid(row=2, column=0)
        # /
        # MION:Sensors
        ValueField("Humidity", mion_sensor_frame).frame.grid(row=0, column=0)
        ValueField("Temperature", mion_sensor_frame).frame.grid(row=1, column=0)
        ValueField("Pressure", mion_sensor_frame).frame.grid(row=2, column=0)
        # /
        # //

        # # Scenthound
        sh_mfc_frame = tk.LabelFrame(sh_frame, text="Mass flow controllers", bd=1)
        
        sh_mfc_frame.grid(row=0, column=0)
        # SH:Flows
        MfcField("Reagent flow", sh_mfc_frame).frame.grid(row=0, column=0)
        MfcField("Sample flow", sh_mfc_frame).frame.grid(row=1, column=0)
        MfcField("Exhaust flow", sh_mfc_frame).frame.grid(row=2, column=0)
        MfcField("Sheath 1 flow", sh_mfc_frame).frame.grid(row=3, column=0)
        MfcField("Sheath 2 flow", sh_mfc_frame).frame.grid(row=4, column=0)
        # /
        # //

        # # Calibrator
        MfcField("Carrier flow", cal_frame).frame.grid(row=0, column=0)
        # # //

        # # Flushplate
        MfcField("Counter flow", fp_frame).frame.grid(row=0, column=0)
        # # //

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()

    async def data_getter(self):
        while True:
            await asyncio.sleep(1)
            # node_id, ntf, data = await kecu.wait_for_notification()

    def style(self):
        self.title("KECU")
        # self.geometry('400x400')
        self.configure(background='grey')

    async def updater(self, interval):
        while True:
            self.update()
            await asyncio.sleep(interval)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = App(loop)
    loop.run_forever()
    loop.close()