# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
from ctypes import create_string_buffer
from multiprocessing import Event
from time import sleep

import numpy as np

from .generator import BaseGenerator
from .lib.TofDaq import (
    TSharedMemoryDesc,
    TSharedMemoryPointer,
    TwAddLogEntry,
    TwCleanupDll,
    TwDaqActive,
    TwGetBufTimeFromShMem,
    TwGetDescriptor,
    TwGetRegUserDataDesc,
    TwGetSpecXaxisFromShMem,
    TwGetTofSpectrumFromShMem,
    TwQueryRegUserDataSize,
    TwReadRegUserData,
    TwRetVal,
    TwStartAcquisition,
    TwStopAcquisition,
    TwTofDaqRunning,
    TwWaitForNewData,
)


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


class TofDaqStreamer(BaseGenerator):
    def __init__(self, shutdown_event=Event()):
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
        BaseGenerator.__init__(self)

        # Initialize TW API related structures 'desc' and 'ptr'
        while not TwTofDaqRunning() and not shutdown_event.is_set():
            print("TofDaq Recorder not running.")
            sleep(1)
        self.desc = TSharedMemoryDesc()  # TW shared memory descriptor
        ret = TwGetDescriptor(self.desc)
        if ret == 4:
            # Success
            self.ptr = TSharedMemoryPointer()  # TW shared memory pointer
        else:
            # Failed
            raise Exception(
                "Trying to fetch shared memory "
                + "descriptor failed: %s" % TwRetVal(ret).name
            )
        # Parameters
        self.timeout = 500  # [ms], timeout for TwWaitForNewData
        # Synchronization primitives
        self.shutdown_event = shutdown_event  # Set to break out from main loop

    @property
    def mz(self):
        # Get mz axis from file
        mz = np.zeros((self.desc.nbrSamples,), dtype=np.double)
        TwGetSpecXaxisFromShMem(mz, 1, None)
        return mz.astype(np.float32)

    @property
    def mz_calibration(self):
        return {
            "mode": self.desc.massCalibMode,
            "par": self.desc.p[: self.desc.nbrMassCalibParams],
        }

    def _get_and_feed_data(self):
        """Read data from the shared memory and put to queues"""
        # Get timestamp from TW shared memory
        ti = np.zeros((1,))
        TwGetBufTimeFromShMem(ti, self.desc.iBuf, self.desc.iWrite)

        # == Get and feed mass spectrum data ==
        # Get most recent spectrum from TW shared memory
        spec = np.zeros((self.desc.nbrSamples,), dtype=np.float32)
        ret = TwGetTofSpectrumFromShMem(spec, 0, 0, self.desc.iBuf, True)  # [mV/ext]
        if ret == 4:  # Success
            # Convert spec from [mV/ext] -> [ions/sec]
            spec *= self.conversion_coefficient
            # Combine data for output
            spec_data = {
                "filename": self.filename,  # Current file basename
                "i": self.speci,  # Current spectrum integer index
                "t": float(ti),  # Timestamp [s]
                "period": self.interval,  # Collection period [s]
                "spec": spec.tobytes(),  # Serialized spectrum [float32]
            }
            # Feed
            self.spec_queue.put(spec_data)

        # # == Get and feed TPS data ==
        # # Query data size
        # nel = np.zeros((1,), dtype=int)
        # TwQueryRegUserDataSize(b'/TPS2', nel)
        # # Get most recent TPS data from TW shared memory
        # data = np.zeros((nel.item(), 1),
        #                 dtype=np.double
        #                 )
        # ret = TwReadRegUserData(b'/TPS2', nel.item(), data)
        # if ret == 4: # Success
        #     # Combine data for output
        #     tps_data = {
        #         'filename': self.filename,          # Current file basename
        #         'i': self.speci,                    # Current spectrum integer index
        #         't': float(ti),                     # Timestamp [s]
        #         'period': self.interval,            # Collection period [s]
        #         'data': data.astype(np.float32 # convert to float32
        #                         ).reshape(-1   # reshape to (-1,)
        #                         ).tobytes(     # serialize
        #                         )                   # Serialized TPS data [float32]
        #         }
        #     # Feed
        #     self.tps_queue.put(tps_data)

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
        if TwQueryRegUserDataSize(b"/TPS2", nel) == 4:
            # Parameter description buffer
            infobuf = create_string_buffer(b"", 256 * nel.item())
            if TwGetRegUserDataDesc(b"/TPS2", nel, infobuf) == 4:
                # Parameter descriptions retrieved succesfully
                # Convert char array to bytes array
                info = np.asarray(infobuf).view("S256").ravel()
                info = info.tolist()  # Array to list
                info = [i.decode("unicode_escape") for i in info]  # bytes to str
        return info

    def add_log_entry(self, text, timestamp=0):
        if timestamp:
            # Convert seconds to filetime
            acquisition_time_zero = self.desc.timeZero
            timestamp = int(acquisition_time_zero + (timestamp * 1e7))
        if not isinstance(text, bytes):
            # Convert string to bytes
            text = text.encode()
        TwAddLogEntry(text, timestamp)

    def run(self):
        prevRecRunning = False
        prevDaqActive = False
        myTotalBufsProcessed = 0
        bufTime = np.zeros((1,), dtype=np.float64)

        def RecorderStarted():
            print("recorder started")

        def FirstDaqActive():
            nonlocal myTotalBufsProcessed
            TwGetDescriptor(
                self.desc
            )  # just update descriptor without waiting for data
            myTotalBufsProcessed = 0
            print("acquisition started")

            # custom
            # custom ends

        def DaqActive():
            nonlocal bufTime, myTotalBufsProcessed
            ret = TwWaitForNewData(1000, self.desc, self.ptr, True)
            if ret == 4:
                if not self.active.is_set():
                    # New file, update attributes
                    h5_filepath = (
                        self.desc.currentDataFileName.decode()
                    )  # TW h5 file full path
                    self.filename = strip_filepath(h5_filepath)
                    tof_period_s = self.desc.tofPeriod
                    if tof_period_s > 1:
                        # Convert [ns]->[s] if needed
                        tof_period_s *= 1e-9
                    self.sample_interval = self.desc.sampleInterval * 1e9  # [s]->[ns]
                    self.single_ion_signal = self.desc.singleIonSignal
                    self.tof_frequency = 1.0 / tof_period_s
                    self.interval = tof_period_s * self.desc.nbrWaveforms  # [s]
                    self.length = (
                        self.desc.nbrWrites * self.desc.nbrBufs
                    ) * self.interval  # [s]
                    # Feed coordinates
                    self._feed_coordinates()
                    print("TofDaqStreamer started: %s" % self.filename)
                    self.active.set()
                if self.desc.totalBufsProcessed > 0:
                    for b in range(myTotalBufsProcessed, self.desc.totalBufsProcessed):
                        bufIndex = b % self.desc.nbrBufs
                        writeIndex = b // self.desc.nbrBufs
                        # get timestamp
                        TwGetBufTimeFromShMem(bufTime, bufIndex, writeIndex)

                        # custom code goes here
                        # New data
                        new_speci = (
                            self.desc.iWrite * self.desc.nbrBufs
                        ) + self.desc.iBuf
                        if new_speci - self.speci > 1:
                            print("Warning: Skipped a spec!")
                        self.speci = new_speci
                        print(self.speci)
                        self._get_and_feed_data()
                        # custom code ends here
                    myTotalBufsProcessed = self.desc.totalBufsProcessed
            elif ret == 8:
                pass
            else:
                print("Unexpected return value: %s" % ret)

        def DaqEnded():
            print("acquisition stopped/ended")
            # custom
            # Clear active flag
            self.active.clear()
            # Reset self
            self._finalize()
            TwCleanupDll()
            # custom ends

        def RecorderClosed():
            print("recorder closed")

        while not self.shutdown_event.is_set():
            isRecorderRunning = TwTofDaqRunning()
            isAcquisitionActive = TwDaqActive() if isRecorderRunning else False

            if isRecorderRunning:
                if not prevRecRunning:
                    RecorderStarted()
                    pass
                if isAcquisitionActive:
                    if not prevDaqActive:
                        FirstDaqActive()
                    DaqActive()
                else:
                    if prevDaqActive:
                        DaqEnded()
                        prevDaqActive = False
                    sleep(1.0)
            else:
                if prevRecRunning:
                    RecorderClosed()
                    prevRecRunning = False
                sleep(1.0)

            prevRecRunning = isRecorderRunning
            prevDaqActive = isAcquisitionActive
        # custom
        self.shutdown()
        # custom ends

    def run_deprecated(self):
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'.
        Loop until 'self.shutdown_event' is set.
        """

        print("TofDaqStreamer running")
        timeout_counter = 0
        # Main loop
        while not self.shutdown_event.is_set():
            ret = TwWaitForNewData(self.timeout, self.desc, self.ptr, True)
            # Timeout
            if ret == 8:
                timeout_counter += 1  # Increment counter
                if self.active.is_set():
                    if not TwDaqActive():
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
                        tot_wait = timeout_counter * self.timeout * 1e-3  # [s]
                        # Calculate acquisition interval
                        acquisition_interval = (
                            self.desc.tofPeriod * 1e-9
                        ) * self.desc.nbrWaveforms  # [s]
                        # Check if waited long enough already
                        wait_seconds = acquisition_interval + 1  # Wait one extra second
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
                print("Unexpected return value: %s" % TwRetVal(ret).name)
                sleep(1)
        # Out of main loop
        print("TofDaqStreamer exiting")
        self.shutdown()

    def start_acquisition(self):
        """Start acquisition by calling TW API"""
        TwStartAcquisition()

    def stop_acquisition(self):
        """Stop acquisition by calling TW API"""
        TwStopAcquisition()

    def stop_stream(self):
        """Stop stream before complete"""
        self.stop_acquisition()
