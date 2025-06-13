# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
from multiprocessing import Event, Queue
from threading import Thread
from time import sleep

import numpy as np

from mascope_tofwerk.runtime import runtime


from mascope_tofwerk.lib.TofDaq import (
    TSharedMemoryDesc,
    TSharedMemoryPointer,
    TwCleanupDll,
    TwDaqActive,
    TwGetDaqParameterBool,
    TwGetDescriptor,
    TwRetVal,
    TwTofDaqRunning,
    TwWaitForNewData,
)


def strip_filepath(filepath: str) -> str:
    """Strip path and extension from filepath

    :param filepath: full file path
    :type filepath: str
    :return: base filename without extension
    :rtype: str
    """
    return os.path.splitext(os.path.basename(filepath))[0]


class TofDaqStreamer(Thread):
    """Thread interfacing with TofDaq Recorder"""

    def __init__(self, shutdown_event=Event()):
        """TofDaqStreamer class to stream data from TofDaq Recorder"""
        super().__init__()

        # Synchronization primitives
        self.active = Event()
        self.shutdown_event = shutdown_event
        self.notification_queue = Queue()

        # Initialize TW API related structures 'desc' and 'ptr'
        runtime.logger.info("TofDaqStreamer initializing...")
        count = 0
        warning_timeout = 10
        while not TwTofDaqRunning() and not shutdown_event.is_set():
            if count % warning_timeout == 0:
                runtime.logger.warning("TofDaq Recorder not running, please launch it!")
            count += 1
            sleep(1)
        self.desc = TSharedMemoryDesc()  # TW shared memory descriptor
        ret = TwGetDescriptor(self.desc)
        if ret == 4:
            # Success
            self.ptr = TSharedMemoryPointer()  # TW shared memory pointer
        else:
            # Failed
            self.shutdown_event.set()
            raise RuntimeError(
                (
                    "Trying to fetch shared memory ",
                    f"descriptor failed with error: {TwRetVal(ret).name}",
                )
            )

        # Acquisition state
        self._prev_rec_running = False
        self._prev_daq_active = False
        self._my_bufs_processed = None
        self._buf_time = np.zeros((1,), dtype=np.float64)
        self._base_filename = None
        self._filepath = None
        self._polarity = None

    @property
    def progress(self) -> float:
        """Acquisition progress in percentage

        :return: percentage of acquisition progress
        :rtype: float
        """
        if not self.active.is_set():
            return 100
        return self._my_bufs_processed / (self.desc.nbrBufs * self.desc.nbrWrites) * 100

    def run(self):
        """Main loop for the TofDaqStreamer"""
        while not self.shutdown_event.is_set():
            # Check TofDaq Recorder status
            is_recorder_running = TwTofDaqRunning()
            is_acquisition_active = TwDaqActive() if is_recorder_running else False

            if is_recorder_running:
                # TofDaq Recorder is running
                if not self._prev_rec_running:
                    # Recorder running first time
                    self.on_recorder_started()

                if is_acquisition_active:
                    # Acquisition is active
                    self.on_daq_active()
                else:
                    # Acquisition is not active
                    if self._prev_daq_active:
                        # Acquisition ended since the last iteration
                        self.on_daq_ended()
                        self._prev_daq_active = False
                    sleep(1.0)
            else:
                # TofDaq Recorder is not running
                if self._prev_rec_running:
                    self.on_recorder_closed()
                    self._prev_rec_running = False
                # Wait a bit to avoid busy loop
                sleep(1.0)

            self._prev_rec_running = is_recorder_running
            self._prev_daq_active = is_acquisition_active

    def on_recorder_started(self) -> None:
        """Callback triggered when TofDaq Recorder is started"""
        runtime.logger.info("TofDaq Recorder was launched")

    def on_first_daq_active(self) -> None:
        """Callback triggered when new acquisition has started

        This is called only once per acquisition. `on_daq_active` will also be called after
        """
        TwGetDescriptor(self.desc)  # just update descriptor without waiting for data
        self._my_bufs_processed = 0
        self._filepath = self.desc.currentDataFileName.decode()
        self._base_filename = strip_filepath(self._filepath)
        self._polarity = "-" if TwGetDaqParameterBool(b"NegativeIonMode") else "+"
        self.active.set()
        runtime.logger.info(f"Acquisition of file {self._base_filename} started")
        self.notification_queue.put(
            {
                "filename": self._base_filename,
                "polarity": self._polarity,
                "i": -1,
            }
        )

    def on_daq_active(self) -> None:
        """Acquisition active callback

        This is called on each iteration of the main loop when acquisition is active
        """
        ret = TwWaitForNewData(1000, self.desc, self.ptr, True)
        if ret == 4:
            runtime.logger.debug("Received new data")
            if self._my_bufs_processed is None:
                # Daq active first time
                self.on_first_daq_active()
            if self.desc.totalBufsProcessed > 0:
                # Process new data
                self._my_bufs_processed = self.desc.totalBufsProcessed
                self.notification_queue.put(
                    {
                        "filename": self._base_filename,
                        "i": self._my_bufs_processed,
                    }
                )
        elif ret == 8:
            # No new data within timeout
            runtime.logger.debug("Timeout while waiting for new data")
        else:
            runtime.logger.warning(f"Unexpected return value: {TwRetVal(ret).name}")

    def on_daq_ended(self):
        """Acquisition ended callback

        Reset acquisition related variables and clear active flag
        """

        runtime.logger.info("Acquisition ended")
        self.notification_queue.put(
            {
                "filename": self._base_filename,
                "i": None,
                "source_filepath": self._filepath,
            }
        )
        # Clear active flag
        self.active.clear()
        # Reset self
        self._my_bufs_processed = None
        self._base_filename = None
        self._filepath = None
        self._polarity = None
        TwCleanupDll()

    def on_recorder_closed(self):
        """TofDaq Recorder closed callback"""
        runtime.logger.info("TofDaq Recorder closed, please restart!")
