# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 12:23:05 2019

@author: Oskari Kausiala
"""

from ThermoFisher.CommonCore.Data import Business

class KOInstrument():
    """
    KInstrument equivalent for Orbitrap
    """    
    def __init__(self, rawfile):
        try:
            self.raw = Business.RawFileReaderFactory.ReadFile(rawfile)
            self.raw.SelectInstrument(0, 1)
            self.filename = rawfile
        except:
            self.raw = None
            raise Exception(rawfile + ' does not appear to be a valid .raw file.'
                                      'Please check path and file and try again.')

    def __del__(self):
        if self.raw is not None:
            try:
                self.raw.Dispose()
            except:
                pass
            