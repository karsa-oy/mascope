import os
from pathlib import Path
import shutil
from multiprocessing import Event, Lock, Queue
from queue import Empty
from threading import Thread
from datetime import datetime, timezone

from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter
from ThermoFisher.CommonCore.Data.Business import Device

from mascope_file.io import write_props
from mascope_file.name import parse_path_from_item_filename
from mascope_file.record import (
    create_sample_file_db_record,
    check_sample_file_db_record,
    delete_sample_file_by_filename,
)
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

    def _handle_failed_file(self, file_path: str) -> None:
        """Handle failed file - moves file to failed_files folder if possible

        :param file_path: Path to the failed file
        :type file_path: str
        """
        self.log.info(
            f"File {file_path} was not processed, moving to the folder of failed files"
        )
        try:
            failed_folder = os.path.join(os.path.dirname(file_path), "failed_files")
            os.makedirs(failed_folder, exist_ok=True)
            # Use full path to enable overwrite if the file already exists
            failed_file = os.path.join(failed_folder, os.path.basename(file_path))
            shutil.move(file_path, failed_file)
            self.log.info(f"Moved failed file to: {failed_file}")
        except PermissionError as e:
            # File is locked - this indicates the file is still being processed
            self.log.warning(f"Could not move locked file {file_path}: {e}")
            self.log.warning(
                "File will remain in streams folder - manual cleanup may be needed"
            )
        except Exception as e:
            self.log.error(f"Failed to move file {file_path} to the error folder")
            self.log.exception(e)

    def _cleanup_successful_file(self, file_to_process: str, file_basename: str):
        """Handle successful file processing cleanup

        NOTE: This should only be called AFTER _finalize() to ensure file is not locked
        """
        try:
            # Delete file from streams folder
            self.log.info("Deleting file from the streams folder")
            os.remove(file_to_process)
            self.log.info(f"Successfully deleted file: {file_to_process}")
        except FileNotFoundError:
            # File already deleted - this is not critical
            self.log.warning(
                f"File {file_to_process} was already deleted from streams folder"
            )
        except PermissionError as e:
            # File locked - this indicates a problem with file handle cleanup
            self.log.warning(f"Could not delete file {file_to_process}: {e}")
            self.log.warning(
                "File will remain in streams folder - manual cleanup may be needed"
            )
            self.log.warning(
                "This may indicate an issue with file handle cleanup in _finalize()"
            )
        except Exception as e:
            # Other deletion errors - log but don't fail
            self.log.error(
                f"Unexpected error during file deletion {file_to_process}: {e}"
            )

        # Always clear context at the end, regardless of file deletion success
        self.socket_client.context_manager.clear_context(file_basename)

    def _get_file_context(self):
        """Get file context for the current raw file being processed.

        :return: File context object
        :raises RuntimeError: If file context is not found
        """
        base_filename = os.path.basename(self.raw.FileName)

        if not (
            file_context := self.socket_client.context_manager.get_context(
                base_filename
            )
        ):
            raise RuntimeError(
                f"File {base_filename} not registered in file converter service"
            )
        return file_context

    def _check_orphan_sample_file_filestore(self, filename: str) -> bool:
        """Check if file's directory exists in filestore without corresponding database record.

        :param filename: Sample filename to check
        :type filename: str
        :return: True if directory is orphaned (exists but no DB record), False otherwise
        :rtype: bool
        """
        try:
            # Check if filestore directory exists
            data_path = parse_path_from_item_filename(filename)
            if not os.path.exists(data_path):
                return False

            # Get file context and check database record
            file_context = self._get_file_context()
            return not check_sample_file_db_record(filename, file_context.access_token)

        except RuntimeError:
            raise
        except Exception as e:
            self.log.error(f"Error checking orphaned filestore {filename}: {e}")
            return False

    def _remove_orphaned_filestore(self, filename: str) -> None:
        """Remove orphaned filestore directory and any database record.

        :param filename: Sample filename to clean up
        :type filename: str
        """
        try:
            file_context = self._get_file_context()
            delete_sample_file_by_filename(filename, file_context.access_token)
        except Exception as e:
            self.log.error(f"Error removing orphaned filestore {filename}: {e}")
            raise

    def _create_filestore_directory(
        self, sample_file_props: dict, raw_file_path: str
    ) -> None:
        """Create filestore directory, write properties, and copy raw file.

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :param raw_file_path: Path to the source raw file
        :type raw_file_path: str
        :raises FileExistsError: If directory already exists
        """
        filename = sample_file_props["filename"]
        data_path = parse_path_from_item_filename(filename)

        # Create sample file directory, will raise FileExistsError if directory exists
        os.makedirs(data_path)

        try:
            # Write properties to the sample file
            write_props(filename, sample_file_props)

            # Copy raw file to the sample file folder
            data_raw_path = os.path.join(data_path, "data.raw")
            shutil.copy(raw_file_path, data_raw_path)

        except Exception:
            # Cleanup directory if file operations fail
            if os.path.exists(data_path):
                shutil.rmtree(data_path)
            raise

    def _create_db_record(self, sample_file_props: dict) -> None:
        """Create database record for the sample file.

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :raises RuntimeError: If database creation fails
        """
        try:
            file_context = self._get_file_context()
            create_sample_file_db_record(
                sample_file_props, access_token=file_context.access_token
            )

        except Exception as e:
            error_msg = f"Failed to create database record: {e}"
            self.log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _process_raw_file(self, sample_file_props: dict, raw_file_path: str) -> None:
        """Process raw files with orphaned directory handling.

        Steps:
        1. Create filestore directory, write properties, and copy raw file
        2. Create database record
        If FileExistsError occurs, check for orphaned filestore and retry creation steps.

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :param raw_file_path: Path to the target raw file
        :type raw_file_path: str
        :raises FileExistsError: If sample file already exists with valid database record
        :raises Exception: If any processing step fails
        """
        filename = sample_file_props["filename"]

        try:
            # Step 1: Create filestore directory, write properties, and copy file
            self._create_filestore_directory(sample_file_props, raw_file_path)

            # Step 2: Create database record
            self._create_db_record(sample_file_props)

        except FileExistsError as exc:
            # Check if filestore exists without database record (orphaned)
            if self._check_orphan_sample_file_filestore(filename):
                self.log.info(
                    f"Found orphaned filestore for {filename}, cleaning up and retrying..."
                )

                self._remove_orphaned_filestore(filename)

                # Retry after cleanup
                self._create_filestore_directory(sample_file_props, raw_file_path)
                self._create_db_record(sample_file_props)
            else:
                self.log.error(
                    f"File already exists in the filestore with valid database record: {filename}"
                )
                raise FileExistsError(
                    "File already exists, please delete the old file, rename the file you want to upload or contact the administrator."
                ) from exc

    def run(self):
        self.log.info(f"Running raw processor ({self.name})")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_to_process = self.file_queue.get(timeout=0.1)
                file_basename = os.path.basename(file_to_process)
                instrument = file_basename.split("_")[0]

                # Initialize Raw file reader (separate error handling)
                try:
                    with self.lock:
                        self.raw = RawFileReaderAdapter.FileFactory(file_to_process)
                        self.raw.SelectInstrument(Device.MS, 1)
                        self.raw.IncludeReferenceAndExceptionData = True
                except Exception as e:
                    error_msg = f"Failed to read file {Path(file_to_process).name}: {e}"
                    self.log.error(error_msg)
                    self.socket_client.emit(
                        "file_processing_error",
                        {
                            "filename": file_basename,
                            "instrument": instrument,
                            "error": error_msg,
                        },
                    )
                    self._finalize()
                    self._handle_failed_file(file_to_process)
                    continue

                # Main processing block (centralized error handling)
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
                    # Process file (will raise exception on failure)
                    self._process_raw_file(sample_file_props, file_to_process)

                    self.log.info(
                        f"Finished processing file: {Path(file_to_process).name}"
                    )

                    # CRITICAL: Finalize BEFORE cleanup to release file locks
                    self._finalize()

                    # Success: delete file and clear context
                    self._cleanup_successful_file(file_to_process, file_basename)
                except Exception as e:
                    error_msg = str(e)
                    self.log.error(
                        f"Failed to process file {Path(file_to_process).name}: {e}"
                    )

                    # CRITICAL: Finalize BEFORE error emission to ensure raw file is disposed
                    self._finalize()

                    self.socket_client.emit(
                        "file_processing_error",
                        {
                            "filename": file_basename,
                            "instrument": instrument,
                            "error": error_msg,
                        },
                    )
                    # Clear context after error emission
                    self.socket_client.context_manager.clear_context(file_basename)
                    self._handle_failed_file(file_to_process)

            except Empty:
                # No file to stream, keep waiting
                continue
            except Exception as e:
                # Catch any unexpected errors (e.g., issues with file queue, etc.)
                self.log.error(f"Unexpected error in processor: {e}")
                if file_to_process and file_basename:
                    # Check that finalize is called before event emission
                    if self.raw:
                        self._finalize()

                    self.socket_client.emit(
                        "file_processing_error",
                        {
                            "filename": file_basename,
                            "instrument": instrument or "unknown",
                            "error": f"Unexpected processor error: {str(e)}",
                        },
                    )

                    # Clear context after emission
                    self.socket_client.context_manager.clear_context(file_basename)

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
