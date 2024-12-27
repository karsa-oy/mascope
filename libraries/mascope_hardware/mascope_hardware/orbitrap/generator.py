# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""
# TODO Remove processed file from filestreams
# TODO more testing
# TODO get_sum_signal technically gives an error alphough works as it should. Better way to create sum_signal?

import os
from pathlib import Path
import shutil
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from time import sleep
from datetime import datetime, timezone
from numba import jit
import numpy as np

from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter
from ThermoFisher.CommonCore.Data.Business import Device

from mascope_hardware.runtime import hardware_runtime
from mascope_hardware.util import create_sample_file_db_record
from mascope_lib.file_func import (
    write_props,
    get_sum_signal,
    get_filestore_path,
    parse_path_from_item_filename,
)
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


# @jit
# def precompute_grid(mz_min, mz_max, points_per_fwhm=4, resolution_coeff=1.715e6):
#     """Precompute mz grid based on the resolution function: `resolution_coeff / sqrt(mz)`

#     :param mz_min: left m/z range border
#     :type mz_min: float
#     :param mz_max: right m/z range border
#     :type mz_max: float
#     :param points_per_fwhm: number of data points per FWHM of the peak, defaults to 4
#     :type points_per_fwhm: float, optional
#     :param resolution_coeff: Resolution function coefficient, defaults to 1.715e6
#     :type resolution_coeff: float, optional
#     :return: computed mz grid
#     :rtype: numpy.ndarray
#     """

#     # Check if values are correct else return None
#     if not 10 < mz_min < mz_max < np.finfo(np.float64).max:
#         return None
#     # Expand mz range
#     mz_min -= 10
#     mz_max += 10
#     # Set starting mz value
#     mz = mz_min
#     # Initialize list with mz grid
#     mz_grid = [mz_min]
#     while mz < mz_max:
#         resolution = resolution_coeff / np.sqrt(mz)
#         fwhm = mz / resolution
#         # Step to the next point of the grid
#         step = fwhm / points_per_fwhm
#         # Add a new point to the mz grid
#         mz += step
#         mz_grid.append(mz)

#     return np.array(mz_grid, dtype=np.float32)


