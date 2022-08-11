# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
import numpy as np
from multiprocessing import Event, Queue, Lock
from queue import Empty
from threading import Thread
from time import sleep

from ThermoFisher.CommonCore.Data import Business as ThermoBusiness

from .util import net2np_array


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


class RawStreamer(Thread):
    def __init__(
            self,
            file_queue=Queue(),
            shutdown_event=Event(),
            lock=Lock(),
            mz_precision=4
            ):
        print("RawStreamer initializing")
        Thread.__init__(self)
        # Parameters
        self._mz_precision = mz_precision
        # Thermo Fischer RawFileReaderFactory
        self.raw = None
        # Synchronization primitives
        self.file_queue = file_queue            # Queue for files to stream
        self.shutdown_event = shutdown_event    # Set to break out from main loop
        self.lock = lock
        self.cancel_event = Event()             # Set to cancel current stream
        self.active = Event()                   # Acquisition active event
        self.spec_queue = Queue()               # Signal output queue
        # Per acquisition attributes
        self.filename = None                    # Filename base from TW h5 file
        self.interval = None                    # Acquisition interval [s]
        self.length = None                      # Acquisition length [s]
        self.progress = 0                       # Acquisition progress [%]
        self.speci = -1                         # Index of last received spectrum,
                                                # -1 when there is no active acquisition

    @property
    def mz(self):
        if self.raw:
            return np.array([self.raw.RunHeaderEx.LowMass,
                             self.raw.RunHeaderEx.HighMass],
                            dtype=np.float32
                            )

    def _get_and_feed_data(self):
        """Read data from the RAW file and put to queues
        """
        # == Get and feed mass spectrum data ==
        scan_no = self.speci + 1
        # Get the scan statistics from the RAW file for this scan number
        with self.lock:
            scan_stats = self.raw.GetScanStatsForScanNumber(scan_no)
        # Get timestamp from scan stats
        ti = scan_stats.StartTime * 60. # [s]
        with self.lock:
            scan = self.raw.GetSegmentedScanFromScanNumber(scan_no, scan_stats)
        # Map .NET arrays into numpy arrays
        mz = net2np_array(scan.Positions).astype(np.float32)
        spec = net2np_array(scan.Intensities).astype(np.float32)
        # Round mz values based on the mz precision
        mz, spec = self._set_mz_precision(mz, spec)
        # Combine data for output
        spec_data = {
                'filename': self.filename,  # Current file basename
                'i': self.speci,            # Current spectrum integer index
                't': float(ti),             # Timestamp [s]
                'period': self.interval,    # Collection period [s]
                'mz': mz.tobytes(),         # Serialized mass axis [float32]
                'spec': spec.tobytes()      # Serialized spectrum [float32]
                }
        # Feed
        self.spec_queue.put(spec_data)

    def _feed_coordinates(self):
        coordinates = {
            'filename': self.filename,
            'i': -1,
            'mz': self.mz.tobytes(),
            't_range': [0, self.length],
        }
        self.spec_queue.put(coordinates)

    def _finalize(self):
        """Finalize acquisition
        """
        # Feed poison pill
        self.spec_queue.put({
            'filename': self.filename,
            'i': None
        })
        # Reset self
        self._reset()

    def _reset(self):
        """Reset per acquisition attributes
        """
        self.filename = None
        self.progress = 0
        self.speci = -1

    def _set_mz_precision(self, mz, spec):
        # Round the mz values based on the mz precision
        mz = np.asarray(np.round(mz, self._mz_precision), dtype=np.float32)

        # Contiguous mz values might now be equivalent. Combine their intensity values by taking the sum.
        unique_mz = np.unique(mz)
        unique_mz_intensities = np.zeros(unique_mz.shape, dtype=np.float32)

        # Note: This assumes that mz and unique_mz are sorted
        if len(mz) != len(unique_mz):
            acc = 0
            current_unique_mz_idx = 0
            current_unique_mz = unique_mz[0]
            for i, mz in enumerate(mz):
                if mz != current_unique_mz:
                    unique_mz_intensities[current_unique_mz_idx] = acc  # Flush the accumulator
                    acc = 0  # Reset the accumulator
                    current_unique_mz_idx += 1  # Go to the next unique mz value
                    current_unique_mz = unique_mz[current_unique_mz_idx]  # Get the unique mz value
                acc += spec[i]  # Increment the accumulator
            unique_mz_intensities[current_unique_mz_idx] = acc  # Flush the accumulator
        else:
            unique_mz_intensities = spec

        return unique_mz, unique_mz_intensities

    def _update(self, scan=None):
        """Update per acquisition attributes. If new data is available, feed into queues.
        """
        # Update
        if scan is None:
            # New file, update attributes
            raw_filepath = self.raw.FileName # TF RAW file full path
            self.filename = strip_filepath(raw_filepath)            
            self.length = self.raw.RunHeaderEx.EndTime * 60. # [s]
            self.interval = self.length / self.raw.RunHeaderEx.LastSpectrum # [s]
            # Feed coordinates
            self._feed_coordinates()
            print("Acquisition started: %s" %self.filename)
        else:
            # New data
            self.speci = scan - 1
            print(self.speci)
            self._get_and_feed_data()
            # Acquisition progress
            self.progress = (scan / self.raw.RunHeaderEx.LastSpectrum) * 100. # [%]

    def _wait_for_queues(self):
        """Wait for tick event to be set before continuing streaming

        Returns
        -------
        bool
            True if ticked, False if shutdown
        """
        while not self.shutdown_event.is_set():
            if not self.spec_queue.qsize():
                # Queues empty
                return True
            elif self.cancel_event.is_set():
                # Cancelled
                while self.spec_queue.qsize():
                    self.spec_queue.get_nowait()
            else:
                # Wait for data to be consumed from queues
                sleep(.01)
        # Shutdown
        return False

    def run(self):
        print("RawStreamer running")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_to_stream = self.file_queue.get(timeout=.1)
                # Initialize Raw file reader
                try:
                    with self.lock:
                        self.raw = ThermoBusiness.RawFileReaderFactory.ReadFile(
                            file_to_stream
                        )
                    self.raw.SelectInstrument(0, 1)
                except Exception as e:
                    print("Error reading file %s: %s" %(file_to_stream, e))
                    continue
            except Empty:
                continue

            # Start streaming
            # Update self and feed data into queue
            self._update()
            # Set active flag 
            self.active.set()
            # Loop through the file and feed to queues
            scans = range(self.raw.RunHeaderEx.FirstSpectrum,
                          self.raw.RunHeaderEx.LastSpectrum + 1
                          )
            for scan in scans:
                # Update self and feed data into queue
                self._update(scan)
                # Wait for queues to be empty
                if self._wait_for_queues():
                    # Empty
                    continue
                else:
                    # Shutdown
                    break
            # Out of stream loop
            self.raw.Dispose()
            self.active.clear()
            self.cancel_event.clear()
            self._finalize()
            print("RawStream finished")
        # Out of main loop
        print('RawStreamer exiting')
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure
        """
        self.shutdown_event.set()
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()

    def start_stream(self, filename):
        if os.path.isfile(filename):
            self.file_queue.put(filename)
        else:
            raise ValueError("File does not exist: %s" %filename)

    def stop_stream(self):
        """Stop stream before complete

        TODO: To be implemented
        """
        raise NotImplementedError