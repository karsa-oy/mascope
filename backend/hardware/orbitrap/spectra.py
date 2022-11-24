# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 12:09:29 2019

@author: Oskari Kausiala
"""

import numpy as np

from datetime import datetime, timedelta

from ThermoFisher.CommonCore.Data import Business

from backend.hardware.lib.util import net2np_array
from .instrument import KOInstrument


class KOSpectra(KOInstrument):
    """
    KSpectra equivalent for Orbitrap
    """
    def __init__(self, rawfile):
        KOInstrument.__init__(self, rawfile)

        # Get timing data
        scans = range( self.raw.RunHeaderEx.FirstSpectrum,
                        self.raw.RunHeaderEx.LastSpectrum + 1 )
        t = [ 60.*self.raw.RetentionTimeFromScanNumber(s) for s in scans ]

        # Get datetime
        sysdt = self.raw.CreationDate
        dt0 = datetime(sysdt.Year,
                        sysdt.Month,
                        sysdt.Day,
                        sysdt.Hour,
                        sysdt.Minute,
                        sysdt.Second,
                        sysdt.Millisecond)
        dt = np.asarray([dt0 + timedelta(seconds=ti)
                          for ti in t])
        dt1 = dt0 + timedelta(seconds=t[-1])
        self.t = np.array(t)
        self.dt = dt
        self.dt0 = dt0
        self.dt1 = dt1
        self.length = t[-1]
        self.scans = scans
        self.time_res = np.diff(t).mean()
        #self.polarity = None

        self.scan_avgr = Business.ScanAveragerFactory.GetScanAverager(self.raw)
    
    def load_spec(self, ind=None, m0=None, m1=None, scan_filter=''):
        if ind is None:
            ind = (self.scans[0], self.scans[-1])
        avg_scan = self.scan_avgr.GetAverageScanInScanRange(ind[0], ind[1], scan_filter)
        mz = net2np_array(avg_scan.SegmentedScan.Positions)
        spec = net2np_array(avg_scan.SegmentedScan.Intensities)
        if m0 is not None or m1 is not None:
            if m0 is None:
                m0 = 0
            if m1 is None:
                m1 = np.inf
            mind = np.logical_and(mz >= m0, mz <= m1)
            mz = mz[mind]
            spec = spec[mind]
        return mz, spec
    
    def load_spectra(self, ind=None, m0=None, m1=None, scan_filter=''):
        if ind is None:
            ind = (self.scans[0], self.scans[-1])
        mzs = []
        specs = []
        for scan in range(ind[0], ind[1]+1):
            segscan = self.raw.GetSegmentedScanFromScanNumber(scan, None)
            mz = net2np_array(segscan.Positions)
            spec = net2np_array(segscan.Intensities)
            if m0 is not None or m1 is not None:
                if m0 is None:
                    m0 = 0
                if m1 is None:
                    m1 = np.inf
                mind = np.logical_and(mz >= m0, mz <= m1)
                mz = mz[mind]
                spec = spec[mind]
            mzs.append(mz)
            specs.append(spec)
        return mzs, specs
    
    def load_stickspec(self, ind=None, m0=None, m1=None, scan_filter=''):
        if ind is None:
            ind = (self.scans[0], self.scans[-1])
        avg_scan = self.scan_avgr.GetAverageScanInScanRange(ind[0], ind[1], scan_filter)
        if avg_scan.CentroidScan.Length == 0:
            raise Exception("No centroid spectrum available.")
        mz = net2np_array(avg_scan.CentroidScan.Masses)
        sticks = net2np_array(avg_scan.CentroidScan.Intensities)
        if m0 is not None or m1 is not None:
            if m0 is None:
                m0 = 0
            if m1 is None:
                m1 = np.inf
            mind = np.logical_and(mz >= m0, mz <= m1)
            mz = mz[mind]
            sticks = sticks[mind]
        return mz, sticks
    
    def load_stickspectra(self, ind=None, m0=None, m1=None, scan_filter=''):
        if ind is None:
            ind = (self.scans[0], self.scans[-1])
        mzs = []
        stickss = []
        for scan in range(ind[0], ind[1]+1):
            cent = self.raw.GetCentroidStream(scan, None)
            masses = net2np_array(cent.Masses)
            sticks = net2np_array(cent.Intensities)
            if m0 is not None or m1 is not None:
                if m0 is None:
                    m0 = 0
                if m1 is None:
                    m1 = np.inf
                mind = np.logical_and(masses >= m0, masses <= m1)
                masses = masses[mind]
                sticks = sticks[mind]
            mzs.append(masses)
            stickss.append(sticks)
        return mzs, stickss