class RawProcessor(Thread):
    """Reads raw file, creates

    :param Thread: _description_
    :type Thread: _type_
    """

    def __init__(self, file_queue=Queue(), shutdown_event=Event(), lock=Lock()):
        Thread.__init__(self)
        # Init logger
        self.log = hardware_runtime.logger.bind(key=self.name)
        self.log.info(f"Initializing raw file processor ({self.name})")
        # Opened raw file
        self.raw = None
        # Synchronization primitives
        self.file_queue = file_queue  # Queue for files to stream
        self.shutdown_event = shutdown_event  # Set to break out from main loop
        self.lock = lock
        self.cancel_event = Event()  # Set to cancel current stream
        self.active = Event()  # Acquisition active event
        # TODO probably to be removed
        self.spec_queue = Queue()  # Signal output queue

    @property
    def timestamp(self) -> datetime:
        """Timestamp in datetime format

        :return: Timestamp
        :rtype: datetime
        """
        if self.raw:
            dotnet_datetime = self.raw.CreationDate

            python_datetime = datetime(
                year=dotnet_datetime.Year,
                month=dotnet_datetime.Month,
                day=dotnet_datetime.Day,
                hour=dotnet_datetime.Hour,
                minute=dotnet_datetime.Minute,
                second=dotnet_datetime.Second,
            )
            return python_datetime

    @property
    def filename(self) -> str | None:
        """Base filename of the raw file currently being processed

        :return: Base filename
        :rtype: str
        """
        if self.raw:
            filename = strip_filepath(self.raw.FileName)
            timestamp = self.timestamp.strftime("%Y.%m.%d-%Hh%Mm%Ss")
            # Add timestamp to the filename
            return filename.replace("_", f"_{timestamp}_", 1)

    @property
    def method_file(self) -> str | None:
        """Instrument method file name from the raw file

        :return: Instrument method file name
        :rtype: str | None
        """
        if self.raw:
            method_file = self.raw.SampleInformation.InstrumentMethodFile
            return method_file if method_file else None
        return None

    @property
    def tic_neg(self) -> float | None:
        """Total ion current in negative polarity (TIC)

        :return: TIC
        :rtype: float | None
        """
        if self.raw:
            num_of_scans = self.raw.RunHeaderEx.SpectraCount
            tics = np.zeros(num_of_scans)
            for i in range(num_of_scans):
                if (
                    self.raw.GetFilterForScanNumber(i + 1).Polarity.ToString()
                    == "Negative"
                ):
                    tics[i] = self.raw.GetScanStatsForScanNumber(i + 1).TIC
            total_tic_neg = np.sum(tics)
            return total_tic_neg
        return None

    @property
    def tic_pos(self) -> float | None:
        """Total ion current in positive polarity (TIC)

        :return: TIC
        :rtype: float | None
        """
        if self.raw:
            num_of_scans = self.raw.RunHeaderEx.SpectraCount
            tics = np.zeros(num_of_scans)
            for i in range(num_of_scans):
                if (
                    self.raw.GetFilterForScanNumber(i + 1).Polarity.ToString()
                    == "Positive"
                ):
                    tics[i] = self.raw.GetScanStatsForScanNumber(i + 1).TIC
            total_tic_pos = np.sum(tics)
            return total_tic_pos
        return None

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
    def mz_range(self) -> list | None:
        """M/z range of the sample file

        :return: M/z range
        :rtype: list | None
        """
        if self.raw:
            return [self.raw.RunHeaderEx.LowMass, self.raw.RunHeaderEx.HighMass]
        return None

    def _finalize(self):
        """Finalize acquisition"""
        # Reset self
        self.active.clear()
        self.speci = -1
        with self.lock:
            self.raw.Dispose()
            self.raw = None
        self.cancel_event.clear()

    def _has_negative_scans(self) -> bool:
        """Does the current raw file contain scans in negative polarity

        :return: Has negative scans
        :rtype: bool
        """
        polarity_filter = self.raw.GetFilterFromString("-")
        scan_enumerator = self.raw.GetFilteredScanEnumerator(
            polarity_filter
        ).GetEnumerator()
        return scan_enumerator.MoveNext()

    def _has_positive_scans(self) -> bool:
        """Does the current raw file contain scans in negative polarity

        :return: Has positive scans
        :rtype: bool
        """
        polarity_filter = self.raw.GetFilterFromString("+")
        scan_enumerator = self.raw.GetFilteredScanEnumerator(
            polarity_filter
        ).GetEnumerator()
        return scan_enumerator.MoveNext()

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

    def _process_raw_file(self, sample_file_props: dict, raw_file_path: str):
        """Main function processing the raw files:
        1. Writes properties into the sample file
        2. Copies raw file into the sample file folder
        3. Creates sum_signal.zarr
        4. Creates a record in the database

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :param raw_file_path: Path to the target raw file
        :type raw_file_path: str
        """
        base_path = get_filestore_path()
        data_path = parse_path_from_item_filename(
            sample_file_props["filename"], base_path
        )
        # Ensure the sample file directory exists
        os.makedirs(data_path, exist_ok=True)

        # Write properties to the sample_file
        write_props(sample_file_props["filename"], sample_file_props)

        # Copy raw file to the sample_file folder
        data_raw_path = os.path.join(data_path, "data.raw")
        shutil.copy(raw_file_path, data_raw_path)

        # Write sum_signal to the sample_file
        get_sum_signal(sample_file_props["filename"])

        create_sample_file_db_record(sample_file_props)

        ## TODO add error handling for file processing

    def run(self):
        self.log.info(f"Running raw processor ({self.name})")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_to_process = self.file_queue.get(timeout=0.1)
                # Initialize Raw file reader
                try:
                    with self.lock:
                        self.raw = RawFileReaderAdapter.FileFactory(file_to_process)
                        self.raw.SelectInstrument(Device.MS, 1)
                        self.raw.IncludeReferenceAndExceptionData = True
                except Exception as e:
                    self.log.error(
                        f"Failed to read file {Path(file_to_process).name}: {e}"
                    )
                    continue
            except Empty:
                # No file to stream, keep waiting
                continue

            # Start processing
            self.log.info(f"Processing started: {Path(file_to_process).name}")
            # Set active flag
            self.active.set()

            # Get UTC offset
            now = datetime.now()
            utc_offset = (
                now - now.astimezone(timezone.utc).replace(tzinfo=None)
            ).seconds

            # Gather sample file data
            sample_file_props = {
                "length": self.length,
                "range": self.mz_range,
                "utc_offset": utc_offset,
                "method_file": self.method_file,
                "timestamp": self.timestamp.isoformat(),  # for DB record
                # streaming leftovers:
                "committed_length": self.length,
                # non-applicable for Orbi:
                "single_ion_signal": None,
                "sample_interval": None,
                "mz_calibration": None,
            }

            # Check if raw file contains negative polarity scans
            if self._has_negative_scans():
                # Add missing properties, negative polarity case
                sample_file_props["polarity"] = "-"
                sample_file_props["tic"] = self.tic_neg
                sample_file_props["filename"] = self.filename.replace(" ", "_") + "_-"

                # Create sample file with positive negative scans
                self._process_raw_file(sample_file_props, file_to_process)

            # Check if raw file contains positive polarity scans
            if self._has_positive_scans():
                # Add missing properties, positive polarity case
                sample_file_props["polarity"] = "+"
                sample_file_props["tic"] = self.tic_pos
                sample_file_props["filename"] = self.filename.replace(" ", "_") + "_+"

                # Create sample file with positive polarity scans
                self._process_raw_file(sample_file_props, file_to_process)

            # Out of stream loop
            self._finalize()
            self.log.info("Processing finished")
        # Out of main loop
        self.log.info(f"Exiting raw processor ({self.name})")
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure"""
        self.shutdown_event.set()
        # Close queues
        self.spec_queue.close()
        self.spec_queue.join_thread()

    def start_stream(self, filename: str):
        """Method to call externally, to start processing a file

        Alternative to directly putting a file into `self.file_queue`

        :param filename: Full path to the file to be streamed
        :type filename: str
        :raises ValueError: If file is not found
        """
        if os.path.isfile(filename):
            self.file_queue.put(filename)
        else:
            raise ValueError(f"File does not exist: {filename}")


# class RawStreamer(Thread):
#     def __init__(self, file_queue=Queue(), shutdown_event=Event(), lock=Lock()):
#         Thread.__init__(self)
# self.log = hardware_runtime.logger.bind(key=self.name)
# self.log.info(f"Initializing raw streamer ({self.name})")
# # Parameters
# self._mz_grid = None
# # Thermo Fischer RawFileReaderFactory
# self.raw = None
# # Synchronization primitives
# self.file_queue = file_queue  # Queue for files to stream
# self.shutdown_event = shutdown_event  # Set to break out from main loop
# self.lock = lock
# self.cancel_event = Event()  # Set to cancel current stream
# self.active = Event()  # Acquisition active event
# self.spec_queue = Queue()  # Signal output queue
# # Per acquisition attributes
# self.speci = -1  # Index of last received spectrum,
# # -1 when there is no active acquisition

# @property
# def timestamp(self) -> datetime:
#     """Timestamp in datetime format

