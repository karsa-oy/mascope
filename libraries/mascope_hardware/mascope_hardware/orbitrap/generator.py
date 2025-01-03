# -*- coding: utf-8 -*-
"""Classes to stream data to KFeeder, either offline from H5 file or online directly
from TofDaq Recorder.

Created on Tue Apr 09 13:08:29 2019

@author: Oskari Kausiala
"""
import os
from pathlib import Path
import shutil
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from time import sleep
from datetime import datetime, timezone
import numpy as np

from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter
from ThermoFisher.CommonCore.Data.Business import Device

from mascope_hardware.runtime import hardware_runtime
from mascope_hardware.util import create_sample_file_db_record
from mascope_lib.file_func import (
    write_props,
    load_file,
    zarr_sdk,
    get_filestore_path,
    parse_path_from_item_filename,
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


class RawProcessor(Thread):
    """Reads and processes Orbi raw files"""

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
        # spec_queue is not used by RawProcessor but is required for
        # backward compatibility with service.py
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
        sample_file_data = load_file(sample_file_props["filename"], vars=[])
        zarr_sdk.write_sum_signal_dataset(sample_file_data)

        create_sample_file_db_record(sample_file_props)

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

            # Delete processed file
            self.log.info("Deleting file from the streams folder")
            try:
                os.remove(file_to_process)
            except FileNotFoundError as e:
                self.log.error(
                    f"Failed to delete file {file_to_process} from streams folder"
                )
                self.log.exception(e)
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
