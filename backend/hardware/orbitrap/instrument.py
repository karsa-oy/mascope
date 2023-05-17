# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 12:23:05 2019

@author: Oskari Kausiala
"""

from ThermoFisher.CommonCore.Data import Business


class KOInstrument:
    """
    KInstrument equivalent for Orbitrap
    """

    def __init__(self, rawfile):
        try:
            self.raw = Business.RawFileReaderFactory.ReadFile(rawfile)
            # TODO: DEVICE.MS is supposed to be at 0; is it always the case?
            i_type = self.raw.GetInstrumentType(0)
            self.raw.SelectInstrument(i_type, 1)
            i_data = self.raw.GetInstrumentData()
            print(f"File: {rawfile}\nInstrument: {i_data.Name} #{i_data.SerialNumber}")
            self.filename = rawfile
        except:
            self.raw = None
            raise Exception(
                rawfile + " does not appear to be a valid .raw file."
                "Please check path and file and try again."
            )

    def __del__(self):
        if self.raw is not None:
            try:
                self.raw.Dispose()
            except:
                pass