#     :return: Timestamp
#     :rtype: datetime
#     """
#     if self.raw:
#         dotnet_datetime = self.raw.CreationDate

#         python_datetime = datetime(
#             year=dotnet_datetime.Year,
#             month=dotnet_datetime.Month,
#             day=dotnet_datetime.Day,
#             hour=dotnet_datetime.Hour,
#             minute=dotnet_datetime.Minute,
#             second=dotnet_datetime.Second,
#         )
#         return python_datetime

# @property
# def filename(self) -> str | None:
#     """Base filename of the raw file currently being streamed

#     :return: Base filename
#     :rtype: str
#     """
#     if self.raw:
#         filename = strip_filepath(self.raw.FileName)
#         timestamp = self.timestamp.strftime("%Y.%m.%d-%Hh%Mm%Ss")
#         # Add timestamp to the filename
#         return filename.replace("_", f"_{timestamp}_", 1)

# @property
# def method_file(self) -> str | None:
#     """Instrument method file name from the raw file

#     :return: Instrument method file name
#     :rtype: str | None
#     """
#     if self.raw:
#         method_file = self.raw.SampleInformation.InstrumentMethodFile
#         return method_file if method_file else None
#     return None

# @property
# def tic_neg(self) -> float | None:
#     """Total ion current in negative polarity (TIC)

