# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 12:23:05 2019

@author: Oskari Kausiala
"""

import numpy as np

from .kospectra import KOSpectra

class KOEvent(KOSpectra):
    """
    KEvent equivalent for Orbitrap data
    """
    def __init__(self, filename, order='auto'):
        KOSpectra.__init__(self, filename)

        self.sampleid = self.raw.SampleInformation.SampleName
        if len(self.sampleid) == 0:
            self.sampleid = None

    def _t2scannum(self, t0=None, t1=None, dt=None):
        """ Get scan index for time window (s) """
        if t0 is None and t1 is None and dt is None:
            return None
        if t0 is not None:
            t0 /= 60. # Convert to minutes
            s0 = self.raw.ScanNumberFromRetentionTime(t0)
        if t1 is not None:
            t1 /= 60. # Convert to minutes
            s1 = self.raw.ScanNumberFromRetentionTime(t1)
        if dt is not None:
            dt /= 60. # Convert to minutes
            s1 = self.raw.ScanNumberFromRetentionTime(t0+dt)
        return (s0, s1)
    
    def get_spec(self, m0=None, m1=None, **kwargs):
        # Get a single spectrum from file
        # Keyword arguments t0, t1 and dt are allowed
        ind = self._t2scannum(**kwargs)
        return self.load_spec(ind, m0, m1)
    
    def get_spectra(self, m0=None, m1=None, **kwargs):
        # Get spectra from file
        # Arguments t0, t1 and dt are allowed
        ind = self._t2scannum(**kwargs)
        return self.load_spectra(ind, m0, m1)

    def get_avg_spectra(self, avg_s, m0=None, m1=None, **kwargs):
        avg_s = max(self.time_res, avg_s)
        if avg_s < self.t[-1]:
            t0 = kwargs.pop('t0', 0.0)
            t1 = kwargs.pop('t1', None)
            dt = kwargs.pop('dt', None)
            if t1 is None:
                if dt is not None:
                    t1 = min((t0 + dt), self.t[-1])
                else:
                    t1 = self.t[-1]
            mzs = []
            avg_spectra = []
            tnow = t0
            while tnow < t1:
                tleft = t1 - tnow
                dt = min(tleft, avg_s)
                mz, avg_spec = self.get_spec(m0=m0, m1=m1, t0=tnow, dt=dt)
                mzs.append(mz)
                avg_spectra.append(avg_spec)
                tnow += avg_s
        else:
            mzs, avg_spectra = self.get_spec(m0=m0, m1=m1)
        return mzs, avg_spectra

    def get_stickspec(self, m0=None, m1=None, **kwargs):
        # Get a single stick spectrum from file
        # Arguments t0, t1 and dt are allowed
        ind = self._t2scannum(**kwargs)
        return self.load_stickspec(ind, m0, m1)

    def get_stickspectra(self, m0=None, m1=None, **kwargs):
        # Get stick spectra from file
        # Arguments t0, t1 and dt are allowed
        ind = self._t2scannum(**kwargs)
        return self.load_stickspectra(ind, m0, m1)

    def get_avg_stickspectra(self, avg_s, m0=None, m1=None, **kwargs):
        avg_s = max(self.time_res, avg_s)
        t0 = kwargs.pop('t0', 0.0)
        t1 = kwargs.pop('t1', None)
        dt = kwargs.pop('dt', None)
        if t1 is None:
            if dt is not None:
                t1 = min((t0 + dt), self.t[-1])
            else:
                t1 = self.t[-1]
        mzs = []
        avg_stickss = []
        tnow = t0
        while tnow < t1:
            tleft = t1 - tnow
            dt = min(tleft, avg_s)
            mz, avg_sticks = self.get_stickspec(m0, m1, t0=tnow, dt=dt)
            mzs.append(mz)
            avg_stickss.append(avg_sticks)
            tnow += avg_s
        return mzs, avg_stickss