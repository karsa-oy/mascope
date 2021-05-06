# -*- coding: utf-8 -*-
"""
Created on Tue Apr 09 17:48:15 2019

@author: Oskari Kausiala
"""

import sys
import os
import numpy as np

from time import sleep
from multiprocessing import Process, Queue, Event
from PIL.Image import Image
from sklearn.decomposition import SparseCoder
from scipy.sparse import csr_matrix
from threading import Thread

from .kcode import find_extrema, find_code_peaks
from .kpeak import fit_peaks
from .kimage import (gen_spec_image,
                     gen_timeseries_trace,
                     gen_heatmap_image,
                     convert_to_base64
                     )

from sklearn.exceptions import ConvergenceWarning
import warnings
warnings.filterwarnings('ignore', category=ConvergenceWarning)


class KEncoder(Process):
    """Process to perform SparseCoding to a segment of mass spectrum

    TODO: Sub-/supersampling notfully implemented nor tested.

    Attributes
    ----------
    alpha : Value
        Regularization parameter for the SparseCoder
    queue_in : Queue
        Queue to read signal from
    queue_out : Queue
        Queue to put results into
    event_active : Event
        Process active flag
    D : csr
        SparseCoder dictionary, sparse matrix whose data is stored in
        RawArrays and shared among all KEncoder processes
    error_log : bool
        Log errors to txt file
    """

    def __init__( self,
                  alpha,
                  queue_in,
                  queue_out,
                  event_active,
                  D_shape,
                  D_data,
                  D_indices,
                  D_indptr,
                  error_log=False
                ):
        """Initialize self

        Parameters
        ----------
        alpha : Value
            Regularization parameter for the SparseCoder
        queue_in : Queue
            Queue to read signal from
        queue_out : Queue
            Queue to put results into
        event_active : Event
            Process active flag
        D_shape : tuple
            Dictionary shape
        D_data : RawArray
            Dictionary data
        D_indices : RawArray
            Dictionary indices
        D_indptr : RawArray
            Dictionary index pointer
        error_log : bool, optional
            Log errors to txt file, by default False
        """
        
        # Initialize logging
        if error_log:
            self.initialize_logging()

        Process.__init__(self)
        self.alpha = alpha
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.event_active = event_active
        # Construct sparse matrix instance for the dictionary
        self.D = csr_matrix((D_data, D_indices, D_indptr),
                            shape=D_shape,
                            copy=False
                            )

    def run(self):
        """Main loop
        """
            
        # Main loop
        while True:
            data = self.queue_in.get() # Get data
            # Set active flag
            self.event_active.set()
            if data:
                # Received data
                i, u, s0, s1, spec = data # speci, unit mass, sample0, sample1, segment
                # SparseCoder
                # if not sub/supersampling, i0==s0 & i1==s1
                i0, i1, code, approx = self.encode(s0, s1, spec)
                # Find peaks
                peak_ind = find_extrema(code)
                peak_x = np.array(range(i0, i1))[peak_ind] # TODO: Fit peaks for better accuracy?
                peak_y = code[peak_ind] # TODO: Fit peaks / integrate for better accuracy?
                peaks = list( zip(peak_x, peak_y) )
                # Sample numbers
                snos = np.arange(s0, s1)
                results = {'specis': i,
                           'u': u,
                           'snos': snos,
                           'spec': spec,
                           'approx': approx,
                           'code': code,
                           'peaks': peaks
                           }
                self.queue_out.put(results)
            else:
                # Clear active flag
                self.event_active.clear()
                # Received break (None)
                if data is None:
                    # Put None back to the queue
                    # self.queue_in.put(None)
                    # Wait until active flag is reset
                    # self.event_active.wait()
                    pass
                # Received poison pill (False)
                else:
                    self.queue_in.put(False)
                    break

    def initialize_logging(self):
        """Reroute stderr of the process to file, for debugging
        """
        
        sys.stdout = open(str(os.getpid()) + ".out", "a", buffering=0)
        sys.stderr = open(str(os.getpid()) + "_error.out", "a", buffering=0)
    
    def encode(self, s0, s1, spec):
        """Function that performs SparseCoding for a segment of mass spectrum

        Parameters
        ----------
        s0 : inst
            First sample number
        s1 : inst
            Last sample number
        spec : array
            Signal to encode

        Returns
        -------
        tuple
            3-tuple is returned with (i0, i1, code), where 'i0' and 'i1'
            are the rows of the dictionary and 'code' is the processing result.
            If subsampling=1, i0==s0 and i1==s1.
        """

        # Check if sub/supersampling
        subsampling = 1.0 * self.D.shape[1] / self.D.shape[0]
        i0 = int(s0 / subsampling) # Index of first row of D
        i1 = int(s1 / subsampling) # Index of last row of D
        D = self.D[i0:i1, s0:s1].toarray() # Load the relevant part of the dictionary
        #D_norm = normalize(D, axis=0, norm='l1')
        # Initialize SparseCoder
        coder = SparseCoder(dictionary=D,
                            transform_algorithm='lasso_cd',
                            transform_alpha=self.alpha.value,
                            n_jobs=1,
                            positive_code=True)
        y = spec.reshape(1, -1)
        #ynorm = normalize(y, norm='l1', axis=1, copy=False)
        code = coder.transform(y).reshape((-1,)) # Process
        code = code.astype(np.float32)
        approx = np.dot(code, D).reshape((-1,))
        return i0, i1, code, approx


