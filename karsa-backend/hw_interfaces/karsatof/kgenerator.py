# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os

import numpy as np

from threading import Thread
from multiprocessing import (Barrier, Event, Process, Queue)
from queue import Empty

from time import sleep

from ctypes import create_string_buffer

from .lib.TofDaq import (
    TwRetVal,
    TSharedMemoryDesc,
    TSharedMemoryPointer,
    TwGetDescriptor,
    TwTofDaqRunning,
    TwDaqActive,
    TwWaitForNewData,
    TwGetBufTimeFromShMem,
    TwGetTofSpectrumFromShMem,
    TwGetStickSpectrumFromShMem,
    TwGetSumSpectrumFromShMem,
    TwQueryRegUserDataSize,
    TwReadRegUserData,
    TwGetRegUserDataDesc,
    TwSetDaqParameter,
    TwGetDaqParameter,
    TwGetDaqParameterInt,
    TwAddAttributeInt,
    TwAddAttributeDouble,
    TwAddAttributeString,
    TwStartAcquisition,
    TwStopAcquisition
    )
from .lib.TwH5 import (
    TwGetBufTimeFromH5,
    TwGetH5Descriptor,
    TwGetRegUserDataFromH5,
    TwGetSpecXaxisFromH5,
    TwGetTofSpectrumFromH5,
    TwH5Desc,
)

from .kinstrument import KInstrument
from .kfeeder import KAccumulator
from .kevent import KEvent
from .kutil import SubscriptableQueue


