# -*- coding: utf-8 -*-
"""
Created on Tue Apr  2 13:27:15 2019

@author: Karsa
"""

from ctypes import create_string_buffer
from datetime import datetime, timedelta
from ntpath import basename
from os import path

import h5py
import numpy as np
import scipy.sparse as sparse

import mascope_runtime as runtime

from .instrument import KInstrument
from .lib.TofDaq import TwRetVal
from .lib.TwH5 import (
    TwCloseH5,
    TwGetH5Descriptor,
    TwGetPeakData,
    TwGetRegUserDataFromH5,
    TwGetStickSpectrumFromH5,
    TwGetSumSpectrumFromH5,
    TwGetTofData,
    TwGetTofSpectrumFromH5,
    TwH5Desc,
)
from .util import filetime2datetime

logger = runtime.logger.service('hardware-lib')


class KSpectra(KInstrument):
    """Class to provide an API for loading data from Tofwerk H5 files.

    KSpectra is a middle layer in the data access API, and the user should
    use KEvent class instead, for simpler API.

    Attributes
    ----------
    filename : str
        Full file path
    polarity : str
        'negative' or 'positive'
    t : array
        Time vector of all data points
    dt0 : datetime
        Start datetime of the sample (UTC)
    dt1 : datetime
        End datetime of the sample (UTC)
    dt : array
        Datetime vector of all data points (UTC)
    dt0_loc : datetime
        Start datetime of the sample (local time)
    dt1_loc : datetime
        End datetime of the sample (local time)
    dt_loc : array
        Datetime vector of all data points (local time)
    length : float
        Data file length in seconds

    """

    def __init__(self, filename):
        """Initialize self

        Parameters
        ----------
        desc : TwH5Desc
            Tofwerk H5 descriptor
        filename : str
            Full file path
        """

        if not path.isfile(filename):
            raise ValueError(
                "Input argument 'filename' (%s) is not a valid data file." % filename
            )
        desc = TwH5Desc()
        ret = TwGetH5Descriptor(filename.encode(), desc)
        if ret != 4:
            raise Exception(
                "Trying to fetch descriptor for file %s " % filename
                + "failed: %s" % TwRetVal(ret).name
            )

        KInstrument.__init__(self, desc)

        with h5py.File(filename, "r") as h5f:
            polarity = h5f.attrs["IonMode"]
            dt0 = filetime2datetime(h5f["TimingData"].attrs["AcquisitionTimeZero"][0])
            bt = h5f["TimingData/BufTimes"]
            t = bt[()].reshape((-1,))
        ncomplete = desc.nbrWrites * desc.nbrBufs
        t = t[:ncomplete]
        dts = t[-1]
        dt1 = dt0 + timedelta(seconds=dts)

        # Try to parse local time from filename
        try:
            pattern = "%Y.%m.%d_%Hh%Mm%Ss"
            datestr = basename(filename)
            datestr = path.splitext(datestr)[0]
            datestr = "_".join(datestr.split("_")[1:])
            dt0_loc = datetime.strptime(datestr, pattern)
            dt0_loc += timedelta(microseconds=dt0.microsecond)
            dt1_loc = dt0_loc + timedelta(seconds=dts)
            self.dt0_loc = dt0_loc  # start datetime local
            self.dt1_loc = dt1_loc  # end timezone local
            # local datetime of datapoints
            self.dt_loc = np.asarray([dt0_loc + timedelta(seconds=ti) for ti in t])
        except Exception as e:
            logger.error("Parsing local time from filename failed: %s" % e)
            dt0_loc = dt1_loc = None

        self.filename = filename
        self.polarity = str(polarity)
        self.t = t  # time elapsed
        self.dt0 = dt0  # start datetime UTC
        self.dt1 = dt1  # end datetime UTC
        self.dt = np.asarray(
            [dt0 + timedelta(seconds=ti) for ti in t]
        )  # UTC datetime of datapoints
        self.length = (dt1 - dt0).total_seconds()

    def __del__(self):
        """Close the file on delete"""

        try:
            TwCloseH5(self.filename.encode())
        except:
            pass

    def _t2flatind(self, t0=None, t1=None, dt=None):
        """Convert time range into flat indices

        Start time (t0) and either end time (t1) or length (dt) are
        required to specify the time range for which to calculate the
        index range.

        Parameters
        ----------
        t0 : float, optional
            Start time of the desired range. The default is None.
        t1 : float, optional
            End time of the desired range. The default is None.
        dt : float, optional
            Length of the desired range. The default is None.

        Returns
        -------
        ind : tuple
            2-Tuple with the range: (start_index, end_index)
        """

        ind = None
        if t0 is not None:
            t0ind = np.argmin(np.abs(self.t - t0))
            ind = (t0ind, t0ind)
        if t1 is not None:
            t1ind = np.argmin(np.abs(self.t - t1))
            ind = (t0ind, t1ind)
        if dt is not None:
            t1ind = np.argmin(np.abs(self.t - (t0 + dt)))
            ind = (t0ind, t1ind)
        return ind

    def _t2bufind(self, t0=None, t1=None, dt=None):
        """Convert time range into Buf/Write indices

        Refer to Tofwerk documentation about the indexing

        Parameters
        ----------
        t0 : float, optional
            Start time of the desired range. The default is None.
        t1 : float, optional
            End time of the desired range. The default is None.
        dt : float, optional
            Length of the desired range. The default is None.

        Returns
        -------
        ind : tuple
            4-Tuple with the range: (buf0, buf1, write0, write1)
        """

        # Convert times (in seconds elapsed) to Buf and Write index
        ind = None
        datashape = (self.desc.nbrWrites, self.desc.nbrBufs)
        if t0 is not None:
            flatind = np.argmin(np.abs(self.t - t0))
            wi0, bi0 = np.unravel_index(flatind, datashape)
            wi1 = wi0
            bi1 = bi0
            ind = (bi0, bi1, wi0, wi1)
        if t1 is not None:
            flatind = np.argmin(np.abs(self.t - t1))
            wi1, bi1 = np.unravel_index(flatind, datashape)
            ind = (bi0, bi1, wi0, wi1)
        if dt is not None:
            flatind = np.argmin(np.abs(self.t - (t0 + dt)))
            wi1, bi1 = np.unravel_index(flatind, datashape)
            ind = (bi0, bi1, wi0, wi1)
        return ind

    def load_spec(self, ind=None, si0=0, si1=None):
        """Load a single (averaged over a time range) mass spectrum,
        in signal intensity unit mV/ext.

        Parameters
        ----------
        ind : tuple, optional
            4-tuple with the range: (buf0, buf1, write0, write1),
            by default None. If None, full time range will be used.
        si0 : int, optional
            First sample number of the desired range. The default is 0.
        si1 : int, optional
            Last sample number of the desired range. The default is None.
            If None, si1=nbrSamples.

        Raises
        ------
        Exception
            If loading data fails

        Returns
        -------
        array
            Averaged spectrum [mV/ext]
        """

        if ind is None:
            # Full time range -> load sum spectrum
            spec = np.zeros((self.desc.nbrSamples,), dtype=np.double)
            ret = TwGetSumSpectrumFromH5(self.filename.encode(), spec, True)
        else:
            # Load average spectrum in a certain time range
            bi0, bi1, wi0, wi1 = ind
            spec = np.zeros((self.desc.nbrSamples,), dtype=np.float32)
            ret = TwGetTofSpectrumFromH5(
                self.filename.encode(), spec, 0, 0, bi0, bi1, wi0, wi1, True, True
            )
        if ret != 4:
            raise Exception("Loading spectrum failed with code %s" % TwRetVal(ret).name)
        # Take specified sample number range
        if si1 is None:
            si1 = self.desc.nbrSamples
        spec = spec[si0 : (si1 + 1)]
        return spec  # mV/ext

    def load_spectra(self, ind=None, si0=0, si1=None):
        """Load multiple mass spectra in a specified time range,
        in signal intensity unit mV/ext.

        Parameters
        ----------
        ind : tuple, optional
            4-tuple with the range: (buf0, buf1, write0, write1),
            by default None. If None, full time range will be used.
        si0 : int, optional
            First sample number of the desired range. The default is 0.
        si1 : int, optional
            Last sample number of the desired range. The default is None.
            If None, si1=nbrSamples.

        Raises
        ------
        Exception
            If loading data fails

        Returns
        -------
        array
            Spectra [mV/ext]
        """

        if si1 is None:
            si1 = self.desc.nbrSamples
        nsmpl = si1 - si0
        nbuf = self.desc.nbrBufs
        if ind is not None:
            bi0, bi1, wi0, wi1 = ind
            nwrite = wi1 - wi0
            if nwrite == 0:
                nbuf = bi1 - bi0 + 1
            nwrite += 1
        else:
            wi0 = 0
            bi0 = 0
            nwrite = self.desc.nbrWrites
        data_shape = (nwrite, nbuf, nsmpl)
        signal = np.zeros(data_shape, dtype="float32")
        ret = TwGetTofData(
            self.filename.encode(), si0, nsmpl, 0, 1, 0, nbuf, wi0, nwrite, signal
        )
        if ret != 4:
            raise Exception("Loading spectra failed with code %s" % TwRetVal(ret).name)
        # Rearrange dimensions
        signal.shape = (-1, nsmpl)
        signal = np.transpose(signal)
        # Remove empty spectra in case of incomplete writes
        signal = signal[:, : len(self.t)]
        return signal

    def load_stickspec(self, ind=None, pi0=0, pi1=None):
        """Load a single (averaged over a time range) unit mass resolution
        mass spectrum, in signal intensity unit mV/ext.

        Parameters
        ----------
        ind : tuple, optional
            4-tuple with the range: (buf0, buf1, write0, write1),
            by default None. If None, full time range will be used.
        pi0 : int, optional
            First unit mass to include, by default 0
        pi1 : int, optional
            Last unit mass to include, by default None. If None,
            pi1=nbrPeaks.

        Raises
        ------
        Exception
            If loading data fails

        Returns
        -------
        array
            Averaged UMR spectrum ("stick spectrum") [mV/ext]. Array
            indices correspond to unit masses if pi0=0.
        """

        stickspec = np.zeros((self.desc.nbrPeaks + 1,), dtype=np.float32)
        if ind is None:
            bi0 = 0
            bi1 = self.desc.nbrBufs - 1
            wi0 = 0
            wi1 = self.desc.nbrWrites - 1
        else:
            bi0, bi1, wi0, wi1 = ind
        ret = TwGetStickSpectrumFromH5(
            self.filename.encode(), stickspec, 0, 0, bi0, bi1, wi0, wi1, True, True
        )
        if ret != 4:
            raise Exception(
                "Loading UMR spectrum failed with code %s" % TwRetVal(ret).name
            )
        # Move indices by one so that index==amu
        stickspec = np.roll(stickspec, 1)
        if pi1 is None:
            pi1 = self.desc.nbrPeaks
        stickspec = stickspec[pi0 : (pi1 + 1)]
        return stickspec  # mV/ext

    def load_stickspectra(self, ind=None, pi0=0, pi1=None):
        """Load multiple unit mass resolution  mass spectra in a specified
        time range, in signal intensity unit mV/ext.

        Parameters
        ----------
        ind : tuple, optional
            4-tuple with the range: (buf0, buf1, write0, write1),
            by default None. If None, full time range will be used.
        pi0 : int, optional
            First unit mass to include, by default 0
        pi1 : int, optional
            Last unit mass to include, by default None. If None,
            pi1=nbrPeaks.

        Raises
        ------
        Exception
            If loading data fails

        Returns
        -------
        array
            UMR spectra ("stick spectra") [mV/ext]. Array row
            indices correspond to unit masses if pi0=0.
        """

        if pi1 is None:
            pi1 = self.desc.nbrPeaks - 1

        nsticks = pi1 - pi0 + 1

        nbuf = self.desc.nbrBufs
        if ind is not None:
            bi0, bi1, wi0, wi1 = ind
            nwrite = wi1 - wi0
            if nwrite == 0:
                nbuf = bi1 - bi0 + 1
            nwrite += 1
        else:
            wi0 = 0
            bi0 = 0
            nwrite = self.desc.nbrWrites
        data_shape = (nwrite, nbuf, nsticks)
        stickdata = np.zeros(data_shape, dtype=np.float32)
        ret = TwGetPeakData(
            self.filename.encode(), pi0, nsticks, 0, 1, 0, nbuf, wi0, nwrite, stickdata
        )
        if ret != 4:
            raise Exception(
                "Loading UMR spectrum failed with code %s" % TwRetVal(ret).name
            )
        # Rearrange dimensions
        stickdata.shape = (-1, nsticks)
        stickdata = np.transpose(stickdata)
        # Move indices by one so that index==amu, unless pi0 is not 0
        if pi0 == 0:
            stickdata = np.vstack([np.zeros((stickdata.shape[1],)), stickdata])
        return stickdata  # mV/ext

    def load_tps_data(self, ind=None, loc=b"TPS2"):
        """Load TPS parameter data from the file.

        Parameters
        ----------
        ind : tuple, optional
            4-tuple with the range: (buf0, buf1, write0, write1),
            by default None. If None, full time range will be used.
        loc : bytes, optional
            Name of the dataset within the file, by default b'TPS2'

        Returns
        -------
        tuple
            2-tuple of (array, list) with the parameter data in an array
            and parameter names in a list.
        """

        nbuf = self.desc.nbrBufs
        nwrite = self.desc.nbrWrites
        # Query data size
        getsize = np.zeros((1, 1), dtype=int)
        TwGetRegUserDataFromH5(self.filename.encode(), loc, -1, -1, getsize, None, None)
        # Initialize data buffer
        nel = int(getsize.item() / (nbuf * nwrite))
        data_shape = (nwrite, nbuf, nel)
        data = np.zeros(data_shape)
        info = create_string_buffer(b"", 256 * nel)
        # Load all data
        TwGetRegUserDataFromH5(self.filename.encode(), loc, -1, -1, getsize, data, info)
        # Character array into string array
        info = np.asarray(info).view("S256").ravel()
        info = info.tolist()
        info = [i.decode("unicode_escape") for i in info]
        if ind is not None:
            # Select requested data
            bi0, bi1, wi0, wi1 = ind
            data = data[wi0 : wi1 + 1, :, :]
            data.shape = (-1, nel)
            i0 = bi0
            i1 = -(nbuf - bi1) + 1
            if i1 == 0:
                i1 = None
            data = data[i0:i1, :]
        else:
            # Reshape
            data.shape = (-1, nel)
        data = np.transpose(data)
        return data, info

    def fit_baseline(self, spec, lam=5e5, p=1e-7, niter=10):
        """Baseline removal from
        "Asymmetric Least Squares Smoothing" by P. Eilers and H. Boelens (2005)

        There are two parameters: p for asymmetry and λ for smoothness.
        Both have to be tuned to the data at hand.
        We found that generally 0.001 ≤ p ≤ 0.1 is a good choice
        (for a signal with positive peaks) and 10^2 ≤ λ ≤ 10^9 ,
        but exceptions may occur. In any case one should vary λ on a grid
        that is approximately linear for log λ

        NOTE: !!! This should be moved to a more appropriate place !!!

        Parameters
        ----------
        spec : array
            Data vector
        lam : float, optional
            Smoothness, by default 5e5
        p : float, optional
            Asymmetry, by default 1e-7
        niter : int, optional
            Number of iterations, by default 10

        Returns
        -------
        array
            Baseline
        """

        s = len(spec)
        # assemble difference matrix
        D0 = sparse.eye(s)
        d1 = [np.ones(s - 1) * -2]
        D1 = sparse.diags(d1, [-1])
        d2 = [np.ones(s - 2) * 1]
        D2 = sparse.diags(d2, [-2])

        D = D0 + D2 + D1
        w = np.ones(s)
        for i in range(niter):
            W = sparse.diags([w], [0])
            Z = W + lam * D.dot(D.transpose())
            bl = sparse.linalg.spsolve(Z, w * spec)
            w = p * (spec > bl) + (1 - p) * (spec < bl)
        return bl
