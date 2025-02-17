# -*- coding: utf-8 -*-
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
from multiprocessing import Event, Queue, Lock
from queue import Empty
from threading import Thread
import h5py
import numpy as np

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

    :param filepath: Full file path
    :type filepath: str
    :return: Base filename
    :rtype: str
    """
    return os.path.splitext(os.path.basename(filepath))[0]


class H5Processor(Thread):
    """Read and process TOF h5 files"""

    def __init__(
        self, socket_client, file_queue=Queue(), shutdown_event=Event(), lock=Lock()
    ):
        Thread.__init__(self)
        # Init logger
        self.log = hardware_runtime.logger.bind(key=self.name)
        self.log.info("H5Processor initialized")
        self.socket_client = socket_client
        self.file_queue = file_queue
        self.shutdown_event = shutdown_event
        self.lock = lock
        self.cancel_event = Event()
        self.active = Event()

        self.h5 = None  # The h5 file reference
        self.file_to_process = None  # Path to the h5 file to process
        self.filename = None  # Filename base from TW h5 file

    @property
    def interval(self) -> float | None:
        """Mean measurement interval in seconds, i.e. length of one spectrum in the sample

        :return: Measurement interval [s]
        :rtype: float
        """
        if self.h5:
            # Check for zero bufs in the last write
            last_write = self.h5["TimingData"]["BufTimes"][-1]
            num_zero_writes = np.sum(last_write == 0)
            # Get total number of valid timestamps/scans
            n_scans = (
                self.h5.attrs["NbrBufs"][0] * self.h5.attrs["NbrWrites"][0]
                - num_zero_writes
            )
            # Return mean difference between timestamps
            return float(self.length / n_scans)  # [s]
        return None

    @property
    def length(self) -> float:
        """Length of the sample file in seconds

        :return: Sample length [s]
        :rtype: float
        """
        if self.h5:
            # Get timestamp reference and retrieve first and last values
            timestamps = self.h5["TimingData"]["BufTimes"]
            t_first = timestamps[0, 0]
            # Last write may contain zero bufs, exclude them
            t_last_bufs = timestamps[-1]
            t_last = t_last_bufs[t_last_bufs != 0][-1]
            # Return difference between first and last timestamp as total length
            return float(t_last - t_first)  # [s]
        return None

    @property
    def mz_range(self) -> list | None:
        """M/z range of the sample file

        :return: M/z range
        :rtype: list | None
        """
        if self.h5:
            # Return a list of 1st and last m/z values
            return self.h5["FullSpectra"]["MassAxis"][[0, -1]].tolist()
        return None

    @property
    def polarity(self) -> str | None:
        """Polarity of the sample file

        :return: polarity as a string
        :rtype: str | None
        """
        if self.h5:
            return "-" if self.h5.attrs["IonMode"] == "negative" else "+"
        return None

    @property
    def single_ion_signal(self) -> float | None:
        """Single ion signal [mV*ns/ion]

        :return: Single ion signal [mV*ns/ion]
        :rtype: float
        """
        if self.h5:
            return float(self.h5["FullSpectra"].attrs["Single Ion Signal"][0])
        return None

    @property
    def sample_interval(self) -> float | None:
        """Sample interval in nanoseconds

        :return: Sample interval [ns]
        :rtype: float
        """
        if self.h5:
            return float(
                self.h5["FullSpectra"].attrs["SampleInterval"][0] * 1e9
            )  # [s]->[ns]
        return None

    @property
    def conversion_coefficient(self) -> float | None:
        """Coefficient to convert signal intensity from [mV/ext] -> [ions/sec]

        Was used TofDaqStreamer, not applied here, but formula is good to keep

        :return: Conversion coefficient
        :rtype: float | None
        """
        if self.h5:
            # TOF frequency [Hz] (1/TOF period)
            tof_frequency = 1 / self.h5["TimingData"].attrs["TofPeriod"][0]
            return float(
                self.interval
                * (self.sample_interval * tof_frequency)
                / self.single_ion_signal
            )
        return None

    @property
    def tic(self) -> float | None:
        """Total Ion Current (TIC) of the sample file

        :return: TIC
        :rtype: float
        """
        if self.h5:
            return float(self.h5["FullSpectra"]["SumSpectrum"][:].sum())
        return None

    @property
    def mass_calibration(self) -> dict | None:
        """Mass calibration properties

        :return: Mass calibration properties
        :rtype: dict
        """
        if self.h5:
            # Get FullSpectra attributes reference
            attrs = self.h5["FullSpectra"].attrs
            # Number of mass calibration parameters
            num_params = attrs["MassCalibration nbrParameters"][0]
            # Get mass calibration parameters
            mass_calib_params = [
                float(attrs[f"MassCalibration p{i+1}"][0]) for i in range(num_params)
            ]
            return {
                "mode": int(attrs["MassCalibMode"][0]),
                "par": mass_calib_params,
            }
        return None

    def _finalize(self):
        """Finalize acquisition"""
        # Reset self
        self.active.clear()
        with self.lock:
            self.h5.close()
            # Reset attributes
            self.h5 = None
            self.filename = None
        self.cancel_event.clear()

    def _process_h5_file(self, sample_file_props: dict, h5_filepath: str) -> bool:
        """Main function processing the h5 files:
        1. Writes properties into the sample file
        2. Copies h5 file into the sample file folder
        3. Creates sum_signal.zarr
        4. Creates a record in the database

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :param h5_filepath: H5 file full path
        :type h5_filepath: str
        """
        base_path = get_filestore_path()
        data_path = parse_path_from_item_filename(
            sample_file_props["filename"], base_path
        )

        try:
            # Create sample file directory
            os.makedirs(data_path)

            # Write properties to the sample_file
            write_props(sample_file_props["filename"], sample_file_props)

            # Copy h5 file to the sample_file folder
            data_h5_path = os.path.join(data_path, "data.h5")
            shutil.copy(h5_filepath, data_h5_path)

            # Create sum_signal array
            sample_file_data = load_file(sample_file_props["filename"], vars=[])
            zarr_sdk.write_sum_signal_dataset(sample_file_data)

            self._create_db_record(sample_file_props)

            return True
        except FileExistsError:
            self.log.error(
                f"Processing error: sample file {sample_file_props['filename']} already exists!"
            )
            return False
        except Exception as e:
            self.log.error(f"Processing error: {e}")
            return False

    def _create_db_record(self, sample_file_props: dict):
        """Create a record in the database

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        """
        try:
            base_filename = Path(self.file_to_process).name
            file_context = self.socket_client.context_manager.get_context(base_filename)
            if file_context is None:
                raise RuntimeError(
                    f"File {base_filename} not registered in file converter service"
                )
            create_sample_file_db_record(
                sample_file_props, access_token=file_context.access_token
            )
        except Exception as e:
            self.log.error(f"Failed to create database record: {e}")

    def run(self):
        self.log.info(f"Running h5 processor ({self.name})")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                self.file_to_process = self.file_queue.get(timeout=0.1)
                # Initialize h5 file reader
                try:
                    with self.lock:
                        self.h5 = h5py.File(self.file_to_process, "r")
                except Exception as e:
                    self.log.error(
                        f"Failed to open file {Path(self.file_to_process)}: {e}"
                    )
                    continue
            except Empty:
                # No file to process, continue
                continue

            # Get filename
            self.filename = Path(self.file_to_process).stem
            self.log.info(f"Processing file: {self.filename}")
            # set active flag
            self.active.set()

            # Get UTC offset
            now = datetime.now()
            utc_offset = (
                now - now.astimezone(timezone.utc).replace(tzinfo=None)
            ).seconds

            # Get sample file properties
            sample_file_props = {
                "filename": self.filename.replace(" ", "_") + "_" + self.polarity,
                "length": self.length,
                "committed_length": self.length,
                "range": self.mz_range,
                "polarity": self.polarity,
                "single_ion_signal": self.single_ion_signal,
                "sample_interval": self.sample_interval,
                "tic": self.tic,
                "mass_calibration": self.mass_calibration,
                "utc_offset": utc_offset,
                # Not applicable for TOF
                "method_file": None,
            }

            if_processed = self._process_h5_file(
                sample_file_props, self.file_to_process
            )

            self._finalize()
            self.log.info(
                f"Finished processing file: {Path(self.file_to_process).name}"
            )

            if if_processed:
                self.log.info("Deleting file from the streams folder")
                try:
                    os.remove(self.file_to_process)
                except FileNotFoundError:
                    self.log.error(
                        f"Failed to delete file {self.file_to_process} from streams folder"
                    )
                    self.log.exception(e)

        # Out of main loop
        self.log.info(f"Exiting h5 processor ({self.name})")
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure"""
        self.shutdown_event.set()

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
