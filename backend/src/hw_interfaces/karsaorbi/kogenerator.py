# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
import numpy as np
from threading import current_thread
from time import sleep

from services.file_io import zarr_sdk
from .lib import Business as ThermoBusiness
from .koutil import net2np_array
from common.base_generator import BaseFileStreamer, PROGRESS_SHIFT


class RawStreamer(BaseFileStreamer):
    def __init__(self, client, mz_precision=4):
        self._mz_precision = mz_precision
        self.raw = None         # Thermo Fischer RawFileReaderFactory
        BaseFileStreamer.__init__(self, client)

    @property
    def mz(self):
        if self.raw:
            return np.array([self.raw.RunHeaderEx.LowMass,
                             self.raw.RunHeaderEx.HighMass],
                            dtype=np.float32
                            )

    def finalize(self):
        self.raw.Dispose()
        super().finalize()

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
        # Combine data for output and feed
        spec_data = {
                'filename': self.filename,  # Current file basename
                'i': self.speci,            # Current spectrum integer index
                't': float(ti),             # Timestamp [s]
                'period': self.interval,    # Collection period [s]
                'mz': mz.tobytes(),         # Serialized mass axis [float32]
                'spec': spec.tobytes()      # Serialized spectrum [float32]
                }
        self.feed_spec_data(spec_data)

        # Centroid data
        centroid_stream = self.raw.GetCentroidStream(scan_no, None)
        # Map .NET arrays into numpy arrays
        c_mz = net2np_array(centroid_stream.Masses).astype(np.float32)
        c_y = net2np_array(centroid_stream.Intensities).astype(np.float32)
        # Round mz values based on the mz precision
        c_mz, c_y = self._set_mz_precision(c_mz, c_y)
        # Combine data for output
        centroid_data = {
                'filename': self.filename,          # Current file basename
                'i': self.speci,                    # Current spectrum integer index
                't': float(ti),                     # Timestamp [s]
                'period': self.interval,            # Collection period [s]
                'peak_mz': c_mz.tobytes(),          # Serialized peak mass [float32]
                'peak_intensity': c_y.tobytes()     # Serialized peak intensity [float32]
                }
        self.feed_centroid_data(centroid_data)

    def _update(self, scan=None):
        """Update per acquisition attributes. If new data is available, feed into queues.
        """
        if scan is None:
            # New file
            self.length = self.raw.RunHeaderEx.EndTime * 60. # [s]
            self.interval = self.length / self.raw.RunHeaderEx.LastSpectrum # [s]
            self.feed_initial_data()
            if not self.wait_for_ack():     # wait for acq data initialization
                raise TimeoutError
            self.feed_centroid_info()
        else:
            # New data
            self.speci = scan - 1
            self.log(self.speci)
            # RawStreamer progress
            self.progress = round((scan / self.raw.RunHeaderEx.LastSpectrum) * 100., 2) # [%]
            self._get_and_feed_data()
            # allow PROGRESS_SHIFT to make it quicker
            if not self.wait_for_ack(progress_shift=PROGRESS_SHIFT):
                raise TimeoutError

    def run(self):
        # Main loop
        self.log(f"started {current_thread().name}")
        while not self.shutdown_event.is_set():
            self.rcontext, self.fdata = self.get_next_file_to_stream()
            if not self.fdata:
                sleep(.5)
                continue
            self.initialize()

            # Initialize Raw file reader
            full_fname = os.path.join(self.fdata['path'], self.filename)
            try:
                self.raw = ThermoBusiness.RawFileReaderFactory.ReadFile(full_fname)
                self.raw.SelectInstrument(0, 1)
            except Exception as e:
                self.log("Error reading file %s: %s" %(full_fname, e))
                continue

            # Start streaming
            self.log(f"started streaming {self.filename}")
            try:
                # Update self and feed data into queue
                self._update()
                # Loop through the file and feed to worker thread(s)
                scans = range(self.raw.RunHeaderEx.FirstSpectrum,
                            self.raw.RunHeaderEx.LastSpectrum + 1
                            )
                for scan in scans:
                    # Update self and feed data into queue
                    self._update(scan)
                    if self.cancel_event.is_set() or self.shutdown_event.is_set():
                        break
                # Out of stream loop
            except TimeoutError:
                self.log(f"Streaming {self.filename} interrupted due to timeout")
            except FileExistsError:     # only in import mode
                self.log(f"Importing {self.filename} cancelled: target exists")
            self.log(f"finished streaming {self.filename}")
            self.finalize()
            self.cancel_event.clear()
        # Out of main loop
        self.log(f"stopped {current_thread().name}")
        self.shutdown()

    #======== Orbitrap extension of a streamer service communication protocol ===============    
    def feed_centroid_info(self):
        sn_data = {
            'name': 'centroid_info',
            'value': {
                'filename': self.target_filename
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
        self.feed_notifications(gen_notifications, streamer_notifications)
        if self.client.target_data_pool_path:
            zarr_sdk.init_centroid_dataset(sn_data, self.item)   

    def feed_centroid_data(self, centroid_data):
        sn_data = {
            'name': 'acquired_centroid_data',
            'value': {
                **centroid_data,
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
        self.feed_notifications(gen_notifications, streamer_notifications)
        if self.client.target_data_pool_path:
            zarr_sdk.update_centroid_dataset(sn_data, self.item)
    # ===The service communication protocol implementation end=========================