# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 13:11:53 2020

@author: Oskari Kausiala
"""
import os
import clr

dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dlls")
libnames = ['ThermoFisher.CommonCore.Data.dll']
for lib in libnames:
    dll = os.path.join(dll_path, lib)
    clr.AddReference(dll)
    
from ThermoFisher.CommonCore.Data import Business