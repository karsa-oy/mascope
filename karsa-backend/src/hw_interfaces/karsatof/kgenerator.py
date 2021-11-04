# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
import numpy as np
from threading import Thread, current_thread
from multiprocessing import (Event, Queue)
from queue import Empty
from time import time, sleep
from ctypes import create_string_buffer
from ntpath import basename
import inspect

from karsalib.util import copy_dict, get_client_notification_context
from numpy.lib.index_tricks import RClass
from services.FileIoService import zarr_sdk
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
    return os.path.splitext(basename(filepath))[0]


class BaseStreamer():
    """Base class for TofDaqStreamer and H5Streamer to inherit common methods from.
    """
    def __init__(self):
        self.filename = None            # Filename base from TW h5 file
        self.interval = None            # TofDaqStreamer interval [s]
        self.length = None              # TofDaqStreamer length [s]
        self.progress = 0               # TofDaqStreamer progress [%]
        self.speci = -1                 # Index of last received spectrum,
                                        # -1 when there is no active acquisition

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

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

    def _get_tps_info(self):
        # virtual method
        pass

    def _get_and_feed_data(self):
        # virtual method
        pass

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
            self.log("started: %s" %self.filename)
            # Check again for new data
            state = self._check()
        if state == 1:
            # New data
            new_speci = (self.desc.iWrite * self.desc.nbrBufs) + self.desc.iBuf
            if new_speci - self.speci > 1:
                self.log("Warning: Skipped a spec!")
            self.speci = new_speci
            self.log(self.speci)
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

class TofDaqStreamer(BaseStreamer, Thread):
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
    def __init__(self, *arg, **kwarg):
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
        self.log("initializing")
        BaseStreamer.__init__(self)
        self.active = Event()           # Streamer active event
        self.spec_queue = Queue()       # Signal output queue
        self.tps_queue = Queue()        # TPS output queue
        self.shutdown_event = Event()   # Set to break out from main loop
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

        self.log("started")
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
                    self.log("finished streaming")
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
                self.log("Unexpected return value: %s" %TofDaqStreamer.TwRetVal(ret).name)
                sleep(1)
        # Out of main loop
        self.log("stopped")
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



MAX_RESPONSE_TIME = 5       # secs to wait for notification acknowledgement
PROGRESS_SHIFT = 10         # shift with acknowledged progress