#     :return: TIC
#     :rtype: float | None
#     """
#     if self.raw:
#         num_of_scans = self.raw.RunHeaderEx.SpectraCount
#         tics = np.zeros(num_of_scans)
#         for i in range(num_of_scans):
#             if (
#                 self.raw.GetFilterForScanNumber(i + 1).Polarity.ToString()
#                 == "Negative"
#             ):
#                 tics[i] = self.raw.GetScanStatsForScanNumber(i + 1).TIC
#         total_tic_neg = np.sum(tics)
#         return total_tic_neg
#     return None

# @property
# def tic_pos(self) -> float | None:
#     """Total ion current in positive polarity (TIC)

#     :return: TIC
#     :rtype: float | None
#     """
#     if self.raw:
#         num_of_scans = self.raw.RunHeaderEx.SpectraCount
#         tics = np.zeros(num_of_scans)
#         for i in range(num_of_scans):
#             if (
#                 self.raw.GetFilterForScanNumber(i + 1).Polarity.ToString()
#                 == "Positive"
#             ):
#                 tics[i] = self.raw.GetScanStatsForScanNumber(i + 1).TIC
#         total_tic_pos = np.sum(tics)
#         return total_tic_pos
#     return None

# @property
# def interval(self) -> float:
#     """Mean measurement interval in seconds, i.e. length of one spectrum in the sample

#     :return: Measurement interval [s]
#     :rtype: float
#     """
#     return (
#         self.length / self.raw.RunHeaderEx.LastSpectrum if self.raw else None
#     )  # [s]

# @property
# def length(self) -> float:
#     """Length of the sample file in seconds

#     :return: Sample length [s]
#     :rtype: float
#     """
#     return self.raw.RunHeaderEx.EndTime * 60.0 if self.raw else None  # [s]

# @property
# def mz(self) -> np.array:
#     """Precomputed m/z grid of the sample file

#     :return: m/z coordinate grid
#     :rtype: np.array
#     """
#     if self.raw:
#         return self._mz_grid.astype(np.float32)

# @property
# def progress(self) -> float:
#     """Streaming progress in percent

#     :return: Prgress [%]
#     :rtype: float
#     """
#     if not self.active.is_set():
#         return 100
#     return ((self.speci + 1) / self.raw.RunHeaderEx.LastSpectrum) * 100.0  # [%]

# def _get_and_feed_data(self, scan_no: int):
#     """Read data from the RAW file and put to queues"""
#     # == Get and feed mass spectrum data ==
#     # Get the scan statistics from the RAW file for this scan number
#     with self.lock:
#         scan_stats = self.raw.GetScanStatsForScanNumber(scan_no)
#     # Get timestamp from scan stats
#     ti = scan_stats.StartTime * 60.0  # [s]
#     # Get polarity from scan stats
#     polarity = scan_stats.ScanType.split(" ")[1]
#     with self.lock:
#         scan = self.raw.GetSegmentedScanFromScanNumber(scan_no, scan_stats)
#     # Map .NET arrays into numpy arrays
#     mz = net2np_array(scan.Positions).astype(np.float32)
#     spec = net2np_array(scan.Intensities).astype(np.float32)

