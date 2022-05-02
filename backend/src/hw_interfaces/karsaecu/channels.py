from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Channel:
    """Channel base class

    Channel represents an input or an output of a device.
    
    Channels may specify a (unit) conversion to translate raw
    data into more readable quantity.
    
    Some channels take the CAN address index and subindex as 
    initialization parameters.
    """
    description: str
    callbacks: 'list[Callable]' = field(default_factory=list, init=False)
    value: float = field(default=None, init=False)
    _value: float = field(init=False, repr=False)

    # def __post_init__(self):
    #     self.callbacks.append(print)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        for callback in self.callbacks:
            callback(self.value)

@dataclass
class AiChannel(Channel):
    unit: str = ""
    conversion: Callable[[float], float] = lambda x : x

    voltage: float = field(default=None, init=False)
    _voltage: float = field(init=False, repr=False)

    @property
    def voltage(self) -> float:
        return self._voltage

    @voltage.setter
    def voltage(self, voltage: float):
        self._voltage = voltage
        if not isinstance(voltage, property):
            self.value = self.conversion(voltage)

@dataclass
class DioChannel(Channel):
    io: bool = None
    active_low: bool = field(default=False)

    state: float = field(default=None, init=False)
    _state: float = field(init=False, repr=False)

    @property
    def state(self) -> bool:
        return self._state

    @state.setter
    def state(self, state: bool) -> bool:
        self._state = state
        if not isinstance(state, property):
            self.value = (state != self.active_low)

@dataclass
class MfcChannel(Channel):
    index: int = None
    subindex: int = None
    settable: bool = None
    unit: str = ""

@dataclass
class ValveChannel(Channel):
    index: int = None
    subindex: int = None
    settable: bool = None

@dataclass
class HvChannel(Channel):
    index: int = None
    subindex: int = None
    settable: bool = None
    unit: str = ""

    voltage: float = field(default=None, init=False)
    _voltage: float = field(init=False, repr=False)
    scaling_factor: float = field(default=None, init=False)

    @property
    def voltage(self) -> float:
        return self._voltage

    @voltage.setter
    def voltage(self, voltage: float):
        self._voltage = voltage
        if not isinstance(voltage, property):
            if self.scaling_factor:
                self.value = voltage * self.scaling_factor

# AI
def MION_AI_CHANNELS(): 
    MION_AI_CHANNEL_CFG = [
        AiChannel("RH", unit="%", conversion=lambda x: 100.0*x),
        AiChannel("T", unit="C", conversion=lambda x: 100.0*x-40.0),
        AiChannel("P", unit="bar", conversion=lambda x: 0.4*x),
        AiChannel("N/C", unit="", conversion=lambda x: x),
        AiChannel("Ion filter", unit="V", conversion=lambda x: 101.0*x+0.0),
        AiChannel("Ion filter", unit="V", conversion=lambda x: 101.0*x+0.0)
    ]
    return {
        i: ch
        for i, ch in enumerate(MION_AI_CHANNEL_CFG)
    }

def SH_AI_CHANNELS():
    SH_AI_CHANNEL_CFG = [
        AiChannel("", unit="", conversion=lambda x: x),
        AiChannel("", unit="", conversion=lambda x: x),
        AiChannel("", unit="", conversion=lambda x: x),
        AiChannel("", unit="", conversion=lambda x: x),
        AiChannel("", unit="", conversion=lambda x: x),
        AiChannel("", unit="", conversion=lambda x: x)
    ]
    return {
        i: ch
        for i, ch in enumerate(SH_AI_CHANNEL_CFG)
    }

def MION2_AI_CHANNELS():
    MION2_AI_CHANNEL_CFG = [
        AiChannel("RH", unit="%", conversion=lambda x: 100.0*x),
        AiChannel("T", unit="C", conversion=lambda x: 100.0*x-40.0),
        AiChannel("P", unit="bar", conversion=lambda x: 0.4*x),
        AiChannel("N/C", unit="", conversion=lambda x: x),
        AiChannel("Ion filter", unit="V", conversion=lambda x: 101.0*x+0.0),
        AiChannel("Ion filter", unit="V", conversion=lambda x: 101.0*x+0.0)
    ]
    return {
        i: ch
        for i, ch in enumerate(MION2_AI_CHANNEL_CFG)
    }
# //