viz_generators = {
            'spectrogram': gen_heatmap_image,
            'timeseries': gen_timeseries_trace,
            'waterfall': gen_spec_image,
            }

class ImageGenerator(Process):
    def __init__(self, queue_in, queue_out, shutdown_event):
        Process.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.shutdown_event = shutdown_event

    def run(self):
        global viz_generators
        while not self.shutdown_event.is_set():
            try:
                data = self.queue_in.get()
            except KeyboardInterrupt:
                self.shutdown_event.set()
                break
            if data is not None:
                # Select function to generate the image
                viz_type = data['viz_type']
                try:
                    viz_gen_func = viz_generators[viz_type]
                except KeyError:
                    print("Requested visualization type '%s' not available!" %viz_type)
                    continue
                data_array = data.pop('data')
                y_range = data.get('y_range', None)
                try:
                    viz = viz_gen_func(data_array,
                                       y_range=y_range
                                       )
                except ZeroDivisionError:
                    print("Caught ZeroDivisionError in %s" %str(viz_gen_func))
                    continue
                if isinstance(viz, Image):
                    img_b = convert_to_base64(viz)
                    data.update({'img': img_b})
                elif isinstance(viz, dict):
                    data.update({'traces': [viz]})
                self.queue_out.put(data)
            else:
                break

class SpecTraceGenerator(Process):

    def __init__(self, queue_in, queue_out):
        Process.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out

    def run(self):
        while True:
            data = self.queue_in.get()
            if data is not None:
                data_array = data.pop('data')
                y_range = data.pop('y_range', None)
                img = gen_spec_image(data_array,
                                     y_range=y_range
                                     )
                img_b = convert_to_base64(img)
                data.update({'img': img_b})
                self.queue_out.put(data)
            else:
                break

class HeatmapGenerator(Process):

    def __init__(self, queue_in, queue_out):
        Process.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out

    def run(self):
        while True:
            data = self.queue_in.get()
            if data is not None:
                data_array = data.pop('data')
                y_range = data.pop('y_range', None)
                img = gen_heatmap_image(data_array,
                                        y_range=y_range
                                        )
                img_b = convert_to_base64(img)
                data.update({'img': img_b})
                self.queue_out.put(data)
            else:
                break

# -------- Deprecated / experimental code below ---------

# class KWorker(Process):
#     def __init__(
#             self,
#             peakshapes,
#             r_par,
#             alpha,
#             queue_in,
#             queue_out,
#             D_shape,
#             D_data,
#             D_indices,
#             D_indptr,
#             error_log=False):
#         Process.__init__(self)
#         self.peakshapes = peakshapes
#         self.r_par = r_par
#         self.alpha = alpha
#         self.queue_in = queue_in
#         self.queue_out = queue_out
#         self.D = csr_matrix((D_data, D_indices, D_indptr),
#                             shape=D_shape, copy=False)
#         self.error_log = error_log

#     def run(self):
#         if self.error_log:
#             self.initialize_logging()
#         while True:
#             data = self.queue_in.get()
#             if data:
#                 # Received data
#                 i, s0, s1, spec = data
#                 code = self.encode(s0, s1, spec)
#                 self.queue_out.put((i, s0, s1, code))

#                 s = np.mean([s0, s1])
#                 r = self.rfun(s)
#                 ps_def = np.asarray(self.peakshapes.keys())
#                 ps_ind = np.argmin(abs(ps_def - s))
#                 ps = self.peakshapes[ps_def[ps_ind]]
#                 self.fit_peaks(np.arange(s0, s1), spec, code, ps, r)

#             else:
#                 # Received break
#                 if data is None:
#                     self.queue_out.put(None)
#                 # Received poison pill
#                 else:
#                     self.queue_out.put(False)
#                     return

#     def initialize_logging(self):
#         # Reroute stderr to file
#         sys.stdout = open(str(os.getpid()) + ".out", "a", buffering=0)
#         sys.stderr = open(str(os.getpid()) + "_error.out", "a", buffering=0)

#     def rfun(self, ppos):
#         R0, m0, dm = self.r_par
#         return R0 - (R0 / (1 + np.exp((ppos - m0) / dm)))

#     def encode(self, s0, s1, spec):
#         D = self.D[s0:s1, s0:s1].toarray()
#         #D_norm = normalize(D, axis=0, norm='l1')
#         coder = SparseCoder(dictionary=D,
#                             transform_algorithm='lasso_cd',
#                             transform_alpha=self.alpha,
#                             n_jobs=None,
#                             positive_code=True)
#         y = spec.reshape(1, -1)
#         #ynorm = normalize(y, norm='l1', axis=1, copy=False)
#         code = coder.transform(y).reshape((-1,))
#         #approx = np.dot(code, D_norm).reshape((-1,))
#         return code