class KAcquisition(Thread, KInstrument):
    """ Thread to interface with TofDaq Recorder, access shared memory
        and feed data into queues.

    Attributes
    ----------
    desc: TSharedMemoryDesc
        Tofwerk shared memory descriptor
    ptr: TSharedMemoryPointer
        Tofwerk sared memory pointer
    tps_info: list
        List of strings, TPS parameter names
    speci: int
        Integer index of the most recent spectrum
    shutdown_event: Event
        The thread runs until shutdown_event is set
    barrier: Barrier
        Barrier instance to synchronize KSignalProcessor threads
    spec_queue: Queue
        Queue to put raw spectra into
    speci_queue: Queue
        Queue to put spectrum index into
    avg_queue: Queue
        Queue to put averaged spectra into
    sum_queue: Queue
        Queue to put sum spectrum into
    stick_queue: Queue
        Queue to put unit mass resolution spectra into
    avg_stick_queue: Queue
        Queue to put averaged unit mass resolution spectra into
    tps_queue: Queue
        Queue to put TPS parameter data into
    avg_step: int
        Averaging step for data to put into avg_queue
    spec_avger: KAccumulator
        KAccumulator instance to average raw spectra
    stick_avg_step: int
        Averaging step for UMR data to put into avg_stick_queue
    stick_avger: KAccumulator
        KAccumulator instance to average UMR spectra
    acq_active: Event
        Event instance which is set when acquiring data, otherwise cleared
    acquired_file: str
        Full file path of the currently (or most recently) acquired file
    acquisition_time: list
        List of float timestamps for the acquired data (seconds from start)
    acq_length: float
        Length of the current (or most recent) acquisition in seconds
    acq_t_res: float
        Time resolution of the current (or most recent) acquisition in seconds
    nspectra: int
        Number of spectra expected in the current (or most recent) acquisition
    mz: list
        m/z vector (read from TofDaq Recorder)
    """

    def __init__(
            self,
            barrier=Barrier(1),
            shutdown_event=Event(),
            speci_queue=SubscriptableQueue(),
            spec_queue=SubscriptableQueue(),
            avg_queue=SubscriptableQueue(),
            sum_queue=SubscriptableQueue(),
            stick_queue=SubscriptableQueue(),
            avg_stick_queue=SubscriptableQueue(),
            tps_queue=SubscriptableQueue(),
            avg_step=None,
            stick_avg_step=None):
        """Initialize self

        For initialization, TofDaq Recorder needs to be running.

        Parameters
        ----------
        barrier: Barrier, optional
            Barrier instance to synchronize KSignalProcessor threads,
            by default Barrier(1)
        shutdown_event : Event, optional
            The thread runs until shutdown_event is set,
            by default Event()
        speci_queue : Queue, optional
            Queue to put spectrum index into,
            by default SubscriptableQueue()
        spec_queue : Queue, optional
            Queue to put raw spectra into,
            by default SubscriptableQueue()
        avg_queue : Queue, optional
            Queue to put averaged spectra into,
            by default SubscriptableQueue()
        sum_queue : Queue, optional
            Queue to put sum spectrum into,
            by default SubscriptableQueue()
        stick_queue : Queue, optional
            Queue to put unit mass resolution spectra into,
            by default SubscriptableQueue()
        avg_stick_queue : Queue, optional
            Queue to put averaged unit mass resolution spectra into,
            by default SubscriptableQueue()
        tps_queue : Queue, optional
            Queue to put TPS parameter data into,
            by default SubscriptableQueue()
        avg_step : int, optional
            Averaging step for data to put into avg_queue,
            by default None (no averaging)
        stick_avg_step : int, optional
            Averaging step for UMR data to put into avg_stick_queue,
            by default None (no averaging)

        Raises
        ------
        Exception
            Raises an exception if fetching shared memory descriptor fails.
        """

        Thread.__init__(self)
        self.desc = TSharedMemoryDesc() # TW shared memory descriptor
        # Check if TofDaq Recorder is running
        if not TwTofDaqRunning():
            raise Exception("TofDaq Recorder not running.")
        # Try to fetch shared memory descriptor and pointer
        ret = TwGetDescriptor(self.desc)
        if ret == 4:
            KInstrument.__init__(self, self.desc)
            self.ptr = TSharedMemoryPointer() # Shared memory pointer
            self.tps_info = self.get_tps_info() # Get TPS parameter info
        else:
            raise Exception("Trying to fetch shared memory " +
                            "descriptor failed: %s" %TwRetVal(ret).name)
        self.speci = -1
        # Initialize parameters
        # Synchronization primitives
        self.shutdown_event = shutdown_event
        # Synchronization between signal processing threads
        self.barrier = barrier
        # Queues where to feed data
        self.spec_queue = spec_queue # Queue to put the raw 
        self.speci_queue = speci_queue # Queue to put spec index
        self.avg_queue = avg_queue # Queue to put accumulated spectra
        self.sum_queue = sum_queue # Queue to put sum of all spectra so far
        self.stick_queue = stick_queue # Queue to put stick spectra
        self.avg_stick_queue = avg_stick_queue  # Queue to put accumulated stick spectra
        self.tps_queue = tps_queue # Queue to put TPS parameters
        # self.tps_info = [] # List of TPS parameter descriptions
        # Averaging parameters
        self.avg_step = avg_step # Number of spectra to accumulate before putting to avg_queue
        self.stick_avg_step = stick_avg_step # Number of stick spectra to accumulate before putting to avg_queue
        if self.avg_queue is not None and self.avg_step is not None:
            # Instantiate accumulator for raw data
            self.spec_avger = KAccumulator(self.avg_step)
        else:
            self.spec_avger = None
        if self.avg_stick_queue is not None and self.stick_avg_step is not None:
            # Instantiate accumulator for stick data
            self.stick_avger = KAccumulator(self.stick_avg_step)
        else:
            self.stick_avger = None
        # Acquisition parameters (reset after each acquisition)
        self.acq_active = Event() # Flag telling whether there is active acquisition running atm
        self.acquired_file = None # Name of acquired file
        self.acquisition_time = [] # List of timestamps for the acquired datapoints
        self.acq_length = None
        self.acq_t_res = None
        self.nspectra = None # Number of spectra (datapoints) expected in the acquisition
        self.mz = []
        self.mz_par = np.zeros((16,), dtype='<f8')
        self.mz_mode = 0
        self.update_mz() # Calculate mass axis

    def run(self):
        """Main loop

        First wait for acquisition to start, then fetch data from the
        TW shared memory and feed to queues. When TwWaitForNewData times
        out, wait for 'barrier'. Then again wait for new acquisition. 
        Runs until 'shutdown_event' is set.

        Raises
        ------
        Exception
            Raises an exception if TwWaitForNewData returns other than
            TwSuccess or TwTimeOut
        """

        print('KAcquisition running')
        self.barrier.wait()
        while not self.shutdown_event.is_set():
            self.speci = -1
            ibuf = -1
            iwrite = 0
            timeout = 5000 # ms
            while not self.shutdown_event.is_set():
                # Wait for acquisition
                if TwDaqActive():
                    break
                sleep(.1)
            while not self.shutdown_event.is_set():
                # Acquisition loop
                if self.speci == -1:
                    print('KAcquisition active')
                ret = TwWaitForNewData(timeout, self.desc, self.ptr, True)
                if ret==4:
                    # New data available
                    if self.speci == -1:
                        # First round
                        # Reset
                        self.reset()
                        # Set timeout
                        timeout = int( self.acq_t_res * 2000 ) + 1000 # ms
                    self.acq_active.set() # Set flag
                    # Index of current spectrum
                    new_ibuf = self.desc.iBuf
                    new_iwrite = self.desc.iWrite
                    new_i = new_iwrite * self.desc.nbrBufs + new_ibuf
                    # Check for skipped spectra
                    while new_ibuf - ibuf > 1:
                        if new_iwrite > iwrite:
                            # Can't go back to previous write
                            break
                        ibuf += 1
                        self.speci = iwrite * self.desc.nbrBufs + ibuf
                        self.get_and_feed_data(self.speci, ibuf, iwrite)
                    # Back to normal track
                    ibuf = new_ibuf
                    iwrite = new_iwrite
                    print(new_i)
                    if new_i - self.speci == 0:
                        # No new data, acquisition has ended
                        continue
                    elif (new_i - self.speci != 1 and
                          self.speci < self.nspectra-1):
                        for i in range(self.speci+1, new_i):
                            print('Warning: skipped a spec with index %s' %i)
                    self.speci = new_i
                    self.get_and_feed_data(self.speci, ibuf, iwrite)
                elif ret==8:
                    print('KAcquisition timed out')
                    # Timed out
                    # Flush accumulators
                    if (self.spec_avger is not None and
                        self.spec_avger.flush()
                        ):
                        # Make sure not negative
                        avgi = max(self.speci + 1 - self.avg_step, 0)
                        self.avg_queue.put( (avgi, self.spec_avger.sum_spec) )
                    if (self.stick_avger is not None and
                        self.stick_avger.flush()
                        ):
                        # Make sure not negative
                        avgi = max(self.speci + 1 - self.stick_avg_step, 0)
                        self.avg_stick_queue.put(
                            (avgi, self.stick_avger.sum_spec)
                            )
                    # Acquisition finished
                    if self.speci > -1:
                        self.acq_active.clear()
                        # Feed Nones to all queues
                        put_all_queues(self, None)
                        # If not in triggered mode, wait until active flag is reset
                        if TwGetDaqParameter(b'DioStartEnable').decode() != 'true':
                            # TODO: if above is for legacy compatibility only
                            while TwDaqActive():
                                sleep(.1)
                        # Wait for other threads to finish
                        print('KAcquisition waiting for other threads')
                        self.barrier.wait()
                    print('KAcquisition ready')
                    break
                else:
                    raise Exception('Unexpected return value: %s'
                                    %TwRetVal(ret).name
                                    )
        print('KAcquisition exiting')
        # Close queues
        close_all_queues(self)
    
    def shutdown(self):
        """Method for setting the 'shutdown_event', causing exit from
        the main loop.
        """

        self.shutdown_event.set()
    
    def update_desc(self):
        """Update the shared memory descriptor.

        Raises
        ------
        Exception
            Exception is raised if the descriptor could not be updated.
        """
        
        ret = TwGetDescriptor(self.desc)
        if ret != 4:
            raise Exception('Trying to update shared memory descriptor ' +
                            'failed: %s' %TwRetVal(ret).name)
    
    def update_mz(self):
        """Calculate m/z vector for the current mass calibration parameters.
        """

        if ( (np.array(self.mz_par) != np.array(self.desc.p)).any() or
             self.mz_mode != self.desc.massCalibMode or 
             len(self.mz) != self.desc.nbrSamples
             ):
            # Update
            self.mz_par = self.desc.p
            self.mz_mode = self.desc.massCalibMode
            self.mz = self.sno2mz(
                range(0, self.desc.nbrSamples)
                )
    
    def reset(self):
        """ Reset acquisition parameters in preparation for new acquisition

        Updates the following attributes:
            desc
            tps_info
            acquired_file
            acquisition_time
            acq_length
            acq_t_res
            nspectra
            spec_avger
            stick_avger
        """

        self.update_desc()
        self.update_mz()
        self.tps_info = self.get_tps_info()
        self.acquired_file = self.desc.currentDataFileName.decode()
        self.acquisition_time = []
        # Reset accumulators in case averaging steps have been changed
        if self.avg_queue is not None and self.avg_step is not None:
            # Instantiate accumulator for raw data
            self.spec_avger = KAccumulator(self.avg_step)
        else:
            self.spec_avger = None
        if self.avg_stick_queue is not None and self.stick_avg_step is not None:
            # Instantiate accumulator for stick data
            self.stick_avger = KAccumulator(self.stick_avg_step)
        else:
            self.stick_avger = None
        # Calculate expected acquisition length
        tof_period_ns = self.desc.tofPeriod
        if tof_period_ns < 1:
            tof_period_ns *= 1e9
        nbr_wf = self.desc.nbrWaveforms
        self.acq_t_res = tof_period_ns * 1e-9 * nbr_wf
        nbr_bufs = self.desc.nbrBufs
        nbr_writes = self.desc.nbrWrites
        # Expected length of the acquisition
        self.nspectra = nbr_writes * nbr_bufs
        self.acq_length = (self.nspectra-1) * self.acq_t_res
        
    def get_and_feed_data(self, speci, ibuf, iwrite):
        """ Read data from the shared memory and put to queues
        """

        # Time
        ti = np.zeros((1,))
        TwGetBufTimeFromShMem(ti, ibuf, iwrite)
        while len(self.acquisition_time) < speci:
            # Missed spectra
            self.acquisition_time.append(None)
        self.acquisition_time.append(ti.item())
        # Spectrum
        if self.spec_queue:
            spec = np.zeros((self.desc.nbrSamples, ), dtype=np.float32)
            TwGetTofSpectrumFromShMem(spec, 0, 0, ibuf, True)  # mV/ext
            self.spec_queue.put((speci, float(ti), spec))
        # Sum spectrum
        if self.sum_queue:
            sumspec = np.zeros((self.desc.nbrSamples, ), dtype=np.double)
            TwGetSumSpectrumFromShMem(sumspec, True)
            self.sum_queue.put(sumspec)
        # Stick spectrum
        if self.stick_queue:
            stickspec = np.zeros((self.desc.nbrPeaks + 1, ),
                                 dtype=np.float32)
            TwGetStickSpectrumFromShMem(stickspec, None, 0, 0, ibuf)
            # Move indices by one so that index==amu
            stickspec = np.roll(stickspec, 1)
            self.stick_queue.put((speci, stickspec))
        # TPS data
        if self.tps_queue:
            nel = np.zeros((1,), dtype=int)
            TwQueryRegUserDataSize(b'/TPS2', nel)
            data = np.zeros((nel.item(), 1),
                            dtype=np.double)
            if TwReadRegUserData(b'/TPS2', nel.item(), data) == 4:
                self.tps_queue.put((speci, data.astype(np.float32).reshape(-1)))
        # Average if requested
        if self.avg_queue and self.avg_step:
            if not self.spec_queue:
                spec = np.zeros((self.desc.nbrSamples, ),
                                dtype=np.float32
                                )
                TwGetTofSpectrumFromShMem(
                    spec, 0, 0, ibuf, True)  # mV/ext
            if self.spec_avger.accumulate(speci, spec):
                avgi = speci + 1 - self.avg_step
                self.avg_queue.put((avgi, self.spec_avger.sum_spec)
                                   )
        # Average sticks if requested
        if self.avg_stick_queue and self.stick_avg_step:
            if not self.stick_queue:
                stickspec = np.zeros((self.desc.nbrPeaks + 1, ),
                                 dtype=np.float32
                                 )
                TwGetStickSpectrumFromShMem(stickspec, None, 0, 0, ibuf)
                # Move indices by one so that index==amu
                stickspec = np.roll(stickspec, 1)
            if self.stick_avger.accumulate(speci, stickspec):
                sticki = speci + 1 - self.stick_avg_step
                self.avg_stick_queue.put(
                               (sticki,
                               self.stick_avger.sum_spec)
                               )
        # Spectrum index
        if self.speci_queue:
            self.speci_queue.put(speci)
    
    def get_tps_info(self):
        """Get TPS parameter descriptions from TofDaq Recorder

        Returns
        -------
        [type]
            [description]
        """

        info = []
        # Query number of parameters
        nel = np.zeros((1,), dtype=int)
        if TwQueryRegUserDataSize(b'/TPS2', nel) == 4:
            # Parameter description buffer
            infobuf = create_string_buffer(b'', 256 * nel.item())
            if TwGetRegUserDataDesc(b'/TPS2', nel, infobuf) == 4:
                # Parameter descriptions retrieved succesfully
                # Convert char array to bytes array
                info = np.asarray(infobuf).view('S256').ravel()
                info = info.tolist() # Array to list
                info = [ i.decode('unicode_escape') for i in info ] # bytes to str
        return info

    def get_save_path(self):
        """[summary]

        Returns
        -------
        [type]
            [description]
        """

        return TwGetDaqParameter(b'DataPath')
    
    def set_save_path(self, new_path):
        """[summary]

        Parameters
        ----------
        new_path : [type]
            [description]

        Raises
        ------
        Exception
            [description]
        Exception
            [description]
        """

        if not os.path.isdir(new_path):
            raise Exception('Invalid path: %s' %new_path)
        else:
            ret = TwSetDaqParameter(b'DataPath', new_path)
            # If not TwSuccess
            if ret != 4:
                raise Exception('Failed to set write path: %s' %TwRetVal(ret).name)

    def write_attribute(self, location, name, value):
        """[summary]

        Parameters
        ----------
        location : [type]
            [description]
        name : [type]
            [description]
        value : [type]
            [description]

        Raises
        ------
        Exception
            [description]
        """

        # Make sure location is in correct format
        if isinstance(location, str):
            # Convert str to bytes
            location = location.encode()
        # Make sure attribute name is in correct format
        if isinstance(name, str):
            # Convert str to bytes
            name = name.encode()
        # Choose the right function based on attribute type
        if isinstance(value, str):
            # Convert str to bytes
            value = value.encode()
        if isinstance(value, bytes):
            ret = TwAddAttributeString(location, name, value)
        elif isinstance(value, float):
            ret = TwAddAttributeDouble(location, name, value)
        elif isinstance(value, int):
            ret = TwAddAttributeInt(location, name, value)
        else:
            ret = 11
        # If not TwSuccess
        if ret != 4:
            raise Exception('Failed to write attribute: %s' %TwRetVal(ret).name)