class H5Streamer(BaseStreamer, KInstrument):
    from .lib.TwH5 import (
            TwGetBufTimeFromH5,
            TwGetH5Descriptor,
            TwGetRegUserDataFromH5,
            TwGetSpecXaxisFromH5,
            TwGetTofSpectrumFromH5,
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
        self.log("initializing")
        BaseStreamer.__init__(self)
        self.filename = None
        self.target_filename = None
        self.item = None                                # data item to stream/store
        self.ack_progress = -1
        self.rcontext = {}
        self.fdata = {}
        self.client = client
        self.requests = client.requests                 # Queue for files to stream
        self.responses = client.responses               # Queue for streamers notifications
        self.shutdown_event = client.shutdown_event     # Set to break out from main loop
        self.cancel_event = Event()                     # Set to cancel current stream
        Thread.__init__(self)

        # Initialize with empty TW h5 descriptor
        self.desc = H5Streamer.TwH5Desc()
        KInstrument.__init__(self, self.desc)

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

    def _check(self):
        """Check for state change

        Returns
        -------
        int
            State change: 2 new file, 1 new data, 0 nothing new
        """
        if self.progress == 0 and self.ack_progress == -1:
            # New file
            return 2
        curr_speci = (self.desc.iWrite * self.desc.nbrBufs) + self.desc.iBuf
        if self.speci < curr_speci:
            # New data
            return 1
        # Nothing new
        return 0


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


    #======== The service communication protocol implementation ===============
    def _feed_notifications(self, gen_notifications, streamer_notifications):
        # gen_notifications are sent always, and streamer_notifications
        # are sent in streamer mode, when target_data_pool_path is None
        if self.client.target_data_pool_path:
            notifications = gen_notifications
        else:
            notifications = [*gen_notifications, *streamer_notifications]
        for n in notifications:
            job_id_data = {'client_room':self.client_room, 'filename':self.filename}
            n.update(job_id_data)   # job_id_data needed for CacheQ indexing of self.responses
            self.responses.cache_put(n)

    def _feed_initial_data(self):
        progress_data = {
            'client_room': self.client_room,
            'source_filename': self.filename,
            'target_filename': self.target_filename,
            'progress': self.progress,
            'ack_progress': self.ack_progress,
        }
        sn_data = {
            'name': 'acquisition_coordinates',
            'value': {
                'filename': self.target_filename,
                'mz': self.mz.tobytes(),
                't_range': [0, self.length]
            },
        }
        gen_notifications = [
            {   # TODO: remove acquisition_status for acquisition_started
                'name': 'acquisition_status',
                'value': 'running',
                'context': self.rcontext,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
            {
                'name': 'acquisition_started',
                'value': {
                    'filename': self.target_filename,
                    'mz_range': [float(self.mz[0]), float(self.mz[-1])],
                    't_range': [0, self.length]
                },
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
            {
                'name': 'acquisition_progress',
                'value': progress_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        streamer_notifications = [
            {
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                    'callback': 'cb_progress',
                    'callback_data': progress_data,
                },
            },
            {  # TODO: remove this public notification after moving DataViz to private_ns
                **sn_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            },
        ]
        self._feed_notifications(gen_notifications, streamer_notifications)
        if self.client.target_data_pool_path:
            self.item = zarr_sdk.init_signal_dataset(sn_data, self.client.target_data_pool_path)
            self.ack_progress = self.progress

    def _feed_tps_parameter_info(self):
        sn_data = {
            'name': 'tps_parameter_info',
            'value': {
                'filename': self.target_filename,
                'tps_info': self.tps_info,
            },
        }
        gen_notifications = []
        streamer_notifications = [
            {
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        self._feed_notifications(gen_notifications, streamer_notifications)
        if self.client.target_data_pool_path:
            zarr_sdk.init_tps_dataset(sn_data, self.item)

    def _feed_spec_data(self, spec_data):
        progress_data = {
            'client_room': self.client_room,
            'source_filename': self.filename,
            'target_filename': self.target_filename,
            'progress': self.progress,
            'ack_progress': self.ack_progress,
        }
        sn_data = {
            'name': 'acquired_spectrum',
            'value': {
                **spec_data,
                'filename': self.target_filename,
            },
        }
        gen_notifications = [
            {
                'name': 'acquisition_progress',
                'value': progress_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        streamer_notifications = [
            {
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                    'callback': 'cb_progress',
                    'callback_data': progress_data,
                },
            },
            {  # TODO: remove this public notification after moving DataViz to private_ns
                **sn_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            },
        ]
        if self.client.target_data_pool_path:
            # target_data_pool_path specified - store data locally
            zarr_sdk.update_signal_dataset(sn_data, self.item)
            if self.item['signal'].delayed_write is None:
                # updates to signal mfzarrs are committed - notify
                dataset_updated = {
                    # TODO: switch to private notification after moving DataViz to private_ns
                    'name': 'dataset_updated',
                    'value': {
                        'data_type': 'signal',
                        **self.item['props'],
                    },
                    'context': {
                        **self.rcontext,
                        'namespace': '/',
                        'room': None,
                    },
                }
                gen_notifications.append(dataset_updated)
            # if data is stored locally, ack_progress is set locally,
            # otherwise by acquired_spectrum callback
            self.ack_progress = self.progress
        self._feed_notifications(gen_notifications, streamer_notifications)

    def _feed_tps_data(self, tps_data):
        sn_data = {
            'name': 'acquired_tps_data',
            'value': {
                **tps_data,
                'filename': self.target_filename,
            },
        }
        gen_notifications = []
        streamer_notifications = [
            {
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        self._feed_notifications(gen_notifications, streamer_notifications)
        if self.client.target_data_pool_path:
            zarr_sdk.update_tps_dataset(sn_data, self.item)

    def _feed_final_data(self):
        sn_data = {
            'name': 'acquisition_finished',
            'value': {
                'filename': self.target_filename,
            },
        }
        gen_notifications = [
            {   # TODO: remove acquisition_status for acquisition_finished
                'name': 'acquisition_status',
                'value': 'not_running',
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
            {   # acquisition_finished for progress bar
                **sn_data,
                'context': {
                    **self.rcontext,
                    'room': None,
                },
            },
        ]
        streamer_notifications = [
            {  # TODO: remove this public notification after moving DataViz to private_ns
                **sn_data,
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            },
        ]
        if self.client.target_data_pool_path and self.item:
            zarr_sdk.finalize_dataset(sn_data, self.item)
            # updates to signal mfzarrs are finalized - notify
            dataset_updated = {
                # TODO: switch to private notification after moving DataViz to private_ns
                'name': 'dataset_updated',
                'value': {
                    'data_type': 'signal',
                    **self.item['props'],
                },
                'context': {
                    **self.rcontext,
                    'namespace': '/',
                    'room': None,
                },
            }
            gen_notifications.append(dataset_updated)
        self._feed_notifications(gen_notifications, streamer_notifications)

# ==========================================================================


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
            self._feed_spec_data(spec_data)

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
            tps_data = {
                'filename': self.filename,          # Current file basename
                'i': self.speci,                    # Current spectrum integer index
                't': float(ti),                     # Timestamp [s]
                'period': self.interval,            # Collection period [s]
                'data': data.astype(np.float32  # convert to float32
                                ).tobytes(      # serialize
                                )                   # Serialized TPS data [float32]
                }
            self._feed_tps_data(tps_data)


    def _update(self):
        """Update per acquisition attributes. If new data is available, feed into queues.
        """
        # Check for updates
        state = self._check()
        if state == 0:      # No update
            return
        if state == 2:      # New sample
            # New file, update attributes
            tof_period_s = self.desc.tofPeriod
            if tof_period_s > 1:
                # Convert [ns]->[s] if needed
                tof_period_s *= 1e-9 
            self.interval = tof_period_s * self.desc.nbrWaveforms # [s]
            self.length = (self.desc.nbrWrites * self.desc.nbrBufs) * self.interval # [s]
            self._feed_initial_data()
            if not self.wait_for_ack():     # wait for acq data initialization
                raise TimeoutError
            self._feed_tps_parameter_info()
            # Check again for new data
            state = self._check()
        if state == 1:      # New data
            new_speci = (self.desc.iWrite * self.desc.nbrBufs) + self.desc.iBuf
            if new_speci - self.speci > 1:
                self.log("Warning: Skipped a spec!")
            self.speci = new_speci
            self.log(self.speci)
            # Streamer progress
            n = self.desc.nbrWrites * self.desc.nbrBufs # Total number of spectra
            self.progress = round(((self.speci+1) / n) * 100., 2) # [%]
            self._get_and_feed_data()
            # allow PROGRESS_SHIFT to make it quicker
            if not self.wait_for_ack(progress_shift=PROGRESS_SHIFT):
                raise TimeoutError


    def _initialize(self):
        self.filename = basename(self.fdata['filename'])
        self.target_filename = '_'.join([self.client.instrument_name, self.filename]).replace(' ', '_')
        self.client_room = self.rcontext['client_room']
        self.job_id = (self.client_room, self.filename)
        with self.client.lock:
            self.client.in_progress[self.job_id] = self

    def _reset(self):
        """Reset per acquisition attributes
        """
        with self.client.lock:
            self.client.in_progress.pop(self.job_id, None)
        self.job_id = None
        self.filename = None
        self.target_filename = None
        self.item = None
        self.rcontext = {}
        self.fdata = {}
        self.progress = 0
        self.ack_progress = -1
        self.speci = -1

    def wait_for_ack(self, progress_shift=0, timeout=MAX_RESPONSE_TIME):
        res = True
        t0 = time()
        while self.progress - self.ack_progress > progress_shift:
            if time() - t0 > timeout:
                self.log(f"Warning: {self.filename} - no progress acknowledgement for {timeout} sec.")
                res = False
                break
            sleep(.3)
        return res

    def _finalize(self):
        """Finalize acquisition
        """
        self._feed_final_data()
        if self.item and not self.cancel_event.is_set() and not self.shutdown_event.is_set():
            self.wait_for_ack()     # wait till all packages are processed
        self._reset()

    def _get_next_file_to_stream(self):
        # get next request to process
        with self.client.lock:
            rdata = self.requests.cache_get()
        if not rdata or not rdata['files']:
            return None, None
        fdata = rdata['files'].pop(0)
        rcontext = copy_dict(rdata, ignore_keys=['files',])
        if rdata['files']:
            # not all requested files are processed - put request back to queue
            self.requests.cache_put(rdata)
        return rcontext, fdata


    def run(self):
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'. 
        Loop until 'self.shutdown_event' is set.
        """
        self.log(f"started {current_thread().name}")
        # Main loop
        while not self.shutdown_event.is_set():
            self.rcontext, self.fdata = self._get_next_file_to_stream()
            if not self.fdata:
                sleep(.5)
                continue
            self._initialize()

            # Update TW h5 descriptor
            full_fname = self.fdata['filename']
            ret = H5Streamer.TwGetH5Descriptor(full_fname.encode(), self.desc)
            if ret != 4:
                # self.log("Error reading file: %s" %H5Streamer.TwRetVal(ret).name)
                self.log("Error reading file: %s" %full_fname)
                continue
            # Add fields to comply with TW shared memory descriptor
            self.desc.currentDataFileName = full_fname.encode()
            self.desc.iBuf = 0
            self.desc.iWrite = 0
            if not (self.desc.nbrWrites and self.desc.nbrBufs):
                # Empty file, skip
                self.log("Skipping empty file: %s" %self.desc.currentDataFileName)
                continue

            # Start streaming
            self.log(f"started streaming {self.filename}")
            try:
                # Update self and feed initial data into queue
                self._update()
                # Loop through the file and all 'writes'
                for iwrite in range(self.desc.nbrWrites):
                    # Increment write index
                    self.desc.iWrite = iwrite
                    # Loop through all 'bufs' per 'write'
                    for ibuf in range(self.desc.nbrBufs):
                        # Increment buf index
                        self.desc.iBuf = ibuf
                        # Update self and feed data into queue
                        self._update()
                    # Out of buf loop
                    # Check for cancel and shutdown flags
                    if self.cancel_event.is_set() or self.shutdown_event.is_set():
                        break
            except TimeoutError:
                self.log(f"Streaming {self.filename} interrupted due to timeout")
            except FileExistsError:     # only in import mode
                self.log(f"Importing {self.filename} cancelled: target exists")
            # Out of write loop
            self.log(f"finished streaming {self.filename}")
            res = H5Streamer.TwCloseH5(full_fname.encode())
            if res != 4:
                self.log(f"Warning: error closing {self.filename} ({res})")
            self._finalize()
            self.cancel_event.clear()
        # Out of main loop
        self.log(f"stopped {current_thread().name}")
        self.shutdown()


    def run_as_daemon(self):
        Thread(target=self.run).start()

    def shutdown(self):
        """Shutdown procedure
        """
        self.client.shutdown_event.set()

    def stop_stream(self):
        """Stop stream before complete
        """
        self.cancel_event.set()
