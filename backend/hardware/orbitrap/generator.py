# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""

import os
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from time import sleep

import numpy as np
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
    def __init__(self, file_queue=Queue(), shutdown_event=Event(), lock=Lock()):
        print("RawStreamer initializing")
        Thread.__init__(self)
        # Parameters
        self._mz_grid = None
        # Thermo Fischer RawFileReaderFactory
        self.raw = None
        # Synchronization primitives
        self.file_queue = file_queue  # Queue for files to stream
        self.shutdown_event = shutdown_event  # Set to break out from main loop
        self.lock = lock
        self.cancel_event = Event()  # Set to cancel current stream
        self.active = Event()  # Acquisition active event
        self.spec_queue = Queue()  # Signal output queue
        # Per acquisition attributes
        self.speci = -1  # Index of last received spectrum,
        # -1 when there is no active acquisition

    @property
    def filename(self) -> str:
        """Base filename of the raw file currently being streamed

        :return: Base filename
        :rtype: str
        """
        return strip_filepath(self.raw.FileName) if self.raw else None

    @property
    def interval(self) -> float:
        """Mean measurement interval in seconds, i.e. length of one spectrum in the sample

        :return: Measurement interval [s]
        :rtype: float
        """
        return (
            self.length / self.raw.RunHeaderEx.LastSpectrum if self.raw else None
        )  # [s]

    @property
    def length(self) -> float:
        """Length of the sample file in seconds

        :return: Sample length [s]
        :rtype: float
        """
        return self.raw.RunHeaderEx.EndTime * 60.0 if self.raw else None  # [s]

    @property
    def mz(self) -> np.array:
        """Precomputed m/z grid of the sample file

        :return: m/z coordinate grid
        :rtype: np.array
        """
        if self.raw:
            return self._mz_grid.astype(np.float32)

    @property
    def progress(self) -> float:
        """Streaming progress in percent

        :return: Prgress [%]
        :rtype: float
        """
        if not self.active.is_set():
            return 100
        return ((self.speci + 1) / self.raw.RunHeaderEx.LastSpectrum) * 100.0  # [%]

    def _get_and_feed_data(self, scan_no: int):
        """Read data from the RAW file and put to queues"""
        # == Get and feed mass spectrum data ==
        # Get the scan statistics from the RAW file for this scan number
        with self.lock:
            scan_stats = self.raw.GetScanStatsForScanNumber(scan_no)
        # Get timestamp from scan stats
        ti = scan_stats.StartTime * 60.0  # [s]
        # Get polarity from scan stats
        polarity = scan_stats.ScanType.split(" ")[1]
        with self.lock:
            scan = self.raw.GetSegmentedScanFromScanNumber(scan_no, scan_stats)
        # Map .NET arrays into numpy arrays
        mz = net2np_array(scan.Positions).astype(np.float32)
        spec = net2np_array(scan.Intensities).astype(np.float32)
        # Round mz values based on the mz precision
        mz, spec = self._set_mz_precision(mz, spec)
        # Combine data for output
        spec_data = {
            "filename": self.filename,  # Current file basename
            "i": self.speci,  # Current spectrum integer index
            "t": float(ti),  # Timestamp [s]
            "period": self.interval,  # Collection period [s]
            "mz": mz.tobytes(),  # Serialized mass axis [float32]
            "spec": spec.tobytes(),  # Serialized spectrum [float32]
            "polarity": polarity,  # Polarity, '-' or '+'
        }
        # Feed
        self.spec_queue.put(spec_data)

    def _feed_coordinates(self):
        if self._has_negative_scans():
            coordinates = {
                "filename": self.filename,
                "i": -1,
                "mz": self.mz.tobytes(),
                "t_range": [0, self.length],
                "polarity": "-",
            }
            self.spec_queue.put(coordinates)
        if self._has_positive_scans():
            coordinates = {
                "filename": self.filename,
                "i": -1,
                "mz": self.mz.tobytes(),
                "t_range": [0, self.length],
                "polarity": "+",
            }
            self.spec_queue.put(coordinates)

    def _finalize(self):
        """Finalize acquisition"""
        if not self.cancel_event.is_set():
            # Feed poison pill
            if self._has_negative_scans():
                self.spec_queue.put(
                    {
                        "filename": self.filename,
                        "i": None,
                        "source_filepath": self.raw.FileName,
                        "polarity": "-",
                    }
                )
            if self._has_positive_scans():
                self.spec_queue.put(
                    {
                        "filename": self.filename,
                        "i": None,
                        "source_filepath": self.raw.FileName,
                        "polarity": "+",
                    }
                )
        # Reset self
        self.speci = -1
        self._mz_grid = None
        with self.lock:
            self.raw.Dispose()
        self.active.clear()
        self.cancel_event.clear()

    def _has_negative_scans(self) -> bool:
        """Does the current raw file contain scans in negative polarity

        :return: Has negative sans
        :rtype: bool
        """
        polarity_filter = self.raw.GetFilterFromString("-")
        scan_enumerator = self.raw.GetFilteredScanEnumerator(
            polarity_filter
        ).GetEnumerator()
        return scan_enumerator.MoveNext()

    def _has_positive_scans(self) -> bool:
        """Does the current raw file contain scans in negative polarity

        :return: Has positive sans
        :rtype: bool
        """
        polarity_filter = self.raw.GetFilterFromString("+")
        scan_enumerator = self.raw.GetFilteredScanEnumerator(
            polarity_filter
        ).GetEnumerator()
        return scan_enumerator.MoveNext()

    def _precompute_grid(self, points_per_fwhm=4, resolution_coeff=1.715e6):
        """Precompute mz grid based on the resolution function: `resolution_coeff / sqrt(mz)`

        :param points_per_fwhm: number of data points per FWHM of the peak, defaults to 4
        :type points_per_fwhm: float, optional
        :param resolution_coeff: Resolution function coefficient, defaults to 1.715e6
        :type resolution_coeff: float, optional
        :return: computed mz grid
        :rtype: numpy.ndarray
        """
        # Get mz range from the file
        mz_min = self.raw.RunHeaderEx.LowMass
        mz_max = self.raw.RunHeaderEx.HighMass
        # Check if values are correct else return None
        if not (10 < mz_min < mz_max < np.finfo(np.float64).max):
            return None
        # Expand mz range
        mz_min -= 10
        mz_max += 10
        # Set starting mz value
        mz = mz_min
        # Initialize list with mz grid
        mz_grid = [mz_min]
        while mz < mz_max:
            resolution = resolution_coeff / np.sqrt(mz)
            fwhm = mz / resolution
            # Step to the next point of the grid
            step = fwhm / points_per_fwhm
            # Add a new point to the mz grid
            mz += step
            mz_grid.append(mz)

        return np.array(mz_grid, dtype=np.float32)

    def _set_mz_precision(self, mz, spec):
        """Rounds mz values to the nearest values of the precomputed mz grid

        :param mz: mz scale
        :type mz: array-like
        :param spec: measured counts
        :type spec: array-like
        :return: a tuple of updated mz scale and counts
        :rtype: tuple
        """
        # Find the indices of the closest values from self._mz_grid
        closest_indices = np.searchsorted(self._mz_grid, mz.astype(np.float32))
        # Filter out of bounds indices
        closest_indices[np.where(closest_indices == len(self._mz_grid))] = (
            len(self._mz_grid) - 1
        )
        # Get the closest mz values from self._mz_grid
        mz_closest = self._mz_grid[closest_indices]
        # Get unique mz values and their corresponding indices
        unique_mz, inverse_indices = np.unique(mz_closest, return_inverse=True)
        # Accumulate the intensities for each unique mz value
        unique_mz_intensities = np.bincount(inverse_indices, weights=spec)

        return unique_mz.astype(np.float32), unique_mz_intensities.astype(np.float32)

    def _wait_for_queues(self):
        """Wait for tick event to be set before continuing streaming

        Returns
        -------
        bool
            True if ticked, False if shutdown
        """
        while not (self.shutdown_event.is_set() or self.cancel_event.is_set()):
            if not self.spec_queue.qsize():
                # Queues empty
                return True
            else:
                # Wait for data to be consumed from queues
                sleep(0.01)
        # Shutdown or cancel
        return False

    def run(self):
        print("RawStreamer running")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_to_stream = self.file_queue.get(timeout=0.1)
                # Initialize Raw file reader
                try:
                    with self.lock:
                        self.raw = ThermoBusiness.RawFileReaderFactory.ReadFile(
                            file_to_stream
                        )
                        i_type = self.raw.GetInstrumentType(0)
                        self.raw.SelectInstrument(i_type, 1)
                except Exception as e:
                    print(f"Error reading file {file_to_stream}: {e}")
                    continue
            except Empty:
                # No file to stream, keep waiting
                continue

            # Precompute mz grid
            self._mz_grid = self._precompute_grid()
            # Check if precomputation
            if self._mz_grid is None:
                print(
                    f"Failed to compute mz grid. File {self.filename} is likely damaged."
                )
                # Close raw file
                with self.lock:
                    self.raw.Dispose()
                continue
            # Start streaming
            # Feed coordinates
            self._feed_coordinates()
            print(f"Acquisition started: {self.filename}")
            # Set active flag
            self.active.set()
            # Loop through the file and feed to queues
            all_scans = range(
                self.raw.RunHeaderEx.FirstSpectrum,
                self.raw.RunHeaderEx.LastSpectrum + 1,
            )
            for scan_no in all_scans:
                print(scan_no)
                self.speci = scan_no - 1
                # Update self and feed data into queue
                self._get_and_feed_data(scan_no)
                # Wait for queues to be empty
                if self._wait_for_queues():
                    # Empty
                    continue
                else:
                    # Done
                    break
            # Out of stream loop
            self._finalize()
            print("RawStream finished")
        # Out of main loop
        print("RawStreamer exiting")
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure"""
        self.shutdown_event.set()
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()

    def start_stream(self, filename: str):
        """Method to call externally, to start streaming a file

        Alternative to directly putting a file into `self.file_queue`

        :param filename: Full path to the file to be streamed
        :type filename: str
        :raises ValueError: If file is not found
        """
        if os.path.isfile(filename):
            self.file_queue.put(filename)
        else:
            raise ValueError(f"File does not exist: {filename}")

    def stop_stream(self):
        """Stop stream before complete

        TODO: To be implemented
        """
        raise NotImplementedError