#     def fit_peaks(self, snos, spec, code, ps, R):
#         if sum(code) == 0:
#             return []
#         min_hei = 2e-4
#         init_peaks = find_code_peaks(code, min_height=min_hei)
#         if len(init_peaks) == 0:
#             return []
#         while len(init_peaks) > 10:
#             min_hei += 5e-5
#             init_peaks = find_code_peaks(code, min_height=min_hei)
#         phei0 = spec[init_peaks]
#         ppos0 = snos[init_peaks]
#         fit = fit_peaks(snos,
#                         spec,
#                         ps,
#                         len(init_peaks),
#                         ppos0,
#                         phei0,
#                         [R] * len(init_peaks),
#                         True,
#                         True,
#                         False,
#                         dpos=3,
#                         max_iter=1500)
#         peaks = []
#         for p in range(len(fit.params) / 3):
#             peak = (fit.params['p%spos' % p].value,
#                     fit.params['p%shei' % p].value)
#             peaks.append(peak)
#         #deconv[s0:s1] += spec - fit.residual
#         #resid[s0:s1] += fit.residual
#         return peaks


# def init_workers(n_jobs, kinstrument, D, alpha, error_log=False):
#     workers = []
#     process_qs = []
#     result_qs = []

#     D_data = RawArray('d', D.data)
#     D_indices = RawArray('i', D.indices)
#     D_indptr = RawArray('i', D.indptr)
#     for n in range(n_jobs):
#         qin = Queue()
#         qout = Queue()
#         peakshapes = kinstrument.peakshapes
#         r_par = (kinstrument.R0, kinstrument.m0, kinstrument.dm)
#         wrkr = KWorker(
#             peakshapes,
#             r_par,
#             alpha,
#             qin,
#             qout,
#             D.shape,
#             D_data,
#             D_indices,
#             D_indptr,
#             error_log)
#         workers.append(wrkr)
#         process_qs.append(qin)
#         result_qs.append(qout)

#     return workers, process_qs, result_qs


# class KFitter(Process):
#     def __init__(self, queue_in, queue_out):
#         Process.__init__(self)
#         self.queue_in = queue_in
#         self.queue_out = queue_out

#     def run(self):
#         while True:
#             if self.queue_in.empty():
#                 sleep(.1)
#             else:
#                 data = self.queue_in.get()
#                 if data:
#                     # Received data
#                     snos, spec, code, ps, R = data
#                     peaks = self.fit_peaks(snos, spec, code, ps, R)
#                     self.queue_out.put(peaks)
#                 else:
#                     # Received break
#                     if data is None:
#                         self.queue_out.put(None)
#                     # Received poison pill
#                     else:
#                         self.queue_out.put(False)
#                         return

#     def fit_peaks(self, snos, spec, code, ps, R):
#         if sum(code) == 0:
#             return []
#         min_hei = 2e-4
#         peaks = find_code_peaks(code, min_height=min_hei)
#         if len(peaks) == 0:
#             return []
#         phei0 = spec[peaks]
#         ppos0 = snos[peaks]
#         fit = fit_peaks(snos,
#                         spec,
#                         ps,
#                         len(peaks),
#                         ppos0,
#                         phei0,
#                         [R] * len(peaks),
#                         True,
#                         True,
#                         False,
#                         dpos=3,
#                         max_iter=1500)
#         peaks = []
#         for p in range(len(fit.params) / 3):
#             peak = (fit.params['p%spos' % p].value,
#                     fit.params['p%shei' % p].value)
#             peaks.append(peak)
#         #deconv[s0:s1] += spec - fit.residual
#         #resid[s0:s1] += fit.residual
#         return peaks


# def init_fitters(n_jobs):
#     fitters = []
#     process_qs = []
#     result_qs = []
#     for n in range(n_jobs):
#         qin = Queue()
#         qout = Queue()
#         fittern = KFitter(qin, qout)
#         fitters.append(fittern)
#         process_qs.append(qin)
#         result_qs.append(qout)
#     return fitters, process_qs, result_qs


# def fit_event(kevent, u_list, n_jobs):
#     code = kevent.get_code()
#     spec = kevent.get_spec()
#     fitters, process_qs, result_qs = init_fitters(n_jobs)
#     for f in fitters:
#         f.start()
#     for i, u in enumerate(u_list):
#         usn = kevent.mz2sno(u, True)
#         usnos = np.arange(
#             kevent.mz2sno(
#                 u - .5,
#                 True),
#             kevent.mz2sno(
#                 u + .5,
#                 True))
#         uspec = spec[usnos]
#         ucode = code[usnos]
#         ups = kevent.get_ps(usn)
#         uR = kevent.r_at_3p(usn)
#         fi = i % n_jobs
#         process_qs[fi].put((usnos, uspec, ucode, ups, uR))
#     for q in process_qs:
#         q.put(False)
#     peaks = []
#     while True:
#         for q in result_qs:
#             if not q.empty():
#                 upeaks = q.get()
#                 if not upeaks:
#                     result_qs.remove(q)
#                     break
#                 else:
#                     peaks.extend(upeaks)
#         if len(result_qs) == 0:
#             break
#     return peaks