# DIO
def MION_DIO_CHANNELS():
    MION_DIO_CHANNEL_CFG = [
        DioChannel("X-ray alert", io=1),
        DioChannel("X-ray enabled", io=1),
        DioChannel("X-ray interlock", io=1),
        DioChannel("X-ray active", io=1),
        DioChannel("X-ray toggle", io=0),
        DioChannel("Ion filter toggle", io=0),
        DioChannel("N/C", io=0),
        DioChannel("N/C", io=0),
    ]
    return {
        i: ch
        for i, ch in enumerate(MION_DIO_CHANNEL_CFG)
    }

def SH_DIO_CHANNELS():
    SH_DIO_CHANNEL_CFG = [
        DioChannel("", io=1),
        DioChannel("", io=1),
        DioChannel("", io=1),
        DioChannel("", io=1),
        DioChannel("", io=0),
        DioChannel("", io=0),
        DioChannel("", io=0),
        DioChannel("", io=0),
    ]
    return {
        i: ch
        for i, ch in enumerate(SH_DIO_CHANNEL_CFG)
    }

def MION1v5_DIO_CHANNELS():
    MION1v5_DIO_CHANNEL_CFG = [
        DioChannel("X-ray alert", io=1),
        DioChannel("X-ray enabled", io=1),
        DioChannel("X-ray 2 active", io=1, active_low=True),
        DioChannel("X-ray 1 active", io=1, active_low=True),
        DioChannel("X-ray 1 toggle", io=0),
        DioChannel("Ion filter toggle", io=0),
        DioChannel("N/C", io=0),
        DioChannel("X-ray 2 toggle", io=0),
    ]
    return {
        i: ch 
        for i, ch in enumerate(MION1v5_DIO_CHANNEL_CFG)
    }

def MION2_DIO_XRAY_ON_CHANNELS(): return {}
def MION2_DIO_XRAY_ALERT_CHANNELS(): return {}
def MION2_DIO_XRAY_CTRL_CHANNELS(): return {}
#//

# MFC
def MFC_CHANNELS():
    MFC_CHANNEL_CFG = [
        MfcChannel(
            "Flow setpoint",
            index=0x2F00,
            subindex=0x01,
            settable=True
            ),
        MfcChannel(
            "Flow monitor value",
            index=0x2C00,
            subindex=0x01,
            settable=False
            ),
        MfcChannel(
            "Medium temperature",
            index=0x2503,
            subindex=0x01,
            settable=False,
            unit="C"
            ),
        MfcChannel(
            "Device status, temperature",
            index=0x2004,
            subindex=0x02,
            settable=False,
            unit="C"
            ),
        MfcChannel(
            "Device status, voltage",
            index=0x2004,
            subindex=0x03,
            settable=False,
            unit="V"
            ),
    ]
    return {
        (ch.index, ch.subindex): ch
        for ch in MFC_CHANNEL_CFG
    }
# //

# Valve
def VALVE_CHANNELS():
    VALVE_CHANNEL_CFG = [
        ValveChannel(
            "Valve output",
            index=0x2500,
            subindex=0x01,
            settable=False
            ),
        ValveChannel(
            "Current",
            index=0x2501,
            subindex=0x01,
            settable=False
            ),
        ValveChannel(
            "Valve input",
            index=0x2540,
            subindex=0x01,
            settable=True
            ),
    ]
    return {
        (ch.index, ch.subindex): ch
        for ch in VALVE_CHANNEL_CFG
    }
# //

# High-voltage
def HV_CHANNELS():
    HV_CHANNEL_CFG = [
        [
        HvChannel(
            "Voltage reading scale factor",
            index=0x2000,
            subindex=i,
            settable=True,
            unit="mV"
            ),
        HvChannel(
            "Current reading scale factor",
            index=0x2001,
            subindex=i,
            settable=True,
            unit="nA"
            ),
        HvChannel(
            "Max voltage",
            index=0x2002,
            subindex=i,
            settable=True,
            unit="V"
            ),
        HvChannel(
            "Max current",
            index=0x2003,
            subindex=i,
            settable=True,
            unit="uA"
            ),
        HvChannel(
            "Voltage monitor value",
            index=0x7130,
            subindex=i,
            settable=False,
            unit="V"
            ),
        HvChannel(
            "Current monitor value",
            index=0x7131,
            subindex=i,
            settable=False
            ),
        HvChannel(
            "Voltage setpoint",
            index=0x7300,
            subindex=i,
            settable=True,
            unit="V"
            ),
        ]
        for i in range(1, 4) # 3 HV modules
    ]
    return {
        (ch.index, ch.subindex): ch
        for chs in HV_CHANNEL_CFG
        for ch in chs
    }
# //