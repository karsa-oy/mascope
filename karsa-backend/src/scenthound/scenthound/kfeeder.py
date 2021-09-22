# -*- coding: utf-8 -*-
"""Classes to collect data from KAcquisition, preprocess/slice it and feed to
KEncoder processes.

Created on Tue Apr 09 17:41:52 2019

@author: Oskari Kausiala
"""

import numpy as np
import scipy.sparse as sparse

from collections import OrderedDict
from threading import Thread
from multiprocessing import Queue, Barrier

#from .kcode import thresholding

from .karsavlm.msspectrum.utils import (
                    binary_search_for_left_range,
                    binary_search_for_right_range
                    )




class FeederProcessor():
    """Class used to define the preprocessing actions performed to a raw 
        spectrum before feeding to workers

        Attributes
        ----------
        kinst: KInstrument
            KInstrument (or KAcquisition) instance
        borders: list
            List of 2-tuples of ints, with segment borders as indices
            of the data vector
        accumulators: list
            List of KAccumulator instances, one per segment

    """
    
    def __init__(self):
        """Initialize self

        Parameters
        ----------
        kinstrument : KInstrument
            KInstrument (or KAcquisition) instance
        u_list : list
            List of integers, unit mass segments to process

        """

        self._fitted = False
        self.borders = OrderedDict()
        self.accumulators = []

    def fit(self, mz_axis, u_list=[]):
        """Generate unit mass borders (convert border m/z to index)

        Parameters
        ----------
        mz_axis : array
            m/z axis
        u_list : list
            List of integers, unit mass segments to process

        Returns
        -------
        list
            List of 2-tuples with (start index (sample number, int),
                                   end index (int)
                                   )
        """

        if len(u_list) == 0:
            u_list = np.unique( np.round(mz_axis).astype(int) )
        # Half mass borders
        u_borders = {}
        si0 = 0
        si1 = 0
        for u in u_list:
            si0 = si1 + binary_search_for_left_range(mz_axis[si1:], u-.5) - 1
            si0 = max(si0, 0)
            si1 = si0 + binary_search_for_right_range(mz_axis[si0:], u+.5)
            u_borders.update( {u: (si0, si1)} )
        
        self.borders = u_borders
        # Instantiate accumulator for each segment
        self.accumulators = [ KAccumulator(step=0,
                                           threshold=0.01) 
                              for _ in self.borders ]
        self._fitted = True

    def transform(self, speci, spec):
        """Preprocess one spectrum

        Parameters
        ----------
        speci : int
            Index of the spectrum
        spec : array
            Data vector

        Returns
        -------
        list
            List of 4-tuples with
            (speci (int),
            start index (sample number, int),
            end index (int),
            spectrum segment (array)
            ).
            If KAccumulators are used, this function only returns the
            segments which satisfy KAccumulator conditions (threshold).

        """

        if not self._fitted:
            raise Exception("Cannot transform before fitting")

        # Got new spectrum
        if spec is not None:
            # Split spectrum to segments
            parts = self._split_spec(spec) # parts = (u, s0, s1, partspec)
            tofeed = []
            for i, part in enumerate(parts):
                u, s0, s1, partspec = part
                # Accumulate each segment separately
                specis = self.accumulators[i].specis + [speci]
                acc = self.accumulators[i].accumulate(speci, partspec)
                if acc:
                    # Accumulated enough
                    # List indices accumulated
                    tofeedi = (specis, u, s0, s1, self.accumulators[i].avg_spec)
                    # Trim borders of the segment
                    # tofeedi = self._trim_partspec(tofeedi)
                    tofeed.append(tofeedi)
                else:
                    # Accumulation not complete, skip until next round
                    continue
        # Got poison pill
        else:
            # Flush accumulators
            tofeed = []
            for i, (u, (s0, s1)) in enumerate(self.borders.items()):
                specis = self.accumulators[i].specis
                if self.accumulators[i].flush():
                    spec = self.accumulators[i].avg_spec
                    tofeedi = (specis, u, s0, s1, spec)
                    tofeed.append(tofeedi)

        return tofeed

    def _split_spec(self, spec):
        """Split spectrum into segments by 'borders'

        Parameters
        ----------
        spec : array
            Data vector

        Returns
        -------
        list
            List of 3-tuples with (start index (sample number, int),
                                   end index (int),
                                   spectrum segment (array)
                                   ).

        """

        parts = []
        for u, (s0, s1) in self.borders.items():
            partspec = spec[s0:s1]
            parts.append( (u, s0, s1, partspec) )
        return parts

    def _trim_partspec(self, part, threshold=0.001):
        """Trim signal segment before feeding to workers

        NOTE: This function should be improved

        Parameters
        ----------
        part : tuple
            4-tuple with (speci (int),
                          start index (sample number, int),
                          end index (int),
                          spectrum segment (array)
                          )
        threshold : float, optional
            Threshold for trimming noise from segment edges,
            by default 0.001

        Returns
        -------
        4-tuple with (speci (int),
                      start index (sample number, int),
                      end index (int),
                      spectrum segment (array)
                      )
        """

        speci, s0, s1, uspec = part

        # Filter noise from edges
        ind = [True] * len(uspec)
        # Left edge
        i = 0
        step = 5
        while (i + step) <= len(ind):
            if sum( uspec[i:(i+step)] > 0 ) > 1:
                # More than one non-zero value
                break
            else:
                # 0 or 1 non-zero value, consider as noise
                ind[i:i+step] = [False] * step
                s0 += step
                i += step
        # Right edge
        i = len(uspec)
        while i-step >= 0:
            if sum( uspec[(i-step):i] > 0 ) > 1:
                # More than one non-zero value
                break
            else:
                # 0 or 1 non-zero value, consider as noise
                ind[(i-step):i] = [False] * step
                s1 -= step
                i -= step
        return speci, s0, s1, uspec[ind]

    def _baseline_als(self, y, lam=5e5, p=1e-7, niter=10):
        """Baseline removal from
        "Asymmetric Least Squares Smoothing" by P. Eilers and H. Boelens (2005)

        There are two parameters: p for asymmetry and λ for smoothness.
        Both have to be tuned to the data at hand.
        We found that generally 0.001 ≤ p ≤ 0.1 is a good choice
        (for a signal with positive peaks) and 10^2 ≤ λ ≤ 10^9 ,
        but exceptions may occur. In any case one should vary λ on a grid
        that is approximately linear for log λ

        Parameters
        ----------
        y : array
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
                        
        s = len(y)
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
            z = sparse.linalg.spsolve(Z, w * y)
            w = p * (y > z) + (1 - p) * (y < z)

        return z


class KFeeder(Thread):
    """Thread to receive data (raw spectra) from KAcquisition or KStreamer,
    slice it into unit mass segments, to be fed for KEncoder processes.
    Optionally some preprocessing can be done in addition to slicing
    (e.g. baseline removal, averaging/accumulation).
    
    ...
    
    Attributes
    ----------
    queue_in: Queue
        Input queue to receive spectra from
    queue_out : Queue
        Output queue to feed the segments into
    barrier : Barrier
        Barrier instance to synchronize KSignalProcessor threads
    preprocessor: FeederProcessor
        FeederProcessor class instance, where the preprocessing
        steps are defined
        
    """
    
    def __init__(self,
                 preprocessor=FeederProcessor(),
                 queue_in=Queue(),
                 queue_out=Queue(),
                #  barrier=Barrier(1)
                 ):
        """Initialize self

        Parameters
        ----------
        preprocessor : FeederProcessor, optional
            FeederProcessor instance defining the transformation
            to be done for each spectrum prior to feeding to workers.
        queue_in : Queue, optional
            Input queue to receive spectra from, by default
            Queue().
        queue_out : Queue, optional
            Output queue to feed the segments into, by default
            Queue().
        barrier : Barrier, optional
            Barrier instance to synchronize KSignalProcessor
            threads, by default Barrier(1).

        """

        Thread.__init__(self)
        self.preprocessor = preprocessor # Feeder processor
        self.queue_in = queue_in # Queue where raw signal will be put
        self.queue_out = queue_out # Queue where averaged segments will be put
        # self.barrier = barrier # Barrier to synchronize KScenthound threads

    def run(self):
        """Main loop

        Get data (or poison pill) from 'queue_in'. When spectrum is received, process
        it by 'preprocessor', and put processed segments into 'queue_out'. In case
        poison pill (None or False) is received, flush leftover data from preprocessor
        into 'queue_out' and then forward the poison pill (None). Finally wait for the
        'barrier'.

        """

        print("KFeeder started")
        speci = -1 # Index of most recent spectrum
        # Main loop
        while True:
            data = self.queue_in.get()
            # Received a spectrum
            if data:
                speci, spec = data
                # Prepare data for workers
                to_feed = self.preprocessor.transform(speci, spec)
                # Feed (averaged) segments
                for tf in to_feed:
                    self.queue_out.put(tf) # Feed data to workers
            # Received a poison pill or a break (False or None)
            else:
                # Got None
                if data is None:
                    if speci >= 0:
                        # Feed remains from accumulators if there is something
                        to_feed = self.preprocessor.transform(speci, None)
                        # Feed
                        for tf in to_feed:
                            self.queue_out.put(tf)
                        speci = -1
                    # self.queue_out.put(None)
                    # Wait for all threads to finish
                    # print("KFeeder waiting at barrier...")
                    # self.barrier.wait()
                # Got False
                else:
                    self.queue_out.put(False)
                    # Exit
                    break
        print("KFeeder exiting")


class KAccumulator():
    """Class to accumulate (sum) spectra. Can either accumulate a predefined
    number of spectra ('step' parameter) or until the signal norm reaches
    the 'threshold' parameter.

    Attributes
    ----------
    step: int
        Minimum number of spectra to accumulate
    threshold: float
        Accumulate until the norm of the signal reaches threshold
    i: int
        Number of spectra accumulated so far (reset after each True return)
    sum_spec: array
        The accumulated spectrum

    """

    def __init__(self, step, threshold=0.0):
        """Initialize self

        Parameters
        ----------
        step : int
            Number of spectra to accumulate
        threshold : float, optional
            Accumulate until signal norm reaches the threshold,
            by default 0.0
        """

        self.step = step # Minimum number of spectra to accumulate
        self.threshold = threshold # Accumulate until the norm of the signal reaches threshold
        self.specis = [] # Indices of spectra accumulated so far (reset after each True return)
        self.sum_spec = np.array([]) # The accumulated spectrum

    def accumulate(self, speci, spec):
        """Accumulate new data to the average spectrum

        Parameters
        ----------
        spec : array
            New data to accumulate

        Returns
        -------
        array or bool
            sum_spec is returned if accumulation conditions are met,
            False otherwise
        """

        if len(self.specis) == 0:
            self.sum_spec = np.zeros(spec.shape) # Instantiate/reset avg_spec
        self.sum_spec += spec # Accumulate 'avg_spec' with 'spec'
        self.specis.append(speci) # Update indics
        # Check accumulation conditions
        if ( len(self.specis) >= self.step and 
             (self.threshold == 0 or np.linalg.norm(self.sum_spec) > self.threshold) ):
            self.specis = [] # Reset indices
            return self.sum_spec # Accumulation finished
        else:
            return False # Accumulation not finished
        
    def flush(self):
        """When acquisition is finished, the accumulator should be flushed
        in order to make sure all data has been retrieved from the accumulator.

        Returns
        -------
        bool
            True is returned if there was something to flush,
            False otherwise
        """

        if len(self.specis) == 0:
            # Nothing to flush
            return False
        self.sum_spec /= float(len(self.specis)) # Normalize avg_spec
        self.specis = []
        return True