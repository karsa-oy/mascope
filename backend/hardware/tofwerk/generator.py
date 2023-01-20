# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
from threading import Thread
from multiprocessing import Event, Queue
from queue import Empty
from time import sleep


def strip_filepath(filepath):
    """Strip path and file extension

    Parameters
    ----------
    filepath : str
        Full file path

    Returns
    -------
    str
        Base filename
    """
    return os.path.splitext(os.path.basename(filepath))[0]


class BaseGenerator(Thread):
    """Base class for TofDaqStreamer and H5Streamer to inherit common methods from.
    """
    def __init__(self):
        # Synchronization primitives
        self.shutdown_event = Event()           # Set to break out from main loop
        self.active = Event()                   # TofDaqStreamer active event
        self.cancel_event = Event()             # Cancel event
        self.spec_queue = Queue()               # Signal output queue
        # self.tps_queue = Queue()                # TPS output queue
        # Per acquisition attributes
        self.filename = None                    # Filename base from TW h5 file
        self.interval = None                    # TofDaqStreamer interval [s]
        self.length = None                      # TofDaqStreamer length [s]
        self.sample_interval = None             # Tof sample interval [ns]
        self.single_ion_signal = None           # Single ion signal [mV*ns/ion]
        self.tof_frequency = None               # Tof frequency [Hz]
        self.speci = -1                         # Index of last received spectrum,
                                                # -1 when there is no active acquisition
        Thread.__init__(self)
        
    @property
    def conversion_coefficient(self):
        """Coefficient to convert signal intensity from [mV/ext] -> [ions/sec]
        """
        return (self.sample_interval * self.tof_frequency) / self.single_ion_signal

    @property
    def progress(self):
        # TofDaqStreamer progress
        if not self.active.is_set():
            return 100
        n = self.desc.nbrWrites * self.desc.nbrBufs # Total number of spectra
        return ((self.speci+1) / n) * 100. # [%]

    @property
    def tps_info(self):
        """List of TPS  names
        """
        return self._get_tps_info()

    def _check(self):
        """Check for state change

        Returns
        -------
        int
            State change: 2 new file, 1 new data, 0 nothing new
        """
        curr_filename = strip_filepath( self.desc.currentDataFileName.decode() )
        if self.filename != curr_filename:
            # New file
            return 2
        curr_speci = (self.desc.iWrite * self.desc.nbrBufs) + self.desc.iBuf
        if self.speci < curr_speci:
            # New data
            return 1
        # Nothing new
        return 0 
    
    def _feed_coordinates(self):
        coordinates = {
            'filename': self.filename,
            'i': -1,
            'mz': self.mz.tobytes(),
            'mz_calibration': self.mz_calibration,
            't_range': [0, self.length],
            'single_ion_signal': self.single_ion_signal,
        }
        self.spec_queue.put(coordinates)
        # tps_info = {
        #     'filename': self.filename,
        #     'i': -1,
        #     'tps_info': self.tps_info,
        #     't_range': [0, self.length],
        # }
        # self.tps_queue.put(tps_info)

    def _finalize(self):
        """Finalize acquisition
        """
        if not self.cancel_event.is_set():
            # Feed poison pill
            self.spec_queue.put({
                'filename': self.filename,
                'i': None,
                'source_filepath': self.desc.currentDataFileName.decode()
            })
            # self.tps_queue.put({
            #     'filename': self.filename,
            #     'i': None
            # })
        # Reset self
        self._reset()

    def _reset(self):
        """Reset per acquisition attributes
        """
        self.filename = None
        self.speci = -1
        self.sample_interval = None
        self.single_ion_signal = None
        self.tof_frequency = None

    def _update(self):
        """Update per acquisition attributes. If new data is available, feed into queues.
        """
        # Check for updates
        state = self._check()
        if state == 0:
            # No update
            return
        # Update
        if state == 2:
            # New file, update attributes
            h5_filepath = self.desc.currentDataFileName.decode() # TW h5 file full path
            self.filename = strip_filepath(h5_filepath)
            tof_period_s = self.desc.tofPeriod
            if tof_period_s > 1:
                # Convert [ns]->[s] if needed
                tof_period_s *= 1e-9
            self.sample_interval = self.desc.sampleInterval * 1e9 # [s]->[ns]
            self.single_ion_signal = self.desc.singleIonSignal
            self.tof_frequency = 1.0 / tof_period_s
            self.interval = tof_period_s * self.desc.nbrWaveforms # [s]
            self.length = (self.desc.nbrWrites * self.desc.nbrBufs) * self.interval # [s]
            # Feed coordinates
            self._feed_coordinates()
            print("TofDaqStreamer started: %s" %self.filename)
            # Check again for new data
            state = self._check()
        if state == 1:
            # New data
            new_speci = (self.desc.iWrite * self.desc.nbrBufs) + self.desc.iBuf
            if new_speci - self.speci > 1:
                print("Warning: Skipped a spec!")
            self.speci = new_speci
            print(self.speci)
            self._get_and_feed_data()
         
    def shutdown(self):
        """Shutdown procedure
        """
        self.shutdown_event.set()
        # Clear left-over data from queues
        while True:
            try:
                self.spec_queue.get_nowait()
                # self.tps_queue.get_nowait()
            except Empty:
                break
            sleep(.1)
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()
        # self.tps_queue.close()
        # self.tps_queue.join_thread()