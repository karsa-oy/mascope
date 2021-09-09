# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os

import numpy as np

from threading import Thread
from multiprocessing import (Event, Queue)
from queue import Empty

from time import sleep

from ctypes import create_string_buffer

from .kinstrument import KInstrument


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


class BaseStreamer(Thread):
    """Base class for TofDaqStreamer and H5Streamer to inherit common methods from.
    """
    def __init__(self):
        # Synchronization primitives
        self.shutdown_event = Event()   # Set to break out from main loop
        self.active = Event()           # TofDaqStreamer active event
        self.spec_queue = Queue()       # Signal output queue
        self.tps_queue = Queue()        # TPS output queue
        # Per acquisition attributes
        self.filename = None            # Filename base from TW h5 file
        self.interval = None            # TofDaqStreamer interval [s]
        self.length = None              # TofDaqStreamer length [s]
        self.progress = 0               # TofDaqStreamer progress [%]
        self.speci = -1                 # Index of last received spectrum,
                                        # -1 when there is no active acquisition
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
    
    def _finalize(self):
        """Finalize acquisition
        """
        # Reset self
        self._reset()
        # Feed poison pill
        self.spec_queue.put(None)
        self.tps_queue.put(None)

    def _reset(self):
        """Reset per acquisition attributes
        """
        self.filename = None
        self.progress = 0
        self.speci = -1

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
            self.interval = tof_period_s * self.desc.nbrWaveforms # [s]
            self.length = (self.desc.nbrWrites * self.desc.nbrBufs) * self.interval # [s]
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
            # TofDaqStreamer progress
            n = self.desc.nbrWrites * self.desc.nbrBufs # Total number of spectra
            self.progress = ((self.speci+1) / n) * 100. # [%]
         
    def shutdown(self):
        """Shutdown procedure
        """
        self.shutdown_event.set()
        # Clear left-over data from queues
        while True:
            try:
                self.spec_queue.get_nowait()
                self.tps_queue.get_nowait()
            except Empty:
                break
            sleep(.1)
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()
        self.tps_queue.close()
        self.tps_queue.join_thread()