#     # Round mz values based on the mz precision
#     mz, spec = self._set_mz_precision(mz, spec)
#     # Combine data for output
#     spec_data = {
#         "filename": self.filename,  # Current file basename
#         "i": self.speci,  # Current spectrum integer index
#         "t": float(ti),  # Timestamp [s]
#         "period": self.interval,  # Collection period [s]
#         "mz": mz.tobytes(),  # Serialized mass axis [float32]
#         "spec": spec.tobytes(),  # Serialized spectrum [float32]
#         "polarity": polarity,  # Polarity, '-' or '+'
#     }
#     # Feed
#     self.spec_queue.put(spec_data)

# def _feed_coordinates(self):
#     if self._has_negative_scans():
#         coordinates = {
#             "filename": self.filename,
#             "i": -1,
#             "mz": self.mz.tobytes(),
#             "t_range": [0, self.length],
#             "polarity": "-",
#             "method_file": self.method_file,
#         }
#         self.spec_queue.put(coordinates)
#     if self._has_positive_scans():
#         coordinates = {
#             "filename": self.filename,
#             "i": -1,
#             "mz": self.mz.tobytes(),
#             "t_range": [0, self.length],
#             "polarity": "+",
#             "method_file": self.method_file,
#         }
#         self.spec_queue.put(coordinates)

# def _finalize(self):
#     """Finalize acquisition"""
#     if not self.cancel_event.is_set():
#         # Feed poison pill
#         if self._has_negative_scans():
#             self.spec_queue.put(
#                 {
#                     "filename": self.filename,
#                     "i": None,
#                     "source_filepath": self.raw.FileName,
#                     "polarity": "-",
#                     "timestamp": self.timestamp.isoformat(),
#                     "tic": self.tic_neg,
#                 }
#             )
#         if self._has_positive_scans():
#             self.spec_queue.put(
#                 {
#                     "filename": self.filename,
#                     "i": None,
#                     "source_filepath": self.raw.FileName,
#                     "polarity": "+",
#                     "timestamp": self.timestamp.isoformat(),
#                     "tic": self.tic_pos,
#                 }
#             )
#     # Reset self
#     self.active.clear()
#     self.speci = -1
#     self._mz_grid = None
#     with self.lock:
#         self.raw.Dispose()
#         self.raw = None
#     self.cancel_event.clear()

# def _has_negative_scans(self) -> bool:
#     """Does the current raw file contain scans in negative polarity

#     :return: Has negative sans
#     :rtype: bool
#     """
#     polarity_filter = self.raw.GetFilterFromString("-")
#     scan_enumerator = self.raw.GetFilteredScanEnumerator(
#         polarity_filter
#     ).GetEnumerator()
#     return scan_enumerator.MoveNext()

# def _has_positive_scans(self) -> bool:
#     """Does the current raw file contain scans in negative polarity

#     :return: Has positive sans
#     :rtype: bool
#     """
#     polarity_filter = self.raw.GetFilterFromString("+")
#     scan_enumerator = self.raw.GetFilteredScanEnumerator(
#         polarity_filter
#     ).GetEnumerator()
#     return scan_enumerator.MoveNext()

# def _set_mz_precision(self, mz: np.ndarray, spec: np.ndarray) -> tuple:
#     """Aligns m/z values to the nearest values in a precomputed m/z grid
#     and aggregates corresponding intensities.

#     :param mz: mz scale
#     :type mz: array-like
#     :param spec: measured counts
#     :type spec: array-like
#     :return: a tuple of updated mz scale and counts
#     :rtype: tuple
#     """
#     mz = mz.astype(np.float32)
#     indices = np.searchsorted(self._mz_grid, mz)
#     indices = np.clip(indices, 0, len(self._mz_grid) - 1)

#     left_mzs = self._mz_grid[indices - 1]
#     right_mzs = self._mz_grid[indices]

