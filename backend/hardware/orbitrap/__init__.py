# -*- coding: utf-8 -*-
"""Module providing interface to ThermoFischer Orbitrap data.

Created on Thu Feb 13 13:11:53 2020

@author: Oskari Kausiala
"""
import os

import clr

package_dir = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(package_dir, "lib", "dlls")
dlls = ["ThermoFisher.CommonCore.Data.dll"]
for dll in dlls:
    reference = os.path.join(dll_path, dll)
    clr.AddReference(reference)
