# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 10:42:01 2020

@author: Oskari Kausiala
"""

import numpy as np
import pandas as pd

from multiprocessing import (
                        cpu_count,
                        Queue,
                        Event,
                        Value,
                        Barrier,
                        Lock
                        )
from threading import Thread
from time import sleep
from scipy.stats import mode
from sklearn.preprocessing import normalize

from .feeder import KFeeder
from .collector import KCollector
from .worker import init_encoders
from .segment import KSegmentSequence

from hardware.tofwerk.generator import KAcquisition
from hardware.tofwerk.util import (
                        read_peaklist,
                        peaklist_to_df,
                        load_peak_dict,
                        )
from lib.struct import QueueSubscription


class KSignalProcessor(Thread):
    """Class to process data stream from TofDaq Recorder

    Attributes
    ----------
    state : str
        Description of the signal processor current status
    barrier : Barrier
        Barrier instance to synchronize KSignalProcessor threads
    shutdown_event : Event
        The thread runs until shutdown_event is set
    h5_write_lock : Lock
        Lock object to synchronize file access among threads
    kgen : KAcquisition or KStreamer
        KAcquisition or KStreamer instance, data producer
    processing_started : Event
        Event object which is set when processing has started, and
        cleared when it is finished
    processing_finished : Event
        Event object which is set when processing has finished, and
        cleared when it is started.
    kf : KFeeder
        KFeeder instance, initialized each time new acquisition starts
    kc : KCollector
        KCollector instance, initialized each time new acquisition starts
    kopid : KOnlinePeakId
        KOnlinePeakId instance, real-time peak identifier
    alpha : Value
        KEncoder alpha parameter
    D : csr
        KEncoder dictionary, sparse matrix
    target_list : str or dict or DataFrame
        List of targets to monitor
    u_list : list
        List of unit masses to monitor, inferred from the target list
    encoders : list
        List of KEncoder processes
    process_q : Queue
        Queue into which data is put by KFeeder to be processed by
        KEncoders
    result_q : Queue
        Queue into which KEncoders put the code, to be collected by
        KCollector
    active_events : list
        List of Event objects, one per KEncoder indicating whether
        they are currently processing an acquisition.
    """
    
    def __init__(self,
                 barrier,
                 shutdown_event,
                 h5_write_lock,
                 kgenerator,
                 target_list,
                 alpha,
                 D_file,
                 n_jobs=-1):
        """Initialize self

        Parameters
        ----------
        barrier : Barrier
            Barrier instance to synchronize KSignalProcessor threads
        shutdown_event : Event
            The thread runs until shutdown_event is set
        h5_write_lock : Lock
            Lock object to synchronize file access among threads
        kgenerator : KAcquisition or KStreamer
            KAcquisition or KStreamer instance, data producer
        target_list : str or dict or DataFrame
            List of targets to monitor
        alpha : Value
            KEncoder alpha parameter
        D_file : str
            Full file path to the KEncoder dictionary file
        n_jobs : int, optional
            Number of KEncoder processes to spawn, by default -1.
            If -1, the number of available CPU cores will be used.
        """

        self.state = 'Initializing'
        Thread.__init__(self)
        
        self.barrier = barrier
        self.shutdown_event = shutdown_event
        self.h5_write_lock = h5_write_lock
        self.kgen = kgenerator
        
        self.processing_started = Event()
        self.processing_finished = Event()
        
        self.kopid = None
                
        self.alpha = alpha
        self.D = load_peak_dict(D_file)
        
        self.init_target_list(target_list)
        self.init_workers(n_jobs)
        self.state = 'Initialized'
        
    def run(self):
        """Indefinitely wait for new acquisition unless
        shutdown_event has been set. When acquisition starts,
        initialize, process and finalize. Then again wait for the
        next acquisition.
        """

        while not self.shutdown_event.is_set():
            self.state = 'Waiting for acquisition'
            if self.kgen.acq_active.wait(timeout=1.):
                # Acquisition active
                self.init_acquisition()
                self.process_acquisition()
                self.finalize_acquisition()
        # Shutdown requested
        self.shutdown()
        self.state = 'Stopped'
        
    def init_target_list(self, target_list):
        """Load peaklist and define list of unit masses to process

        Parameters
        ----------
        target_list : str or dict or DataFrame
            List of targets to monitor
        """

        # Check and load peaklist
        if ( isinstance(target_list, str) or 
             isinstance(target_list, bytes) ):
            target_list = read_peaklist(target_list, .1)
        if isinstance(target_list, dict):
            target_list = peaklist_to_df(target_list)
        self.target_list = target_list
        # Define list of unit masses to process
        if len(target_list)==0:
            # No peaklist -> process all unit masses
            self.u_list = []
        else:
            # Peaklist defined -> only process relevant unit masses
            self.u_list = [ int(round(m)) 
                            for ms in target_list['mass']
                            for m in ms ]
            self.u_list = list(np.unique(self.u_list))
        
    def init_workers(self, n_jobs):
        """Initialize worker processes

        Parameters
        ----------
        n_jobs : [type]
            [description]
        """
        
        self.state = 'Initializing workers'
        if n_jobs == -1:
            n_jobs = cpu_count()
        (self.encoders, 
         self.process_q, 
         self.result_q, 
         self.active_events) = init_encoders(
                                         n_jobs, 
                                         self.D, 
                                         self.alpha, 
                                         error_log=False
                                          )
        for i, enc in enumerate(self.encoders):
            self.state = 'Spawning worker %s/%s' %((i+1), n_jobs)
            print(self.state)
            enc.start() # Start worker processes
        
    def init_acquisition(self):
        """Initialize threads in preparation for acquisition
        """
        
        self.state = 'Initializing acquisition'
        if self.kgen.avg_step is None:
            spec_queue = QueueSubscription(self.kgen.spec_queue)
        else:
            spec_queue = QueueSubscription(self.kgen.avg_queue)
        peak_id_queue = Queue()
        # Initialize feeder thread
        kf = KFeeder(self.kgen,
                     spec_queue,
                     self.process_q,
                     self.barrier,
                     self.u_list)
        # Initialize collector thread
        subsampling = 1.0 * self.D.shape[1] / self.D.shape[0] # Determine sub/supersampling from dictionary dimensions
        code_shape = ( int(self.kgen.desc.nbrSamples / subsampling),
                       self.kgen.desc.nbrBufs * self.kgen.desc.nbrWrites ) # Set code shape
        kc = KCollector(self.result_q,
                        self.barrier,
                        self.active_events,
                        code_shape,
                        peak_id_queue)
        # If target list given, initialize peak identifier
        if len(self.target_list) > 0:
            kopid = KOnlinePeakId(
                            self.target_list,
                            self.kgen,
                            kf.preprocessor.borders,
                            peak_id_queue
                            )
        else:
            kopid = None
        # Activate workers
        for e in self.active_events:
            e.set()
        kf.start() # Start feeder thread
        kc.start() # Start collector thread
        if kopid is not None:
            kopid.start() # Start peak identifier thread
        self.kf = kf
        self.kc = kc
        self.kopid = kopid
    
    def process_acquisition(self):
        """Actions to be performed while acquisition is running
        """

        self.state = 'Processing acquisition'
        self.processing_finished.clear()
        self.processing_started.set()
        while self.kc.collecting:
            try:
                sleep(.5)
            except:
                pass
        
    def finalize_acquisition(self):
        """Actions to be performed when acquisition has ended
        """

        self.state = 'Finalizing acquisition'
        self.barrier.wait() # Wait until all threads are finished
        self.process_q.get() # Clear poison pill from queue

        last_processed = self.kgen.acquired_file # Get filename
        if last_processed is None:
            return
        print('KSignalProcessor file write disabled')
        # self.h5_write_lock.acquire()
        # self.kc.write_to_file(last_processed) # Write code to file
        # with h5py.File(last_processed, 'r+') as h5f:
        #     # Add averaging step as an attribute
        #     avg_step = self.kgen.avg_step
        #     if avg_step is None:
        #         avg_step = 0
        #     h5f['Karsa/code'].attrs['avg_step'] = avg_step
        # # Write target list
        # print('Writing target list')
        # self.kopid.target_list.to_hdf(last_processed,
        #                               '/Karsa/target_list',
        #                               mode='r+'
        #                               )
        # self.h5_write_lock.release()
        # Clear processing flag
        self.processing_started.clear()
        self.processing_finished.set()
        print('KSignalProcessor ready')
    
    def shutdown(self):
        """Shutdown, close queues and end processes
        """

        self.state = 'Shutting down'
        # Kill Workers
        for i, enc in enumerate(self.encoders):
            self.active_events[i].set() # Wake up
            self.process_q.put(False) # Feed poison pill
            # Wait for worker to terminate
            enc.join(5) # timeout
            if enc.is_alive():
                # Force kill
                print('Force kill %s' %enc)
                enc.terminate()
        # Close and join queues
        self.process_q.close()
        self.process_q.join_thread()
        self.result_q.close()
        self.result_q.join_thread()
        

        
class KOnlinePeakId(Thread):
    """Online peak identifier. Get KEncoder results from queue and process.
    Put results (detected targets) to queue.

    TODO: !!! This implementation needs to be revisited and refactored !!!

    Attributes
    ----------
    kgen : KAcquisition or KStreamer
        KAcquisition or KStreamer instance, data producer
    target_list : DataFrame
        List of targets to monitor
    queue_in : Queue
        Queue to receive processed data from KEncoders
    updated : Event
        Event to be set when 'target_list' got updated.
    seg_seqs : list
        List of KSegmentSequences, keeping track of the peak detection
    all_peaks : DataFrame
        All detected peaks (ridges of the segment sequences)
    """

    def __init__(self,
                 target_list,
                 kgenerator,
                 segment_borders, 
                 queue_in):
        """Initialize self

        Parameters
        ----------
        target_list : DataFrame
            List of targets to monitor
        kgenerator : KAcquisition or KStreamer
            KAcquisition or KStreamer instance
        segment_borders : list
            List of 2-tuples, segment borders
        queue_in : Queue
            Queue to receive processed data from KCollector
        """

        Thread.__init__(self)
        self.kgen = kgenerator
        (self.target_list,
         self.target_peaks) = self.initialize_target_list(target_list)
        self.queue_in = queue_in
        self.updated = Event()

        self.seg_seqs = {}
        for b in segment_borders:
            b_hash = hash( (b[0], b[1]) )
            self.seg_seqs[b_hash] = KSegmentSequence(b)
        
        self.all_peaks = pd.DataFrame(columns=['mz', 'signal', 'ridge'])
        
    def initialize_target_list(self, target_list):
        """Prepare target list and target peak list

        Parameters
        ----------
        target_list : DataFrame
            List of targets to monitor

        Returns
        -------
        tuple
            Returns the modified 'target_list' and another DataFrame
            'target_peaks' where the peaks relevant to the 'target_list'
            are extracted into.
        """

        # Initialize i column
        target_list['i'] = range(len(target_list))
        # Initialize 'match' column
        target_list['match'] = [False] * len(target_list)
        # Initialize 'signal' column
        target_list['signal'] = [
                [0.0] * len(data['mass']) 
                for trg, data in target_list.iterrows()
                ]
        # Initialize mass error column
        target_list['mass error'] = [
                [None] * len(data['mass']) 
                for trg, data in target_list.iterrows()
                ]
        # Initialize isotope abundance match column
        target_list['abundance score'] = [0.0] * len(target_list)
        # Initialize isotope correlation coefficient column
        target_list['isotope r2'] = [0.0] * len(target_list)
        # Initialize target peak list
        target_is = []
        mzs = []
        for ref, data in target_list.iterrows():
            for mz in data.mass:
                target_is.append(data.i)
                mzs.append(mz)
        ridge_matches = [None]*len(mzs)
        mz_error = [None]*len(mzs)
        target_peaks = pd.DataFrame(columns=['target_i',
                                             'mz',
                                             'matching_ridge',
                                             'mz_error'],
                                    data=np.array([target_is,
                                                   mzs,
                                                   ridge_matches,
                                                   mz_error]).T
                                    )
        return target_list, target_peaks
        
    def run(self):
        """Get KEncoder results from queue, calculate identification score
        towards a target list and then match against set thresholds. Runs
        until poison pill is received to 'queue_in'.
        """

        while True:
            data = self.queue_in.get()
            if data is not None:
                i, s0, s1, code = data
                seq_hash = hash((s0, s1))
                self.seg_seqs[seq_hash].append(i, code)
                seg_ridges = self.seg_seqs[seq_hash].filter_ridges(
                                                        min_len=3
                                                        )
                for rdg in seg_ridges:
                    rdg_hash = hash((seq_hash, rdg[0][0]))
                    ppos = mode(rdg[0])[0][0] # peak position (sno)
                    mz = self.kgen.sno2mz(ppos) # peak mz
                    phei = np.sum(rdg[2]).item() # peak height
                    signal = phei #XXX Should convert to cps
                    # Construct row to all_peaks
                    peak = pd.DataFrame(index=[rdg_hash],
                                        data={'mz': [mz],
                                              'signal': [signal],
                                              'ridge': [rdg]
                                              }
                                        )
                    if not rdg_hash in self.all_peaks.index:
                        # New peak, append to all_peaks
                        self.all_peaks = self.all_peaks.append(peak)
                    else:
                        # Existing peak, update
                        self.all_peaks.update(peak)
                    # Match the peak with target_peaks list
                    self.match_ridge_to_target(peak)
            else:
                self.updated.clear()
                break

    def match_ridge_to_target(self, peak):
        """Try to find a match for a detected ridge in 'target_peaks'.
        If match is found, try to match 'target_peaks' with a target 
        in 'target_list'.

        TODO: !!! There are currently some hard-coded parameters which need
        to be tuned !!!

        Parameters
        ----------
        peak : DataFrame
            Single row DataFrame with parameters of a peak
        """

        mz_tol_ppm = 30 #XXX Preselection mz error tolerance
        peak_mz = peak.mz.iloc[0]
        mz_tol = 1e-6 * mz_tol_ppm * peak_mz
        match_ind = np.logical_and((self.target_peaks.mz >= peak_mz - mz_tol),
                                   (self.target_peaks.mz <= peak_mz + mz_tol)
                                   )
        for key, target_peak in self.target_peaks[match_ind].iterrows():
            dmz = target_peak.mz - peak_mz
            dmz_ppm = dmz / target_peak.mz * 1e6
            if (target_peak.mz_error is None or
                np.abs(target_peak.mz_error) < np.abs(dmz_ppm)):
                # New or better match found
                rdg_hash = peak.index
                data = {'target_i': target_peak.target_i,
                        'mz': target_peak.mz,
                        'matching_ridge': rdg_hash,
                        'mz_error': dmz_ppm
                        }
                self.target_peaks.loc[key] = data
                # Try to match with target compound
                self.score_peaks_to_targets(target_peak.target_i)

    def score_peaks_to_targets(self, target_i):
        """For a specified target, see if matching peaks can be found
        from 'target_peaks' and if so, put the detected target into
        'queue_out'.
        
        TODO: Separate this so that here the matching score is calculated
        and actual matching in separate function.

        Parameters
        ----------
        target_i : [type]
            [description]
        """

        match = True
        peaks = self.target_peaks[self.target_peaks.target_i == target_i]
        if (np.array(peaks.mz_error)==None).any():
            # Check if all target peaks detected, if not return
            match = False
            return
        target_ind = self.target_list.i == target_i
        target = self.target_list[target_ind].iloc[0]
        # Loop through detected peaks for target_i
        sum_signals = []
        signals = []
        mz_error = np.array(peaks.mz_error)
        target['mass error'] = mz_error
        for key, peak in peaks.iterrows():
            rdg_hash = peak.matching_ridge
            sum_signal = self.all_peaks.loc[rdg_hash].iloc[0].signal
            sum_signals.append(sum_signal)
            ridge = self.all_peaks.loc[rdg_hash].iloc[0].ridge
            signal = (ridge[1], ridge[2]) # (x, y)
            signals.append(signal)
        target['signal'] = np.array(sum_signals)
        # Isotope matching
        if len(peaks) > 1:
            # Abundance matching
            match_abus = normalize(
                    np.array(sum_signals).reshape(1, -1)
                    ).reshape(-1,)
            true_abus = normalize(
                    np.array(target['abundance']).reshape(1, -1)
                    ).reshape(-1,)
            abu_match = np.dot(match_abus, true_abus)
            # Correlation matching
            # First collect all spec indices to construct signal array
            xs = []
            for signal in signals:
                xs += signal[0]
            xs = np.unique(xs)
            # Construct signal array
            all_signals = np.zeros((len(signals), len(xs)))
            for row, signal in enumerate(signals):
                for si in range(len(signal[0])):
                    x = signal[0][si]
                    y = signal[1][si]
                    col = np.where(xs==x)
                    all_signals[row, col] = y
            pearr = np.min(np.corrcoef(all_signals))
            r2 = np.sign(pearr) * pearr**2
        else:
            abu_match = 1.0
            r2 = 1.0
        target['abundance score'] = abu_match
        target['isotope r2'] = r2
        # Do matching
        match = self.match_target(target)
        target['match'] = match
        # Update
        self.target_list.loc[target.name] = target
        if match:
            self.updated.set()

    def match_target(self, target):
        """Compare calculated identification scores to set parameters. 

        TODO: !!! There are some hard-coded parameters intended for testing
        purposes only !!!

        Parameters
        ----------
        target : DataFrame
            Single DataFrame row with target data

        Returns
        -------
        bool
            Returns True if match was found, False otherwise.
        """

        (threshold,
        mzErrTol,
        isoAbuTol,
        isoPearR
        ) = target.idPar
        #XXX Hard coded parameters for testing only
        mzErrTol = 20
        isoAbuTol = 0.9
        match = True
        if None in target['mass error']:
            match = False
        # Check m/z error condition
        if (np.abs(target['mass error']) > mzErrTol).any():
            # mz error condition not satisfied
            match = False
        # Check threshold condition
        if sum(target['signal']) < threshold:
            match = False
        # Check isotope abundance condition
        if target['abundance score'] < isoAbuTol:
            match = False
        # Check isotope correlation condition
        if target['isotope r2'] < isoPearR:
            match = False
        return match
    

if __name__ == '__main__':
    peaklist = '..//..//xplpar.db'
    alpha = Value('d', 1e-3)

    # ----------- Hard coded parameters -----------
    # Dictionary file for KSignalProcessor
    D_file = '..//..//test.h5'
    
    shutdown_event = Event()
    num_threads = 4 # generator
    barrier = Barrier(num_threads)
    
    avg_step = 10    
    stick_avg_step = None
    
    kacq = KAcquisition(
                barrier,
                shutdown_event,
                spec_queue=None,
                sum_queue=None,
                stick_queue=None,
                avg_stick_queue=None,
                tps_queue=None,
                avg_step=avg_step,
                stick_avg_step=stick_avg_step
                )
    
    h5_write_lock = Lock()

    ksp = KSignalProcessor(
                barrier,
                shutdown_event,
                h5_write_lock,
                kacq,
                peaklist,
                alpha,
                D_file,
                n_jobs=-1
                )
    kacq.start()
    ksp.start()
    kacq.acq_active.wait()
    sleep(1)
    
    from kscenthound_new import StatePrinter
    printer = StatePrinter(ksp)
    printer.start()
    while True:
        found_target = ksp.kopid.queue_out.get()
        if found_target is None:
            break
        else:
            print(found_target.name)
    input('Press any key to shutdown')
    shutdown_event.set()
    ksp.join()