#     left_diff = np.abs(left_mzs - mz)
#     right_diff = np.abs(right_mzs - mz)

#     closest_mzs = np.where(left_diff < right_diff, left_mzs, right_mzs)
#     unique_mz, inverse_indices = np.unique(closest_mzs, return_inverse=True)
#     aggregated_intensities = np.bincount(inverse_indices, weights=spec)

#     return unique_mz.astype(np.float32), aggregated_intensities.astype(np.float32)

# def _wait_for_queues(self):
#     """Wait for tick event to be set before continuing streaming

#     Returns
#     -------
#     bool
#         True if ticked, False if shutdown
#     """
#     while not (self.shutdown_event.is_set() or self.cancel_event.is_set()):
#         if not self.spec_queue.qsize():
#             # Queues empty
#             return True
#         else:
#             # Wait for data to be consumed from queues
#             sleep(0.01)
#     # Shutdown or cancel
#     return False

# def run(self):
#     self.log.info(f"Running raw streamer ({self.name})")
#     # Main loop
#     while not self.shutdown_event.is_set():
#         try:
#             file_to_stream = self.file_queue.get(timeout=0.1)
#             # Initialize Raw file reader
#             try:
#                 with self.lock:
#                     self.raw = RawFileReaderAdapter.FileFactory(file_to_stream)
#                     self.raw.SelectInstrument(Device.MS, 1)
#                     self.raw.IncludeReferenceAndExceptionData = True
#             except Exception as e:
#                 self.log.error(
#                     f"Failed to read file {Path(file_to_stream).name}: {e}"
#                 )
#                 continue
#         except Empty:
#             # No file to stream, keep waiting
#             continue

#         # Get mz range from the file
#         mz_min = self.raw.RunHeaderEx.LowMass
#         mz_max = self.raw.RunHeaderEx.HighMass
#         # Precompute mz grid
#         self._mz_grid = precompute_grid(mz_min, mz_max)
#         # Check if precomputation
#         if self._mz_grid is None:
#             self.log.error(
#                 f"Failed to compute mz grid. File {Path(file_to_stream).name} is likely damaged."
#             )
#             # Close raw file
#             with self.lock:
#                 self.raw.Dispose()
#             continue
#         # Start streaming
#         # Feed coordinates
#         self._feed_coordinates()
#         self.log.info(f"Acquisition started: {Path(file_to_stream).name}")
#         # Set active flag
#         self.active.set()
#         # Loop through the file and feed to queues
#         all_scans = range(
#             self.raw.RunHeaderEx.FirstSpectrum,
#             self.raw.RunHeaderEx.LastSpectrum + 1,
#         )
#         for scan_no in all_scans:
#             self.log.info(scan_no)
#             self.speci = scan_no - 1
#             # Update self and feed data into queue
#             self._get_and_feed_data(scan_no)
#             # Wait for queues to be empty
#             if self._wait_for_queues():
#                 # Empty
#                 continue
#             else:
#                 # Done
#                 break
#         # Out of stream loop
#         self._finalize()
#         self.log.info("Streaming finished")
#     # Out of main loop
#     self.log.info(f"Exiting raw streamer ({self.name})")
#     self.shutdown()

# def shutdown(self):
#     """Shutdown procedure"""
#     self.shutdown_event.set()
#     # Close queues
#     self.spec_queue.close()
#     self.spec_queue.join_thread()

# def start_stream(self, filename: str):
#     """Method to call externally, to start streaming a file

#     Alternative to directly putting a file into `self.file_queue`

#     :param filename: Full path to the file to be streamed
#     :type filename: str
#     :raises ValueError: If file is not found
#     """
#     if os.path.isfile(filename):
#         self.file_queue.put(filename)
#     else:
#         raise ValueError(f"File does not exist: {filename}")

# def stop_stream(self):
#     """Stop stream before complete

#     TODO: To be implemented
#     """
#     raise NotImplementedError
