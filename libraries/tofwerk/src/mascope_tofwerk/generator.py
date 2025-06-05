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

from mascope_tofwerk.runtime import runtime
from mascope_file.io import write_props
from mascope_file.name import parse_path_from_item_filename
from mascope_file.record import create_sample_file_db_record


class H5Processor(Thread):
    """Read and process TOF h5 files"""

    def __init__(
        self, socket_client, file_queue=Queue(), shutdown_event=Event(), lock=Lock()
    ):
        Thread.__init__(self)
        # Init logger
        self.log = runtime.logger.bind(key=self.name)
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
            timestamps = self.h5["TimingData"]["BufTimes"][:].flatten()
            non_zero_indices = np.where(timestamps != 0)[0]

            # Trim trailing zeros
            timestamps = timestamps[: non_zero_indices[-1] + 1]

            # Calculate the mean difference between consecutive datapoints
            differences = np.diff(timestamps)
            return float(np.mean(differences))  # [s]

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
            # Total length of the sample file is the difference between
            # starts of the first and the last scan + mean interval between scans
            return float(t_last - t_first) + self.interval  # [s]

    @property
    def mz_range(self) -> list | None:
        """M/z range of the sample file

        :return: M/z range
        :rtype: list | None
        """
        if self.h5:
            # Return a list of 1st and last m/z values
            return self.h5["FullSpectra"]["MassAxis"][[0, -1]].tolist()

    @property
    def single_ion_signal(self) -> float | None:
        """Single ion signal [mV*ns/ion]

        :return: Single ion signal [mV*ns/ion]
        :rtype: float
        """
        if self.h5:
            return float(self.h5["FullSpectra"].attrs["Single Ion Signal"][0])

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
                float(attrs[f"MassCalibration p{i + 1}"][0]) for i in range(num_params)
            ]
            return {
                "mode": int(attrs["MassCalibMode"][0]),
                "par": mass_calib_params,
            }

    @property
    def polarity(self) -> str | None:
        """Polarity options in the sample file

        :return: Polarity options
        :rtype: str | None
        """
        if self.h5:
            ion_mode = self.h5.attrs.get("IonMode", "").lower()
            if ion_mode == b"negative":
                return "-"
            elif ion_mode == b"positive":
                return "+"

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

    def _process_h5_file(self, sample_file_props: dict, h5_filepath: str) -> None:
        """Main function processing the h5 files:
        1. Writes properties into the sample file
        2. Copies h5 file into the sample file folder
        3. Creates a record in the database

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :param h5_filepath: H5 file full path
        :type h5_filepath: str
        :raises FileExistsError: If sample file already exists
        :raises Exception: If any processing step fails
        """
        data_path = parse_path_from_item_filename(sample_file_props["filename"])

        try:
            # Create sample file directory
            os.makedirs(data_path)

            # Write properties to the sample_file
            write_props(sample_file_props["filename"], sample_file_props)

            # Copy h5 file to the sample_file folder
            data_h5_path = os.path.join(data_path, "data.h5")
            shutil.copy(h5_filepath, data_h5_path)

            # Create database record (raises exceptions on failure)
            self._create_db_record(sample_file_props)

        except FileExistsError as exc:
            raise FileExistsError(
                "File already exists in the filestore. Please contact the administrator or rename the file."
            ) from exc
        except Exception as e:
            raise Exception(str(e)) from e

    def _create_db_record(self, sample_file_props: dict):
        """Create a record in the database

        :param sample_file_props: Sample file properties
        :type sample_file_props: dict
        :raises RuntimeError: If file context is not found or database creation fails
        """
        base_filename = Path(self.file_to_process).name
        try:
            file_context = self.socket_client.context_manager.get_context(base_filename)
            if file_context is None:
                raise RuntimeError(
                    f"File {base_filename} not registered in file converter service"
                )

            create_sample_file_db_record(
                sample_file_props, access_token=file_context.access_token
            )
        except Exception as e:
            error_msg = f"Failed to create database record: {str(e)}"
            self.log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def run(self):
        self.log.info(f"Running h5 processor ({self.name})")
        # Main loop
        while not self.shutdown_event.is_set():
            try:
                self.file_to_process = self.file_queue.get(timeout=0.1)
                file_basename = Path(self.file_to_process).name
                instrument = file_basename.split("_")[0]

                # Initialize h5 file reader (separate error handling)
                try:
                    with self.lock:
                        self.h5 = h5py.File(self.file_to_process, "r")
                except Exception as e:
                    error_msg = f"Cannot open file: {str(e)}"
                    self.log.error(
                        f"Failed to open file {Path(self.file_to_process)}: {e}"
                    )

                    self.socket_client.emit(
                        "file_processing_error",
                        {
                            "filename": file_basename,
                            "instrument": instrument,
                            "error": error_msg,
                        },
                    )

                    self._handle_failed_file(self.file_to_process)
                    continue

                # Main processing block (centralized error handling)
                try:
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
                        "filename": self.filename.replace(" ", "_"),
                        "length": self.length,
                        "committed_length": self.length,
                        "range": self.mz_range,
                        "single_ion_signal": self.single_ion_signal,
                        "sample_interval": self.sample_interval,
                        "mass_calibration": self.mass_calibration,
                        "utc_offset": utc_offset,
                        "polarity": self.polarity,
                        # Not applicable for TOF
                        "method_file": None,
                    }

                    # Process file (raises exceptions on failure)
                    self._process_h5_file(sample_file_props, self.file_to_process)

                    self.log.info(
                        f"Finished processing file: {Path(self.file_to_process).name}"
                    )

                    # CRITICAL: Finalize BEFORE cleanup to release file locks
                    self._finalize()

                    # Success: delete file and clear context
                    self._cleanup_successful_file(self.file_to_process, file_basename)
                except Exception as e:
                    error_msg = str(e)
                    self.log.error(
                        f"Failed to process file {Path(self.file_to_process).name}: {e}"
                    )

                    # CRITICAL: Finalize BEFORE error emission to ensure h5 file is closed
                    self._finalize()

                    # Emit clean error message
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
                    self._handle_failed_file(self.file_to_process)

            except Empty:
                # No file to process, continue
                continue
            except Exception as e:
                # Catch any unexpected errors
                self.log.error(f"Unexpected error in h5 processor: {e}")
                if self.file_to_process and file_basename:
                    # Ensure finalize is called before emission
                    if self.h5:
                        self._finalize()

                    self.socket_client.emit(
                        "file_processing_error",
                        {
                            "filename": file_basename,
                            "instrument": instrument or "unknown",
                            "error": f"Unexpected error: {str(e)}",
                        },
                    )

                    # Clear context after emission
                    self.socket_client.context_manager.clear_context(file_basename)

        # Out of main loop
        self.log.info(f"Exiting h5 processor ({self.name})")
        self.shutdown()

    def shutdown(self):
        """Shutdown procedure"""
        self.shutdown_event.set()
