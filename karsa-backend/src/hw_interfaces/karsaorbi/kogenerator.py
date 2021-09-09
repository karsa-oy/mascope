# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os

import numpy as np

from threading import Thread
from multiprocessing import Event, Queue
from queue import Empty

from time import sleep


from .lib import Business as ThermoBusiness
from .koutil import net2np_array


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
    def __init__(self, client, mz_precision=4):
        print("RawStreamer initializing")
        Thread.__init__(self)
        # Parameters
        self.client = client
        self._mz_precision = mz_precision
        # Thermo Fischer RawFileReaderFactory
        self.raw = None
        # Synchronization primitives
        # Streamer specific
        self.requests = client.requests     # Queue for files to stream
        self.request_in_progress = client.request_in_progress
        self.cancel_event = Event()         # Set to cancel current stream
        # Common with TofDaqStreamer
        self.shutdown_event = Event()       # Set to break out from main loop
        self.active = Event()               # RawStreamer active event
        self.spec_queue = Queue()           # Signal output queue
        # Per acquisition attributes
        self.filename = None                # Filename base from TW h5 file
        self.interval = None                # RawStreamer interval [s]
        self.length = None                  # RawStreamer length [s]
        self.progress = 0                   # RawStreamer progress [%]
        self.speci = -1                     # Index of last received spectrum,
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
        scan_stats = self.raw.GetScanStatsForScanNumber(scan_no)
        # Get timestamp from scan stats
        ti = scan_stats.StartTime * 60. # [s]
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

    def _finalize(self):
        """Finalize acquisition
        """
        self.raw.Dispose()
        # Reset self
        self._reset()
        # Feed poison pill
        self.spec_queue.put(None)

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
            print("RawStreamer started: %s" %self.filename)
        else:
            # New data
            self.speci = scan - 1
            print(self.speci)
            self._get_and_feed_data()
            # RawStreamer progress
            self.progress = (scan / self.raw.RunHeaderEx.LastSpectrum) * 100. # [%]

    def _wait_for_queues(self):
        """Wait for tick event to be set before continuing streaming

        Returns
        -------
        bool
            True if ticked, False if cancel or shutdown
        """
        while not (self.cancel_event.is_set() or self.shutdown_event.is_set()):
            if self.spec_queue.qsize():
                # Still something in queue
                sleep(.1)
            else:
                # Queues empty
                return True
        # Cancel or shutdown
        return False

    def _get_next_file_to_stream(self):
        # get next request to process
        rdata = self.requests.cache_get()
        if not rdata or not rdata['files']:
            return None, None
        fdata = rdata['files'].pop(0)
        client_room = rdata['client_room']
        if rdata['files']:
            # not all requested files are processed - put request back to queue
            self.requests.cache_put(rdata)
        return client_room, fdata

    def _update_request_in_progress(self, client_room, fdata):
        with self.client.lock:
            if client_room not in self.request_in_progress:
                self.request_in_progress[client_room] = {}
            fname = fdata['filename']
            self.request_in_progress[client_room][fname] = {
                **fdata,
                'progress': round(self.progress, 2),
                'streamer': self,
            }

    def _remove_request_in_progress(self, client_room, fname):
        with self.client.lock:
            del self.request_in_progress[client_room][fname]
            if not self.request_in_progress[client_room]:
                del self.request_in_progress[client_room]

    def run(self):
        print("RawStreamer running")
        # Main loop
        while not self.shutdown_event.is_set():
            client_room, fdata = self._get_next_file_to_stream()
            if not fdata:
                sleep(.5)
                continue
            fname = fdata['filename']

            # Initialize Raw file reader
            try:
                self.raw = ThermoBusiness.RawFileReaderFactory.ReadFile(fname)
                self.raw.SelectInstrument(0, 1)
            except Exception as e:
                print("Error reading file %s: %s" %(fname, e))
                continue

            # Start streaming
            # Update self and feed data into queue
            self._update()
            self._update_request_in_progress(client_room, fdata)
            # Set active flag 
            self.active.set()
            # Loop through the file and feed to queues
            scans = range(self.raw.RunHeaderEx.FirstSpectrum,
                          self.raw.RunHeaderEx.LastSpectrum + 1
                          )
            for scan in scans:
                # Update self and feed data into queue
                self._update(scan)
                self._update_request_in_progress(client_room, fdata)
                # Wait for queues to be empty
                if self._wait_for_queues():
                    # Empty
                    continue
                else:
                    # Shutdown
                    break
            # Out of stream loop
            self.active.clear()
            self.cancel_event.clear()
            self._finalize()
            self._remove_request_in_progress(client_room, fname)
            print("RawStream finished")
        # Out of main loop
        print('RawStreamer exiting')
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure
        """
        self.shutdown_event.set()
        # Clear all left-over data from queue
        while True:
            try:
                self.spec_queue.get_nowait()
            except Empty:
                break
            except ValueError:
                break
            except KeyboardInterrupt:
                break
            sleep(.1)
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()

    def stop_stream(self):
        """Stop stream before complete
        """
        self.cancel_event.set()
