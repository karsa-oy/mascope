import os
from pathlib import Path
import shutil
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from datetime import datetime, timezone
import numpy as np

from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter
from ThermoFisher.CommonCore.Data.Business import Device

from mascope_file.io import write_props
from mascope_file.name import parse_path_from_item_filename
from mascope_file.record import create_sample_file_db_record
from mascope_thermo.thermo import get_polarity_options

from mascope_thermo.runtime import runtime


def strip_filepath(filepath: str) -> str:
    """Strip path and file extension"""
    return os.path.splitext(os.path.basename(filepath))[0]


class RawProcessor(Thread):
    """Reads and processes Orbi raw files"""

    def __init__(
        self,
        socket_client,
        file_queue=Queue(),
        shutdown_event=Event(),
        lock=Lock(),
    ):
        Thread.__init__(self)
        # Init logger
        self.log = runtime.logger.bind(key=self.name)
        self.log.info(f"Initializing raw file processor ({self.name})")
        # Init socket client
        self.socket_client = socket_client
        # Opened raw file
        self.raw = None
        # Synchronization primitives
        self.file_queue = file_queue  # Queue for files to stream
        self.shutdown_event = shutdown_event  # Set to break out from main loop
        self.lock = lock
        self.cancel_event = Event()  # Set to cancel current stream
        self.active = Event()  # Acquisition active event

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

    @property
    def interval(self) -> float:
        """Mean measurement interval in seconds, i.e. length of one spectrum in the sample

        :return: Measurement interval [s]
        :rtype: float
        """
        if self.raw:
            return self.length / self.raw.RunHeaderEx.LastSpectrum  # [s]

    @property
    def length(self) -> float:
        """Length of the sample file in seconds

        :return: Sample length [s]
        :rtype: float
        """
        if self.raw:
            return self.raw.RunHeaderEx.EndTime * 60.0  # [s]

    @property
    def mz_range(self) -> list | None:
        """M/z range of the sample file

        :return: M/z range
        :rtype: list | None
        """
        if self.raw:
            return [self.raw.RunHeaderEx.LowMass, self.raw.RunHeaderEx.HighMass]

    @property
    def polarity(self) -> str | None:
        """Polarity options in the sample file

        :return: Polarity options
        :rtype: str | None
        """
        if self.raw:
            return get_polarity_options(self.raw.FileName)

    def _finalize(self):
        """Finalize acquisition"""
        # Reset self
        self.active.clear()
        with self.lock:
            self.raw.Dispose()
            self.raw = None
        self.cancel_event.clear()

    def _process_raw_file(self, sample_file_props: dict, raw_file_path: str) -> bool:
        """Main function processing the raw files:
        1. Writes properties into the sample file
        2. Copies raw file into the sample file folder
        3. Creates sum_signal.zarr
        4. Creates a record in the database

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :param raw_file_path: Path to the target raw file
        :type raw_file_path: str
        :return: True if raw file processed successfully, False otherwise
        :rtype: bool
        """
        data_path = parse_path_from_item_filename(sample_file_props["filename"])

        try:
            # Create sample file directory
            os.makedirs(data_path)

            # Write properties to the sample_file
            write_props(sample_file_props["filename"], sample_file_props)

            # Copy raw file to the sample_file folder
            data_raw_path = os.path.join(data_path, "data.raw")
            shutil.copy(raw_file_path, data_raw_path)

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
        """
        Creates a record in the database.

        Requires file to be registered in the file converter service context.
        Raises error if file context is not found.
        """
        try:
            base_filename = os.path.basename(self.raw.FileName)
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
            try:
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
                    "filename": self.filename.replace(" ", "_"),
                    "length": self.length,
                    "range": self.mz_range,
                    "utc_offset": utc_offset,
                    "method_file": self.method_file,
                    "timestamp": self.timestamp.isoformat(),  # for DB record
                    "polarity": self.polarity,
                    # streaming leftovers:
                    "committed_length": self.length,
                    # non-applicable for Orbi:
                    "single_ion_signal": None,
                    "sample_interval": None,
                    "mz_calibration": None,
                }
                if_processed = self._process_raw_file(
                    sample_file_props, file_to_process
                )
                self.log.info(f"Finished processing file: {Path(file_to_process).name}")
            except Exception as e:
                self.log.error(
                    f"Failed to process file {Path(file_to_process).name}: {e}"
                )
                if_processed = False
            finally:
                self._finalize()
            if if_processed:
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
