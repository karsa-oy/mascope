# -*- coding: utf-8 -*-
"""Module providing interface to TofWerk TOF data, as well as
algorithms to process it.

Created on Wed Jun 20 10:07:53 2018
"""
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from .lib.TwTool import *