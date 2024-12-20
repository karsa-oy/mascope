# -*- coding: utf-8 -*-
"""Module providing interface to ThermoFischer Orbitrap data.

Created on Thu Feb 13 13:11:53 2020

@author: Oskari Kausiala
"""
import os
import sys
from pythonnet import load

load("coreclr")
import clr
import mascope_hardware

sys.path.append(os.path.join(mascope_hardware.__path__[0], "./orbitrap/lib/dlls/"))
clr.AddReference("ThermoFisher.CommonCore.Data")
clr.AddReference("ThermoFisher.CommonCore.RawFileReader")
