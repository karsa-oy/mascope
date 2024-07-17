# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
import h5py
from ctypes import create_string_buffer
from multiprocessing import Event, Lock, Queue
from queue import Empty
from time import sleep

import numpy as np

import mascope_runtime as runtime

from .generator import BaseGenerator
from .instrument import KInstrument
from .lib.TwH5 import (
    TwCloseH5,
    TwGetBufTimeFromH5,
    TwGetH5Descriptor,
    TwGetRegUserDataFromH5,
    TwGetSpecXaxisFromH5,
    TwGetTofSpectrumFromH5,
    TwH5Desc,
)

logger = runtime.logger.service('hardware-lib')


class H5Streamer(BaseGenerator, KInstrument):
    def __init__(self, file_queue=Queue(), shutdown_event=Event(), lock=Lock()):
        """Initialize self

        Inherits 'karsatof.kinstrument.KInstrument' which provides some
        convenience methods for instrument functions.

        Raises
        ------
        Exception
            Exception is raised if fetching 'TwH5Desc' fails for some reason.
        """
        logger.info("H5Streamer initializing")
        BaseGenerator.__init__(self)

        # Initialize with empty TW h5 descriptor
        self.desc = TwH5Desc()
        KInstrument.__init__(self, self.desc)

        # Synchronization primitives
        # Streamer specific
        self.file_queue = file_queue  # Queue for files to stream
        self.cancel_event = Event()  # Set to cancel current stream
        self.shutdown_event = shutdown_event  # Set to break out from main loop
        self.lock = lock

    @property
    def mz(self):
        # Get mz axis from file
        mz = np.zeros((self.desc.nbrSamples,), dtype=np.double)
        with self.lock:
            TwGetSpecXaxisFromH5(self.desc.currentDataFileName, mz, 1, None, 0, 0)
        return mz.astype(np.float32)

    @property
    def mz_calibration(self):
        return {
            "mode": self.desc.massCalibMode,
            "par": self.desc.p[: self.desc.nbrCalibParams],
        }

    @property
    def polarity(self) -> str:
        """Ion polarity

        :return: Return either "+" or "-"
        :rtype: str
        """
        with h5py.File(self.desc.currentDataFileName, "r") as f:
            polarity_str = f.attrs["IonMode"].decode()
        return "-" if polarity_str == "negative" else "+"

    @property
    def tps_info(self):
        """List of TPS  names"""
        return self._get_tps_info()

    def _get_and_feed_data(self):
        """Read data from the h5 and put to queues"""
        # Get timestamp from TW h5
        ti = np.zeros((1,))
        with self.lock:
            TwGetBufTimeFromH5(
                self.desc.currentDataFileName, ti, self.desc.iBuf, self.desc.iWrite
            )
        # == Get and feed mass spectrum data ==
        # Get most recent spectrum from TW shared memory
        spec = np.zeros((self.desc.nbrSamples,), dtype=np.float32)
        with self.lock:
            ret = TwGetTofSpectrumFromH5(
                self.desc.currentDataFileName,
                spec,
                0,  # Segment start index
                0,  # Segment end index
                self.desc.iBuf,  # Buf start index
                self.desc.iBuf,  # Buf end index
                self.desc.iWrite,  # Write start index
                self.desc.iWrite,  # Write end index
                True,  # BufWrite linked
                True,  # Normalize to
            )  # [mV/ext]
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
                "polarity": self.polarity,  # Ion polarity
            }
            # Feed
            self.spec_queue.put(spec_data)

        # # == Get and feed TPS data ==
        # # Query data size
        # nel = np.zeros((1,), dtype=np.int32)
        # with self.lock:
        #     TwGetRegUserDataFromH5(
        #         self.desc.currentDataFileName,
        #         b'/TPS2',
        #         0,
        #         0,
        #         nel,
        #         None,
        #         None
        #     )
        # # Get TPS data from TW h5
        # data = np.zeros((nel.item(), ),
        #                 dtype=np.double
        #                 )
        # with self.lock:
        #     ret = TwGetRegUserDataFromH5(
        #         self.desc.currentDataFileName,
        #         b'/TPS2',
        #         self.desc.iBuf,
        #         self.desc.iWrite,
        #         nel,
        #         data,
        #         None # char buffer for info
        #     )
        # if ret == 4: # Success
        #     # Combine data for output
        #     tps_data = {
        #         'filename': self.filename,          # Current file basename
        #         'i': self.speci,                    # Current spectrum integer index
        #         't': float(ti),                     # Timestamp [s]
        #         'period': self.interval,            # Collection period [s]
        #         'data': data.astype(np.float32  # convert to float32
        #                         ).tobytes(      # serialize
        #                         )                   # Serialized TPS data [float32]
        #         }
        #     # Feed
        #     self.tps_queue.put(tps_data)

    def _get_tps_info(self):
        """Get TPS parameter descriptions from TW h5

        Returns
        -------
        list of str
            List of TPS parameter names
        """
        info = []
        # Query TPS data size
        nel = np.zeros((1,), dtype=np.int32)
        with self.lock:
            TwGetRegUserDataFromH5(
                self.desc.currentDataFileName, b"TPS2", 0, 0, nel, None, None
            )
        # Parameter description buffer
        infobuf = create_string_buffer(b"", 256 * nel.item())
        # Get TPS data from TW h5
        data = np.zeros((nel.item(),), dtype=np.double)
        with self.lock:
            TwGetRegUserDataFromH5(
                self.desc.currentDataFileName,
                b"TPS2",
                0,
                0,
                nel,
                data,  # data not used, but needs to be there
                infobuf,
            )
        # Parameter descriptions retrieved succesfully
        # Convert char array to bytes array
        info = np.asarray(infobuf).view("S256").ravel()
        info = info.tolist()  # Array to list
        info = [i.decode("unicode_escape") for i in info]  # bytes to str
        return info

    def _wait_for_queues(self):
        """Wait for tick event to be set before continuing streaming

        Returns
        -------
        bool
            True if ticked, False if cancel or shutdown
        """
        while not (self.shutdown_event.is_set() or self.cancel_event.is_set()):
            if not (self.spec_queue.qsize()):  # or self.tps_queue.qsize()):
                # Queues empty
                return True
            else:
                # Wait for data to be consumed from queues
                sleep(0.01)
        # Shutdown or cancel
        return False

    def run(self):
        """Main loop

        Poll TW API for new data at interval set by 'self.timeout'.
        Loop until 'self.shutdown_event' is set.
        """

        logger.info("H5Streamer running")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_to_stream = self.file_queue.get(timeout=0.1)
                file_to_stream = file_to_stream.encode()
                # Update TW h5 descriptor
                with self.lock:
                    ret = TwGetH5Descriptor(file_to_stream, self.desc)
                    if ret != 4:
                        logger.error("Failed to read file: %s" % ret)
                        TwCloseH5(file_to_stream)
                        continue
                    if not (self.desc.nbrBufs and self.desc.nbrWrites):
                        # Empty file, skip
                        logger.warning("Skipping empty file: %s" % file_to_stream)
                        TwCloseH5(file_to_stream)
                        continue
                # Test read to check for corrupt file
                with self.lock:
                    ret = TwGetTofSpectrumFromH5(
                        file_to_stream,
                        np.zeros((self.desc.nbrSamples,), dtype=np.float32),
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        True,
                        True,
                    )
                    if ret != 4:
                        logger.error("Failed to read file: %s" % ret)
                        TwCloseH5(file_to_stream)
                        continue
                # Add fields to comply with TW shared memory descriptor
                self.desc.currentDataFileName = file_to_stream
                self.desc.iBuf = 0
                self.desc.iWrite = 0
            except Empty:
                continue
            # Start streaming
            # Update self and feed data into queue
            self._update()
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
                    # Wait for queues to be empty
                    if self._wait_for_queues():
                        # Empty
                        continue
                    else:
                        # Done
                        break
                # Out of buf loop
                # Check for cancel and shutdown flags
                if self.cancel_event.is_set() or self.shutdown_event.is_set():
                    break
            # Out of write loop
            with self.lock:
                TwCloseH5(file_to_stream)
            self.active.clear()
            self._finalize()
            self.cancel_event.clear()
            logger.info("h5Stream finished")
        # Out of main loop
        logger.info("H5Streamer exiting")
        self.shutdown()

    def start_stream(self, filename):
        if os.path.isfile(filename):
            self.file_queue.put(filename)
        else:
            raise ValueError("File does not exist: %s" % filename)

    def stop_stream(self):
        """Stop stream before complete"""
        self.cancel_event.set()
