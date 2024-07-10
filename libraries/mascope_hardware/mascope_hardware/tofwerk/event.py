# -*- coding: utf-8 -*-
"""KEvent implements an API to Tofwerk h5 data files.

KEvent instance provides attributes and methods to load and visualize
data and its attributes. It utilizes Tofwerk API to access the raw data.

Created on Tue Apr  2 13:36:46 2019
"""

import h5py
import numpy as np
import pandas as pd

import mascope_runtime as runtime

from .spectra import KSpectra

logger = runtime.logger.service('hardware-lib')

class KEvent(KSpectra):
    """Class providing an API to read and visualize
    TOF data

    ...

    Attributes
    ----------
    sampleid : str
        User defined Sample ID for the data
    description : str
        User defined description of the sample
    """

    def __init__(self, filename):
        """Initialize self

        Retrieve TwH5Descriptor for the file, load time vectors,
        Sample ID and Sample description when available.

        Parameters
        ----------
        filename : str
            Data file name

        Raises
        ------
        ValueError
            If the given filename is not valid
        Exception
            If retrieving TwH5Descriptor fails
        """

        KSpectra.__init__(self, filename)

    def mz(self, si0=0, si1=None):
        """Calculate m/z axis for given range of TOF sample numbers

        With default parameters, complete m/z vector is returned.

        Parameters
        ----------
        si0 : int, optional
            First sample number of the desired range. The default is 0.
        si1 : int, optional
            Last sample number of the desired range. The default is None.

        Returns
        -------
        mz : array
            m/z vector of the requested sample number range
        """

        if si1 is None:
            si1 = self.desc.nbrSamples
        return np.asarray(self.sno2mz(range(si0, si1)))

    def get_spec(self, m0=None, m1=None, si0=0, si1=None, t0=None, t1=None, dt=None):
        """Get a single (averaged) spectrum from file

        Calculate average spectrum for a given mass/sample and/or time range.
        Use either m0 & m1 or si0 & si1 to specify the ranges.

        Parameters
        ----------
        m0 : int, optional
            Beginning of mass range. The default is None. If None,
            'si0' will be used instead.
        m1 : int, optional
            End of mass range. The default is None. If None,
            'si1' will be used instead.
        si0 : int, optional
            Beginning of sample number range. The default is 0.
        si1 : int, optional
            End of sample number range. The default is None.
        t0 : float, optional
            Start time of the desired time range. The default is None.
            If None, start time of the acquisition is used.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        spec : array
            Average spectrum for the requested ranges.
        """

        ind = self._t2bufind(t0, t1, dt)
        if m0 is not None:
            si0 = self.mz2sno(m0, True)
        if m1 is not None:
            si1 = self.mz2sno(m1, True)
        spec = self.load_spec(ind, si0, si1)
        spec[spec < 0] = 0
        return spec

    def get_spectra(self, m0=None, m1=None, si0=0, si1=None, t0=None, t1=None, dt=None):
        """Get multiple spectra from file

        Load non-averaged spectra for a given mass/sample and/or time range.
        Use either m0 & m1 or si0 & si1 to specify the ranges.

        Parameters
        ----------
        m0 : int, optional
            Beginning of mass range. The default is None.
        m1 : int, optional
            End of mass range. The default is None.
        si0 : int, optional
            Beginning of sample number range. The default is 0.
        si1 : int, optional
            End of sample number range. The default is None.
        t0 : float, optional
            Start time of the desired time range. The default is None.
            If None, start time of the acquisition is used.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        spectra : array
            Spectra for the requested ranges.
        """

        ind = self._t2bufind(t0, t1, dt)
        if m0 is not None:
            si0 = self.mz2sno(m0, True)
        if m1 is not None:
            si1 = self.mz2sno(m1, True)
        spectra = self.load_spectra(ind, si0, si1)
        spectra[spectra < 0] = 0
        return spectra

    def get_avg_spectra(
        self, avg_s, m0=None, m1=None, si0=0, si1=None, t0=0.0, t1=None, dt=None
    ):
        """Get averaged spectra from file

        Calculate averaged spectra for a given mass/sample and/or time range
        and averaging window. Use either m0 & m1 or si0 & si1 to specify the
        ranges.

        Parameters
        ----------
        avg_s : float
            Averaging window in seconds
        m0 : int, optional
            Beginning of mass range. The default is None.
        m1 : int, optional
            End of mass range. The default is None.
        si0 : int, optional
            Beginning of sample number range. The default is 0.
        si1 : int, optional
            End of sample number range. The default is None.
        t0 : float, optional
            Start time of the desired time range. The default is 0.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        avg_spectra : array
            Averaged spectra for the requested ranges.
        """

        if m0 is not None:
            si0 = self.mz2sno(m0, True)
        if m1 is not None:
            si1 = self.mz2sno(m1, True)

        if avg_s < self.t[-1]:
            if t1 is None:
                if dt is not None:
                    t1 = t0 + dt
                else:
                    t1 = self.t[-1]
            t1 = min(t1, self.t[-1])
            avg_spectra = []
            tnow = t0
            while tnow < t1:
                tleft = t1 - tnow
                dt = min(tleft, avg_s)
                avg_spectra.append(self.get_spec(si0, si1, t0=tnow, dt=dt))
                tnow += avg_s
        else:
            # Load sum spectrum
            avg_spectra = [self.get_spec(si0=si0, si1=si1)]

        return np.asarray(avg_spectra).T

    def get_stickspec(self, pi0=0, pi1=None, t0=None, t1=None, dt=None):
        """Get a single (averaged) unit mass resolution (UMR) spectrum from file

        Calculate average UMR spectrum for a given mass/sample and/or time range.

        Parameters
        ----------
        pi0 : int, optional
            Beginning of UM range (amu). The default is None.
        pi1 : int, optional
            End of UM range (amu). The default is 0.
        t0 : float, optional
            Start time of the desired time range. The default is None.
            If None, start time of the acquisition is used.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        stickspec : array
            Average UMR spectrum for the requested ranges.
        """

        ind = self._t2bufind(t0, t1, dt)
        return self.load_stickspec(ind, pi0, pi1)

    def get_stickspectra(self, pi0=0, pi1=None, t0=None, t1=None, dt=None):
        """Get multiple unit mass resolution (UMR) spectra from file

        Load non-averaged UMR spectra for a given mass/sample and/or time range.

        Parameters
        ----------
        pi0 : int, optional
            Beginning of UM range (amu). The default is 0.
        pi1 : int, optional
            End of UM range (amu). The default is None.
        t0 : float, optional
            Start time of the desired time range. The default is None.
            If None, start time of the acquisition is used.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        stickspectra : array
            UMR spectra for the requested ranges.
        """

        ind = self._t2bufind(t0, t1, dt)
        return self.load_stickspectra(ind, pi0, pi1)

    def get_avg_stickspectra(self, avg_s, pi0=0, pi1=None, t0=0.0, t1=None, dt=None):
        """Get averaged UMR spectra from file

        Calculate averaged UMR spectra for a given mass/sample and/or time range
        and averaging window.

        Parameters
        ----------
        avg_s : float
            Averaging window in seconds
        pi0 : int, optional
            Beginning of UM range (amu). The default is 0.
        pi1 : int, optional
            End of UM range (amu). The default is None.
        t0 : float, optional
            Start time of the desired time range. The default is 0.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        avg_spectra : array
            Averaged spectra for the requested ranges.
        """

        avg_s = max(self.time_res, avg_s)
        if t1 is None:
            if dt is not None:
                t1 = t0 + dt
            else:
                t1 = self.t[-1]
        t1 = min(t1, self.t[-1])
        avg_sticks = []
        tnow = t0
        while tnow < t1:
            tleft = t1 - tnow
            dt = min(tleft, avg_s)
            avg_sticks.append(self.get_stickspec(pi0, pi1, t0=tnow, dt=dt))
            tnow += avg_s
        return np.asarray(avg_sticks).T

    def get_tps_data(self, t0=None, t1=None, dt=None):
        """Load TPS parameter data from file

        Parameters
        ----------
        t0 : float, optional
            Start time of the desired time range. The default is None.
            If None, start time of the acquisition is used.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        data, info : array
            Returns TPS parameter data and parameter names
        """

        ind = self._t2bufind(t0, t1, dt)
        data, info = self.load_tps_data(ind)
        return data, info

    def get_avg_tps_data(self, avg_s, t0=0.0, t1=None, dt=None):
        """Load averaged TPS parameter data from file

        Parameters
        ----------
        avg_s : float
            averaging window in seconds
        t0 : float, optional
            Start time of the desired time range. The default is 0.
        t1 : float, optional
            End time of the desired range. The default is None.
            If None, end time of the acquisition is used.
        dt : float, optional
            Length of the desired range. The default is None.
            If not None, 't0' and 'dt' are used to define the range
            instead of 't0' and 't1'.

        Returns
        -------
        data, info : array
            Returns averaged TPS parameter data and parameter names
        """

        avg_s = max(self.time_res, avg_s)
        if t1 is None:
            if dt is not None:
                t1 = t0 + dt
            else:
                t1 = self.t[-1]
        t1 = min(t1, self.t[-1])
        data, info = self.get_tps_data(t0=t0, t1=t1)
        avg_data = []
        tnow = t0
        while tnow < t1:
            tleft = t1 - tnow
            dt = min(tleft, avg_s)
            i0, i1 = self._t2flatind(t0=tnow, dt=dt)
            data_t = data[:, i0:i1]
            avg_data.append(data_t.mean(axis=1))
            tnow += avg_s
        return np.asarray(avg_data).T, info

    def write_peaks(self, peaks):
        """Write peaks to file

        Write peak position and height to the h5 file, to datasets:
            '/Karsa/peaks/pos'
            '/Karsa/peaks/hei'

        Parameters
        ----------
        peaks : list
            List of 2-tuples with peak position (sample number) and height
        """

        ppos, phei = zip(*peaks)
        with h5py.File(self.filename, "r+") as h5f:
            dset = "Karsa/peaks"
            if dset in h5f:
                del h5f[dset]
            h5f[dset + "/pos"] = np.asarray(ppos)
            h5f[dset + "/hei"] = np.asarray(phei)

    def get_peaks(self):
        """Read peaks from file

        Try to read peaks from the file, return None if failed.

        Returns
        -------
        peaks : list or None
            List of 2-tuples with peak position and height. If
            reading from file failed, returns None.
        """

        try:
            with h5py.File(self.filename, "r") as h5f:
                posds = h5f["Karsa/peaks/pos"]
                heids = h5f["Karsa/peaks/hei"]
                ppos = posds[()]
                phei = heids[()]
                peaks = [(ppos[i], phei[i]) for i in range(len(ppos))]
        except BaseException:
            peaks = None
        return peaks

    def get_target_list(self):
        """Read target list DataFrame from file

        Returns
        -------
        target_list : DataFrame
            Returns target_list DataFrame, empty if reading failed

        """

        try:
            target_list = pd.read_hdf(self.filename, "/Karsa/target_list")
        except KeyError:
            logger.error("Target list not saved in file")
            target_list = pd.DataFrame()
        return target_list