class Acquisition(Thread, KInstrument):
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
        print("Acquisition initializing")
        Thread.__init__(self)

        # Initialize TW API related structures 'desc' and 'ptr'
        if not TwTofDaqRunning():
            raise Exception("TofDaq Recorder not running.")
        self.desc = TSharedMemoryDesc() # TW shared memory descriptor
        ret = TwGetDescriptor(self.desc)
        if ret == 4:
            # Success
            # Initialize karsatof.kinstrument.KInstrument
            KInstrument.__init__(self, self.desc)
            self.ptr = TSharedMemoryPointer() # TW shared memory pointer
        else:
            # Failed
            raise Exception("Trying to fetch shared memory " +
                            "descriptor failed: %s" %TwRetVal(ret).name)
        # Parameters
        self.timeout = 500 # [ms], timeout for TwWaitForNewData
        # Synchronization primitives
        self.shutdown_event = Event()   # Set to break out from main loop
        self.active = Event()           # Acquisition active event
        self.spec_queue = Queue()       # Signal output queue
        self.tps_queue = Queue()        # TPS output queue
        # Per acquisition attributes
        self.filename = None            # Filename base from TW h5 file
        self.interval = None            # Acquisition interval [s]
        self.length = None              # Acquisition length [s]
        self.progress = 0               # Acquisition progress [%]
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
        curr_filename = self._strip_filepath( self.desc.currentDataFileName.decode() )
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

    def _get_and_feed_data(self):
        """Read data from the shared memory and put to queues
        """
        # Get timestamp from TW shared memory
        ti = np.zeros((1,))
        TwGetBufTimeFromShMem(ti, self.desc.iBuf, self.desc.iWrite)

        # == Get and feed mass spectrum data ==
        # Get most recent spectrum from TW shared memory
        spec = np.zeros((self.desc.nbrSamples, ), dtype=np.float32)
        ret = TwGetTofSpectrumFromShMem(spec, 0, 0, self.desc.iBuf, True)  # [mV/ext]
        if ret == 4: # Success
            # Combine data for output
            spec_data = {
                    'filename': self.filename, # Current file basename
                    'i': self.speci, # Current spectrum integer index
                    't': float(ti), # Timestamp [s]
                    'spec': spec.tobytes() # Serialized spectrum [float32]
                    }
            # Feed
            self.spec_queue.put(spec_data)

        # == Get and feed TPS data ==
        # Query data size
        nel = np.zeros((1,), dtype=int)
        TwQueryRegUserDataSize(b'/TPS2', nel)
        # Get most recent TPS data from TW shared memory
        data = np.zeros((nel.item(), 1),
                        dtype=np.double
                        )
        ret = TwReadRegUserData(b'/TPS2', nel.item(), data)
        if ret == 4: # Success
            # Combine data for output
            tps_data = {
                'filename': self.filename,          # Current file basename
                'i': self.speci,                    # Current spectrum integer index
                't': float(ti),                     # Timestamp [s]
                'data': data.astype(np.float32  # convert to float32
                                ).reshape(-1    # reshape to (-1,)
                                ).tobytes(      # serialize
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
        if TwQueryRegUserDataSize(b'/TPS2', nel) == 4:
            # Parameter description buffer
            infobuf = create_string_buffer(b'', 256 * nel.item())
            if TwGetRegUserDataDesc(b'/TPS2', nel, infobuf) == 4:
                # Parameter descriptions retrieved succesfully
                # Convert char array to bytes array
                info = np.asarray(infobuf).view('S256').ravel()
                info = info.tolist() # Array to list
                info = [ i.decode('unicode_escape') for i in info ] # bytes to str
        return info

    def _reset(self):
        """Reset per acquisition attributes
        """
        self.filename = None
        self.progress = 0
        self.speci = -1

    def _strip_filepath(self, h5_filepath):
        """Strip path and file extension

        Parameters
        ----------
        h5_filepath : str
            Full file path

        Returns
        -------
        str
            Base filename
        """
        return os.path.splitext(os.path.basename(h5_filepath))[0]

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
            self.filename = self._strip_filepath(h5_filepath)
            tof_period_s = self.desc.tofPeriod
            if tof_period_s > 1:
                # Convert [ns]->[s] if needed
                tof_period_s *= 1e-9 
            self.interval = tof_period_s * self.desc.nbrWaveforms # [s]
            self.length = (self.desc.nbrWrites * self.desc.nbrBufs) * self.interval # [s]
            print("Acquisition started: %s" %self.filename)
            # Check again for new data
            state = self._check()
        if state == 1:
            # New data
            self.speci = (self.desc.iWrite * self.desc.nbrBufs) + self.desc.iBuf
            print(self.speci)
            self._get_and_feed_data()
            # Acquisition progress
            n = self.desc.nbrWrites * self.desc.nbrBufs # Total number of spectra
            self.progress = ((self.speci+1) / n) * 100. # [%]
         
    def run(self):
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'. 
        Loop until 'self.shutdown_event' is set.
        """

        print("Acquisition running")
        timeout_counter = 0
        # Main loop
        while not self.shutdown_event.is_set():
            ret = TwWaitForNewData(self.timeout,
                                   self.desc,
                                   self.ptr,
                                   True
                                   )
            # Timeout
            if ret == 8:
                timeout_counter += 1 # Increment counter
                if self.active.is_set():
                    if not TwDaqActive():
                        # No active acquisition
                        # Acquisition has ended
                        pass
                    else:
                        # Acquition active, but 'TwWaitForNewData' timed out

                        # Here we may end up from three scenarios:
                        # 1) Acquisition active, but interval is longer than 'self.timeout'
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
                    print("Acquisition finished")
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
                print("Unexpected return value: %s" %TwRetVal(ret).name)
        # Out of main loop
        print('Acquisition exiting')
        self.shutdown()
        
    def shutdown(self):
        """Shutdown procedure
        """
        self.shutdown_event.set()
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()
        self.tps_queue.close()
        self.tps_queue.join_thread()

    def start_acquisition(self):
        """Start acquisition by calling TW API
        """
        TwStartAcquisition()

    def stop_acquisition(self):
        """Stop acquisition by calling TW API
        """
        TwStopAcquisition()


class h5Streamer(Acquisition):
    def __init__(self):
        """Initialize self

        Inherits 'karsatof.kinstrument.KInstrument' which provides some
        convenience methods for instrument functions.

        Raises
        ------
        Exception
            Exception is raised if fetching 'TwH5Desc' fails for some reason.
        """
        print("h5Streamer initializing")
        Thread.__init__(self)

        # Initialize with empty TW h5 descriptor
        self.desc = TwH5Desc()
        KInstrument.__init__(self, self.desc)

        # Synchronization primitives
        # Streamer specific
        self.file_queue = Queue()       # Queue for files to stream
        self.tick = Event()             # Event to control data feed
        # Common with Acquisition
        self.shutdown_event = Event()   # Set to break out from main loop
        self.active = Event()           # Acquisition active event
        self.spec_queue = Queue()       # Signal output queue
        self.tps_queue = Queue()        # TPS output queue
        # Per acquisition attributes
        self.filename = None            # Filename base from TW h5 file
        self.interval = None            # Acquisition interval [s]
        self.length = None              # Acquisition length [s]
        self.progress = 0               # Acquisition progress [%]
        self.speci = -1                 # Index of last received spectrum,
                                        # -1 when there is no active acquisition

    def _get_and_feed_data(self):
        """Read data from the h5 and put to queues
        """
        # Get timestamp from TW h5
        ti = np.zeros((1,))
        TwGetBufTimeFromH5(self.desc.currentDataFileName,
                           ti,
                           self.desc.iBuf,
                           self.desc.iWrite
                           )
        # == Get and feed mass spectrum data ==
        # Get most recent spectrum from TW shared memory
        spec = np.zeros((self.desc.nbrSamples, ), dtype=np.float32)
        ret = TwGetTofSpectrumFromH5(
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
                    'filename': self.filename, # Current file basename
                    'i': self.speci, # Current spectrum integer index
                    't': float(ti), # Timestamp [s]
                    'spec': spec.tobytes() # Serialized spectrum [float32]
                    }
            # Feed
            self.spec_queue.put(spec_data)

        # == Get and feed TPS data ==
        # Query data size
        nel = np.zeros((1,), dtype=int)
        TwGetRegUserDataFromH5(
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
        ret = TwGetRegUserDataFromH5(
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
        TwGetRegUserDataFromH5(
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

        TwGetRegUserDataFromH5(
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
            True if ticked, False if shutdown
        """
        while not self.shutdown_event.is_set():
            if self.spec_queue.qsize() or self.tps_queue.qsize():
                # Still something in queue
                sleep(.1)
            else:
                # Queues empty
                return True
        # Shutdown
        return False

    def run(self):
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'. 
        Loop until 'self.shutdown_event' is set.
        """

        print("h5Streamer running")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_to_stream = self.file_queue.get(timeout=.1)
                # Update TW h5 descriptor
                ret = TwGetH5Descriptor(file_to_stream.encode(), self.desc)
                # Add fields to comply with TW shared memory descriptor
                self.desc.currentDataFileName = file_to_stream.encode()
                self.desc.iBuf = 0
                self.desc.iWrite = 0
                self._update_mz()
            except Empty:
                continue
            # Start streaming
            # Update self and feed data into queue
            self._update()
            # Set active flag 
            self.active.set()
            # Loop through the file and feed to queues
            # Loop through all 'writes'
            for iwrite in range(self.desc.nbrWrites):
                # Check for shutdown flag
                if self.shutdown_event.is_set():
                    break
                # Increment write index
                self.desc.iWrite = iwrite
                # Loop through all 'bufs' per 'write'
                for ibuf in range(self.desc.nbrBufs):
                    # Increment buf index
                    self.desc.iBuf = ibuf
                    # Update self and feed data into queue
                    self._update()
                    # Wait for queues to be empty
                    if self._wait_for_queues():
                        # Empty
                        continue
                    else:
                        # Shutdown
                        break
            # Out of stream loop
            self.active.clear()
            self._finalize()
            print("h5Stream finished")
        # Out of main loop
        print('h5Streamer exiting')
        self.shutdown()

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

    def _update_mz(self):
        # Get mz axis from file
        mz = np.zeros((self.desc.nbrSamples,), dtype=np.double)
        TwGetSpecXaxisFromH5(self.desc.currentDataFileName,
                             mz,
                             1,
                             None,
                             0,
                             0
                             )
        self._mz = mz.astype(np.float32)


class KStreamer(Thread, KInstrument):
    """Thread to stream data from h5 file for offline processing,
    simulating KAcquisition.

    Attributes
    ----------
    desc: TSharedMemoryDesc
        Tofwerk shared memory descriptor
    ptr: TSharedMemoryPointer
        Tofwerk sared memory pointer
    tps_info: list
        List of strings, TPS parameter names
    speci: int
        Integer index of the most recent spectrum
    shutdown_event: Event
        The thread runs until shutdown_event is set
    barrier: Barrier
        Barrier instance to synchronize KSignalProcessor threads
    spec_queue: Queue
        Queue to put raw spectra into
    speci_queue: Queue
        Queue to put spectrum index into
    avg_queue: Queue
        Queue to put averaged spectra into
    sum_queue: Queue
        Queue to put sum spectrum into
    stick_queue: Queue
        Queue to put unit mass resolution spectra into
    avg_stick_queue: Queue
        Queue to put averaged unit mass resolution spectra into
    tps_queue: Queue
        Queue to put TPS parameter data into
    avg_step: int
        Averaging step for data to put into avg_queue
    spec_avger: KAccumulator
        KAccumulator instance to average raw spectra
    stick_avg_step: int
        Averaging step for UMR data to put into avg_stick_queue
    stick_avger: KAccumulator
        KAccumulator instance to average UMR spectra
    acq_active: Event
        Event instance which is set when acquiring data, otherwise cleared
    acquired_file: str
        Full file path of the currently (or most recently) acquired file
    acquisition_time: list
        List of float timestamps for the acquired data (seconds from start)
    acq_length: float
        Length of the current (or most recent) acquisition in seconds
    acq_t_res: float
        Time resolution of the current (or most recent) acquisition in seconds
    nspectra: int
        Number of spectra expected in the current (or most recent) acquisition
    mz: list
        m/z vector (read from TofDaq Recorder)
    file_to_stream : str
        Full file path to the file to be streamed
    """

    def __init__(
            self,
            file_queue=Queue(),
            barrier=Barrier(1),
            shutdown_event=Event(),
            speci_queue=SubscriptableQueue(),
            spec_queue=SubscriptableQueue(),
            avg_queue=SubscriptableQueue(),
            sum_queue=SubscriptableQueue(),
            stick_queue=SubscriptableQueue(),
            avg_stick_queue=SubscriptableQueue(),
            tps_queue=SubscriptableQueue(),
            avg_step=None,
            stick_avg_step=None):
        """Initialize self

        Parameters
        ----------
        
        file_queue : Queue, optional
            Queue for the files to stream, by default Queue.
        barrier: Barrier, optional
            Barrier instance to synchronize KSignalProcessor threads,
            by default Barrier(1)
        shutdown_event : Event, optional
            The thread runs until shutdown_event is set,
            by default Event()
        speci_queue : Queue, optional
            Queue to put spectrum index into,
            by default SubscriptableQueue()
        spec_queue : Queue, optional
            Queue to put raw spectra into,
            by default SubscriptableQueue()
        avg_queue : Queue, optional
            Queue to put averaged spectra into,
            by default SubscriptableQueue()
        sum_queue : Queue, optional
            Queue to put sum spectrum into,
            by default SubscriptableQueue()
        stick_queue : Queue, optional
            Queue to put unit mass resolution spectra into,
            by default SubscriptableQueue()
        avg_stick_queue : Queue, optional
            Queue to put averaged unit mass resolution spectra into,
            by default SubscriptableQueue()
        tps_queue : Queue, optional
            Queue to put TPS parameter data into,
            by default SubscriptableQueue()
        avg_step : int, optional
            Averaging step for data to put into avg_queue,
            by default None (no averaging)
        stick_avg_step : int, optional
            Averaging step for UMR data to put into avg_stick_queue,
            by default None (no averaging)

        Raises
        ------
        Exception
            Raises an exception if fetching file descriptor fails
        """

        Thread.__init__(self)
        self.desc = TwH5Desc() # TW file descriptor
        KInstrument.__init__(self, self.desc)

        self.file_queue = file_queue
        self.speci = -1
        # Initialize parameters
        # Synchronization primitives
        self.shutdown_event = shutdown_event
        # Synchronization between signal processing threads
        self.barrier = barrier
        # Queues where to feed data
        self.spec_queue = spec_queue # Queue to put the raw 
        self.speci_queue = speci_queue # Queue to put spec index
        self.avg_queue = avg_queue # Queue to put accumulated spectra
        self.sum_queue = sum_queue # Queue to put sum of all spectra so far
        self.stick_queue = stick_queue # Queue to put stick spectra
        self.avg_stick_queue = avg_stick_queue  # Queue to put accumulated stick spectra
        self.tps_queue = tps_queue # Queue to put TPS parameters
        # self.tps_info = [] # List of TPS parameter descriptions
        # Averaging parameters
        self.avg_step = avg_step # Number of spectra to accumulate before putting to avg_queue
        self.stick_avg_step = stick_avg_step # Number of stick spectra to accumulate before putting to avg_queue
        if self.avg_queue is not None and self.avg_step is not None:
            # Instantiate accumulator for raw data
            self.spec_avger = KAccumulator(self.avg_step)
        else:
            self.spec_avger = None
        if self.avg_stick_queue is not None and self.stick_avg_step is not None:
            # Instantiate accumulator for stick data
            self.stick_avger = KAccumulator(self.stick_avg_step)
        else:
            self.stick_avger = None
        # Acquisition parameters (reset after each acquisition)
        self.acq_active = Event() # Flag telling whether there is active acquisition running atm
        self.acquired_file = None # Name of acquired file
        self.acquisition_time = [] # List of timestamps for the acquired datapoints
        self.acq_length = None
        self.acq_t_res = None
        self.nspectra = None # Number of spectra (datapoints) expected in the acquisition
        self.mz = []
        self.mz_par = np.zeros((16,), dtype='<f8')
        self.mz_mode = 0
        self.update_mz() # Calculate mass axis
        self.ke = None

    def run(self):
        """Main loop

        Instantiate KEvent for the file to be streamed, load data from
        file and put to queues. When all data is put to queues, wait for
        the barrier and then exit.

        """

        print("KStreamer running")
        while not self.shutdown_event.is_set():
            try:
                file_to_stream = self.file_queue.get(timeout=.1)
                print("KStreamer got from queue: %s" %file_to_stream)
            except Empty:
                continue
            try:
                self.reset(file_to_stream)
            except Exception as e:
                print("Streaming failed: %s" % e)
                continue
            print("Streaming %s" %file_to_stream)
            self.speci = -1 # Index of the most recent spectrum
            self.acq_active.set() # Set acquisition flag
            # Loop through the data and feed to queues
            for iwrite in range(self.desc.nbrWrites): # Loop through all 'writes'
                for ibuf in range(self.desc.nbrBufs): # Loop through all 'bufs' per 'write'
                    self.speci += 1 # Update spec index
                    print(self.speci)
                    self.get_and_feed_data(self.speci, ibuf, iwrite)
                    # Delay
                    sleep(.5)
                    # Check for shutdown flag
                    if self.shutdown_event.is_set():
                        break
                # Check for shutdown flag
                if self.shutdown_event.is_set():
                        break
            # End of file
            self.acq_active.clear() # Update flag
            put_all_queues(self, None) # Put 'Break'
            # Wait for all threads to finish
            print("KStreamer waiting for other threads")
            self.barrier.wait()
            # Exit
            print("KStreamer ready")
            
        print("KStreamer exiting")

    def shutdown(self):
        """Method for setting the 'shutdown_event', causing exit from
        the main loop.
        """

        self.shutdown_event.set()

    def update_desc(self, file_to_stream):
        """Update the H5 descriptor.

        Raises
        ------
        Exception
            Exception is raised if the descriptor could not be updated.
        """

        ret = TwGetH5Descriptor(file_to_stream.encode(), self.desc)
        if ret != 4:
            raise Exception('Failed to get file descriptor.')

    def update_mz(self):
        """Calculate m/z vector for the current mass calibration parameters.
        """

        if ( (np.array(self.mz_par) != np.array(self.desc.p)).any() or
             self.mz_mode != self.desc.massCalibMode or 
             len(self.mz) != self.desc.nbrSamples
             ):
            # Update
            self.mz_par = self.desc.p
            self.mz_mode = self.desc.massCalibMode
            self.mz = self.sno2mz(
                range(0, self.desc.nbrSamples)
                )

    def get_tps_info(self):
        _, info = self.ke.load_tps_data()
        return info

    def reset(self, file_to_stream):
        """ Reset acquisition parameters in preparation for new acquisition

        Updates the following attributes:
            desc
            tps_info
            acquired_file
            acquisition_time
            acq_length
            acq_t_res
            nspectra
            spec_avger
            stick_avger
        """

        self.ke = KEvent(file_to_stream) # KEvent instance for the file to be streamed
        self.update_desc(file_to_stream)
        self.update_mz()
        self.tps_info = self.get_tps_info()
        self.acquired_file = file_to_stream
        self.acquisition_time = []
        # Reset accumulators in case averaging steps have been changed
        if self.avg_queue is not None and self.avg_step is not None:
            # Instantiate accumulator for raw data
            self.spec_avger = KAccumulator(self.avg_step)
        else:
            self.spec_avger = None
        if self.avg_stick_queue is not None and self.stick_avg_step is not None:
            # Instantiate accumulator for stick data
            self.stick_avger = KAccumulator(self.stick_avg_step)
        else:
            self.stick_avger = None
        # Calculate expected acquisition length
        tof_period_ns = self.desc.tofPeriod
        if tof_period_ns < 1:
            tof_period_ns *= 1e9
        nbr_wf = self.desc.nbrWaveforms
        self.acq_t_res = tof_period_ns * 1e-9 * nbr_wf #TODO: Different results in new TOFs!
        nbr_bufs = self.desc.nbrBufs
        nbr_writes = self.desc.nbrWrites
        # Expected length of the acquisition
        self.nspectra = nbr_writes * nbr_bufs
        #self.acq_length = (self.nspectra-1) * self.acq_t_res
        self.acq_length = self.ke.t[-1] #TODO: Temporary fix. See note above

    def get_and_feed_data(self, speci, ibuf, iwrite):
        """ Read data from the shared memory and put to queues
        """
        bi0 = bi1 = ibuf
        wi0 = wi1 = iwrite
        ind = (bi0, bi1, wi0, wi1)        
        # Time
        ti = self.ke.t[speci]
        while len(self.acquisition_time) < speci:
            # Missed spectra
            self.acquisition_time.append(None)
        self.acquisition_time.append(ti)
        # Spectrum
        if self.spec_queue:
            spec = self.ke.load_spec(ind) # Load spectrum from file
            self.spec_queue.put((speci, ti, spec))
        # Sum spectrum
        if self.sum_queue:
            sum_ind = (0, bi1, 0, wi1)
            sumspec = self.ke.load_spec(sum_ind) # Load spectrum from file
            self.sum_queue.put(sumspec)
        # Stick spectrum
        if self.stick_queue:
            stickspec = self.ke.load_stickspec(ind) # Load sticks from file
            self.stick_queue.put((speci, stickspec))
        # TPS data
        if self.tps_queue:
            data, info = self.ke.load_tps_data(ind)
            self.tps_info = info
            self.tps_queue.put((speci, data.astype(np.float32).reshape(-1)))
        # Average if requested
        if self.avg_queue and self.avg_step:
            if not self.spec_queue:
                spec = self.ke.load_spec(ind) # Load spectrum from file
            if self.spec_avger.accumulate(speci, spec):
                avgi = speci + 1 - self.avg_step
                self.avg_queue.put((avgi, self.spec_avger.sum_spec)
                                   )
        # Average sticks if requested
        if self.avg_stick_queue and self.stick_avg_step:
            if not self.stick_queue:
                stickspec = self.ke.load_stickspec(ind) # Load sticks from file
            if self.stick_avger.accumulate(speci, stickspec):
                sticki = speci + 1 - self.stick_avg_step
                self.avg_stick_queue.put(
                               (sticki,
                               self.stick_avger.sum_spec)
                               )
        # Spectrum index
        if self.speci_queue:
            self.speci_queue.put(speci)


def put_all_queues(kgenerator, val):
    """Helper function to put the same value to all kgenerator queues

    Parameters
    ----------
    kgenerator : KAcquisition or KStreamer
        KAcquisition or KStreamer instance
    val : any
        Data to put to the queues
    """

    if kgenerator.speci_queue is not None:
        kgenerator.speci_queue.put(val)
    if kgenerator.spec_queue is not None:
        kgenerator.spec_queue.put(val)
    if kgenerator.sum_queue is not None:
        kgenerator.sum_queue.put(val)
    if kgenerator.stick_queue is not None:
        kgenerator.stick_queue.put(val)
    if kgenerator.tps_queue is not None:
        kgenerator.tps_queue.put(val)
    if kgenerator.avg_queue is not None:
        kgenerator.avg_queue.put(val)
    if kgenerator.avg_stick_queue is not None:
        kgenerator.avg_stick_queue.put(val)
        
def close_all_queues(kgenerator):
    """Helper function to close all kgenerator queues

    Parameters
    ----------
    kgenerator : KAcquisition or KStreamer
        KAcquisition or KStreamer instance
    """

    if kgenerator.speci_queue is not None:
        kgenerator.speci_queue.close()
        kgenerator.speci_queue.join_thread()
    if kgenerator.spec_queue is not None:
        kgenerator.spec_queue.close()
        kgenerator.spec_queue.join_thread()
    if kgenerator.sum_queue is not None:
        kgenerator.sum_queue.close()
        kgenerator.sum_queue.join_thread()
    if kgenerator.stick_queue is not None:
        kgenerator.stick_queue.close()
        kgenerator.stick_queue.join_thread()
    if kgenerator.tps_queue is not None:
        kgenerator.tps_queue.close()
        kgenerator.tps_queue.join_thread()
    if kgenerator.avg_queue is not None:
        kgenerator.avg_queue.close()
        kgenerator.avg_queue.join_thread()
    if kgenerator.avg_stick_queue is not None:
        kgenerator.avg_stick_queue.close()
        kgenerator.avg_stick_queue.join_thread()