class TofDaqStreamer(BaseStreamer):
    from .lib.TofDaq import (
            TwRetVal,
            TSharedMemoryDesc,
            TSharedMemoryPointer,
            TwAddLogEntry,
            TwGetDescriptor,
            TwTofDaqRunning,
            TwDaqActive,
            TwWaitForNewData,
            TwGetBufTimeFromShMem,
            TwGetTofSpectrumFromShMem,
            TwQueryRegUserDataSize,
            TwReadRegUserData,
            TwGetRegUserDataDesc,
            TwGetSpecXaxisFromShMem,
            TwStartAcquisition,
            TwStopAcquisition
            )
    def __init__(self):
        """Initialize self

        Inherits 'karsatof.kinstrument.KInstrument' which provides some
        convenience methods for instrument functions. TofDaq Recorder must 
        be running before initializing.

        Raises
        ------
        Exception
            Exception is raised if TofDaq Recorder is not running, or if
            fetching 'TwSharedMemoryDesc' fails for another reason.
        """
        print("TofDaqStreamer initializing")
        BaseStreamer.__init__(self)
        Thread.__init__(self)

        # Initialize TW API related structures 'desc' and 'ptr'
        if not TofDaqStreamer.TwTofDaqRunning():
            raise ModuleNotFoundError("TofDaq Recorder not running.")
        self.desc = TofDaqStreamer.TSharedMemoryDesc() # TW shared memory descriptor
        ret = TofDaqStreamer.TwGetDescriptor(self.desc)
        if ret == 4:
            # Success
            self.ptr = TofDaqStreamer.TSharedMemoryPointer() # TW shared memory pointer
        else:
            # Failed
            raise Exception("Trying to fetch shared memory " +
                            "descriptor failed: %s" %TofDaqStreamer.TwRetVal(ret).name)
        # Parameters
        self.timeout = 500 # [ms], timeout for TwWaitForNewData

    @property
    def mz(self):
        # Get mz axis from file
        mz = np.zeros((self.desc.nbrSamples,), dtype=np.double)
        TofDaqStreamer.TwGetSpecXaxisFromShMem(mz,
                                               1,
                                               None
                                               )
        return mz.astype(np.float32)

    def _get_and_feed_data(self):
        """Read data from the shared memory and put to queues
        """
        # Get timestamp from TW shared memory
        ti = np.zeros((1,))
        TofDaqStreamer.TwGetBufTimeFromShMem(ti, self.desc.iBuf, self.desc.iWrite)

        # == Get and feed mass spectrum data ==
        # Get most recent spectrum from TW shared memory
        spec = np.zeros((self.desc.nbrSamples, ), dtype=np.float32)
        ret = TofDaqStreamer.TwGetTofSpectrumFromShMem(spec, 0, 0, self.desc.iBuf, True)  # [mV/ext]
        if ret == 4: # Success
            # Combine data for output
            spec_data = {
                    'filename': self.filename,  # Current file basename
                    'i': self.speci,            # Current spectrum integer index
                    't': float(ti),             # Timestamp [s]
                    'period': self.interval,    # Collection period [s]
                    'spec': spec.tobytes()      # Serialized spectrum [float32]
                    }
            # Feed
            self.spec_queue.put(spec_data)

        # == Get and feed TPS data ==
        # Query data size
        nel = np.zeros((1,), dtype=int)
        TofDaqStreamer.TwQueryRegUserDataSize(b'/TPS2', nel)
        # Get most recent TPS data from TW shared memory
        data = np.zeros((nel.item(), 1),
                        dtype=np.double
                        )
        ret = TofDaqStreamer.TwReadRegUserData(b'/TPS2', nel.item(), data)
        if ret == 4: # Success
            # Combine data for output
            tps_data = {
                'filename': self.filename,          # Current file basename
                'i': self.speci,                    # Current spectrum integer index
                't': float(ti),                     # Timestamp [s]
                'period': self.interval,            # Collection period [s]
                'data': data.astype(np.float32 # convert to float32
                                ).reshape(-1   # reshape to (-1,)
                                ).tobytes(     # serialize
                                )                   # Serialized TPS data [float32]
                }
            # Feed
            self.tps_queue.put(tps_data)

    def _get_tps_info(self):
        """Get TPS parameter descriptions from TofDaq Recorder

        Returns
        -------
        list of str
            List of TPS parameter names
        """
        info = []
        # Query number of parameters
        nel = np.zeros((1,), dtype=int)
        if TofDaqStreamer.TwQueryRegUserDataSize(b'/TPS2', nel) == 4:
            # Parameter description buffer
            infobuf = create_string_buffer(b'', 256 * nel.item())
            if TofDaqStreamer.TwGetRegUserDataDesc(b'/TPS2', nel, infobuf) == 4:
                # Parameter descriptions retrieved succesfully
                # Convert char array to bytes array
                info = np.asarray(infobuf).view('S256').ravel()
                info = info.tolist() # Array to list
                info = [ i.decode('unicode_escape') for i in info ] # bytes to str
        return info

    def add_log_entry(self, text, timestamp=0):
        if timestamp:
            # Convert seconds to filetime
            acquisition_time_zero = self.desc.timeZero
            timestamp = int( acquisition_time_zero + (timestamp*1e7) )
        if not isinstance(text, bytes):
            # Convert string to bytes
            text = text.encode()
        TofDaqStreamer.TwAddLogEntry(text, timestamp)

    def run(self):
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'. 
        Loop until 'self.shutdown_event' is set.
        """

        print("TofDaqStreamer running")
        timeout_counter = 0
        # Main loop
        while not self.shutdown_event.is_set():
            ret = TofDaqStreamer.TwWaitForNewData(self.timeout,
                                                  self.desc,
                                                  self.ptr,
                                                  True
                                                  )
            # Timeout
            if ret == 8:
                timeout_counter += 1 # Increment counter
                if self.active.is_set():
                    if not TofDaqStreamer.TwDaqActive():
                        # No active acquisition
                        # TofDaqStreamer has ended
                        pass
                    else:
                        # Acquition active, but 'TwWaitForNewData' timed out

                        # Here we may end up from three scenarios:
                        # 1) TofDaqStreamer active, but interval is longer than 'self.timeout'
                        # 2) TwDaqActive not yet cleared after recently finished acquisition
                        # 3) DAQ configured to HW trigger mode, no actual acquisition (legacy feature)
                        
                        # Wait time so far
                        tot_wait = timeout_counter * self.timeout * 1e-3 # [s]
                        # Calculate acquisition interval
                        acquisition_interval = (self.desc.tofPeriod * 1e-9) * self.desc.nbrWaveforms # [s]
                        # Check if waited long enough already
                        wait_seconds = acquisition_interval + 1 # Wait one extra second
                        if not tot_wait > wait_seconds:
                            # Wait some more
                            continue
                        else:
                            # Waited long enough, declare acquisition finished
                            pass
                    # Clear active flag
                    self.active.clear()
                    # Reset self
                    self._finalize()
                    print("TofDaqStreamer finished")
            # New data
            elif ret == 4:
                # Reset timeout counter
                timeout_counter = 0
                # Update self and feed data into queue
                self._update()
                # Make sure active flag is set
                self.active.set()
                continue
            # Unexpected return value
            else:
                print("Unexpected return value: %s" %TofDaqStreamer.TwRetVal(ret).name)
                sleep(1)
        # Out of main loop
        print('TofDaqStreamer exiting')
        self.shutdown()

    def start_acquisition(self):
        """Start acquisition by calling TW API
        """
        TofDaqStreamer.TwStartAcquisition()

    def stop_acquisition(self):
        """Stop acquisition by calling TW API
        """
        TofDaqStreamer.TwStopAcquisition()

    def stop_stream(self):
        """Stop stream before complete
        """
        self.stop_acquisition()


class H5Streamer(BaseStreamer, KInstrument):
    from .lib.TwH5 import (
            TwGetBufTimeFromH5,
            TwGetH5Descriptor,
            TwGetRegUserDataFromH5,
            TwGetSpecXaxisFromH5,
            TwGetTofSpectrumFromH5,
            TwCloseH5,
            TwH5Desc,
            )
    def __init__(self, client):
        """Initialize self

        Inherits 'karsatof.kinstrument.KInstrument' which provides some
        convenience methods for instrument functions.

        Raises
        ------
        Exception
            Exception is raised if fetching 'TwH5Desc' fails for some reason.
        """
        print("H5Streamer initializing")
        BaseStreamer.__init__(self)
        Thread.__init__(self)

        # Initialize with empty TW h5 descriptor
        self.desc = H5Streamer.TwH5Desc()
        KInstrument.__init__(self, self.desc)

        # Synchronization primitives
        # Streamer specific
        self.client = client
        self.requests = client.requests         # Queue for files to stream
        self.request_in_progress = client.request_in_progress
        self.cancel_event = Event()             # Set to cancel current stream

    @property
    def mz(self):
        # Get mz axis from file
        mz = np.zeros((self.desc.nbrSamples,), dtype=np.double)
        H5Streamer.TwGetSpecXaxisFromH5(self.desc.currentDataFileName,
                                        mz,
                                        1,
                                        None,
                                        0,
                                        0
                                        )
        return mz.astype(np.float32)

    def _get_and_feed_data(self):
        """Read data from the h5 and put to queues
        """
        # Get timestamp from TW h5
        ti = np.zeros((1,))
        H5Streamer.TwGetBufTimeFromH5(self.desc.currentDataFileName,
                                      ti,
                                      self.desc.iBuf,
                                      self.desc.iWrite
                                      )
        # == Get and feed mass spectrum data ==
        # Get most recent spectrum from TW shared memory
        spec = np.zeros((self.desc.nbrSamples, ), dtype=np.float32)
        ret = H5Streamer.TwGetTofSpectrumFromH5(
                                self.desc.currentDataFileName,
                                spec,
                                0,                  # Segment start index
                                0,                  # Segment end index
                                self.desc.iBuf,     # Buf start index
                                self.desc.iBuf,     # Buf end index
                                self.desc.iWrite,   # Write start index
                                self.desc.iWrite,   # Write end index
                                True,               # BufWrite linked
                                True                # Normalize to
                                )                   # [mV/ext]
        if ret == 4: # Success
            # Combine data for output
            spec_data = {
                    'filename': self.filename,  # Current file basename
                    'i': self.speci,            # Current spectrum integer index
                    't': float(ti),             # Timestamp [s]
                    'period': self.interval,    # Collection period [s]
                    'spec': spec.tobytes()      # Serialized spectrum [float32]
                    }
            # Feed
            self.spec_queue.put(spec_data)

        # == Get and feed TPS data ==
        # Query data size
        nel = np.zeros((1,), dtype=int)
        H5Streamer.TwGetRegUserDataFromH5(
               self.desc.currentDataFileName,
               b'/TPS2',
               0,
               0,
               nel,
               None,
               None
               )
        # Get TPS data from TW h5
        data = np.zeros((nel.item(), ),
                        dtype=np.double
                        )
        ret = H5Streamer.TwGetRegUserDataFromH5(
               self.desc.currentDataFileName,
               b'/TPS2',
               self.desc.iBuf,
               self.desc.iWrite,
               nel,
               data,
               None # char buffer for info
               )
        if ret == 4: # Success
            # Combine data for output
            tps_data = {
                'filename': self.filename,          # Current file basename
                'i': self.speci,                    # Current spectrum integer index
                't': float(ti),                     # Timestamp [s]
                'period': self.interval,            # Collection period [s]
                'data': data.astype(np.float32  # convert to float32
                                ).tobytes(      # serialize
                                )                   # Serialized TPS data [float32]
                }
            # Feed
            self.tps_queue.put(tps_data)

    def _get_tps_info(self):
        """Get TPS parameter descriptions from TW h5

        Returns
        -------
        list of str
            List of TPS parameter names
        """
        info = []
        # Query TPS data size
        nel = np.zeros((1,), dtype=int)
        H5Streamer.TwGetRegUserDataFromH5(
                    self.desc.currentDataFileName,
                    b'TPS2',
                    0,
                    0,
                    nel,
                    None,
                    None
                    )
        # Parameter description buffer
        infobuf = create_string_buffer(b'', 256 * nel.item())
        # Get TPS data from TW h5
        data = np.zeros((nel.item(),),
                        dtype=np.double
                        )

        H5Streamer.TwGetRegUserDataFromH5(
                    self.desc.currentDataFileName,
                    b'TPS2',
                    0,
                    0,
                    nel,
                    data,   # data not used, but needs to be there
                    infobuf
                    )
        # Parameter descriptions retrieved succesfully
        # Convert char array to bytes array
        info = np.asarray(infobuf).view('S256').ravel()
        info = info.tolist() # Array to list
        info = [ i.decode('unicode_escape') for i in info ] # bytes to str
        return info

    def _wait_for_queues(self):
        """Wait for tick event to be set before continuing streaming

        Returns
        -------
        bool
            True if ticked, False if cancel or shutdown
        """
        while not (self.cancel_event.is_set() or self.shutdown_event.is_set()):
            if self.spec_queue.qsize() or self.tps_queue.qsize():
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
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'. 
        Loop until 'self.shutdown_event' is set.
        """

        print("H5Streamer running")
        # Main loop
        while not self.shutdown_event.is_set():
            client_room, fdata = self._get_next_file_to_stream()
            if not fdata:
                sleep(.5)
                continue
            fname = fdata['filename']

            # Update TW h5 descriptor
            ret = H5Streamer.TwGetH5Descriptor(fname.encode(), self.desc)
            if ret != 4:
                print("Error reading file: %s" %H5Streamer.TwRetVal(ret).name)
                continue
            # Add fields to comply with TW shared memory descriptor
            self.desc.currentDataFileName = fname.encode()
            self.desc.iBuf = 0
            self.desc.iWrite = 0
            if not (self.desc.nbrWrites and self.desc.nbrBufs):
                # Empty file, skip
                print("Skipping empty file: %s" %self.desc.currentDataFileName)
                continue

            # Start streaming
            # Update self and feed data into queue
            self._update()
            self._update_request_in_progress(client_room, fdata)
            # Set active flag 
            self.active.set()
            # Loop through the file and feed to queues
            # Loop through all 'writes'
            for iwrite in range(self.desc.nbrWrites):
                # Increment write index
                self.desc.iWrite = iwrite
                # Loop through all 'bufs' per 'write'
                for ibuf in range(self.desc.nbrBufs):
                    # Increment buf index
                    self.desc.iBuf = ibuf
                    # Update self and feed data into queue
                    self._update()
                    self._update_request_in_progress(client_room, fdata)
                    # Wait for queues to be empty
                    if self._wait_for_queues():
                        # Empty
                        continue
                    else:
                        # Shutdown
                        break
                # Out of buf loop
                # Check for cancel and shutdown flags
                if self.cancel_event.is_set() or self.shutdown_event.is_set():
                    break
            # Out of write loop
            self.active.clear()
            self.cancel_event.clear()
            self._finalize()
            self._remove_request_in_progress(client_room, fname)
            H5Streamer.TwCloseH5(fname.encode())
            print("h5Stream finished")
        # Out of main loop
        print('H5Streamer exiting')
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure
        """
        self.shutdown_event.set()
        # Clear all left-over data from queue
        while True:
            try:
                self.spec_queue.get_nowait()
                self.tps_queue.get_nowait()
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
        self.tps_queue.close()
        self.tps_queue.join_thread()

    def stop_stream(self):
        """Stop stream before complete
        """
        self.cancel_event.set()
