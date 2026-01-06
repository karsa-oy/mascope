# -*- coding: utf-8 -*-
"""Base file processor class for shared functionality between different file type processors."""

import asyncio
import os
import shutil
import traceback
from abc import ABC, ABCMeta, abstractmethod
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from threading import Event, Thread

import mascope_sdk
from mascope_file.io import write_props
from mascope_file.name import (
    get_instrument_name,
    parse_path_from_item_filename,
)
from mascope_signal.peak import compute_peaks

from .api import (
    check_sample_file_db_record,
    create_instrument_config_db_record,
    create_sample_file_db_record,
    delete_sample_file_by_filename,
)
from .runtime import runtime
from .schema import SampleFileProps


# Configure service name to use in request headers
mascope_sdk.SERVICE_NAME = "file-converter"


def with_file_context(prop_getter) -> callable:
    """Abstract file context manager decorator

    :param prop_getter: Property getter function
    :type prop_getter: callable
    :return: Wrapped property getter
    """

    def wrapper(self):
        # Use the class's context manager, passing the file path
        with self._file_context_manager(  # pylint: disable=protected-access
            self.file_to_process
        ) as file_handle:
            self.file_handle = file_handle
            prop = prop_getter(self)

        self.file_handle = None
        return prop

    return wrapper


class FileProcessorMeta(ABCMeta):
    """Metaclass that automatically creates abstract properties based on SampleFileProps fields."""

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Only apply to BaseFileProcessor, not its subclasses
        if name == "BaseFileProcessor":
            schema_fields = SampleFileProps.model_fields

            if "__annotations__" not in namespace:
                namespace["__annotations__"] = {}

            # Create abstract properties for each schema field
            for field_name, field_info in schema_fields.items():
                if field_name in namespace:
                    continue

                # Add type to class annotations for type checker recognition
                field_type = field_info.annotation
                namespace["__annotations__"][field_name] = field_type

                def make_abstract_property(prop_type, description):
                    """Create abstract property with proper closure"""

                    def getter(self):
                        raise NotImplementedError

                    getter.__doc__ = description
                    getter.__annotations__ = {"return": prop_type}

                    return property(abstractmethod(getter))

                # Get description from field info
                description = getattr(
                    field_info, "description", f"Abstract property for {field_name}"
                )

                # Add the abstract property to the namespace
                namespace[field_name] = make_abstract_property(field_type, description)

        return super().__new__(mcs, name, bases, namespace, **kwargs)


class BaseFileProcessor(Thread, ABC, metaclass=FileProcessorMeta):
    """Base class for file processors with shared functionality.

    Abstract properties are automatically generated from SampleFileProps schema fields
    using the FileProcessorMeta metaclass. This ensures a single source of truth
    for property definitions.
    """

    def __init__(
        self,
        socket_client,
        file_queue=Queue(),
        shutdown_event=Event(),
    ):
        Thread.__init__(self)
        runtime.logger.info(f"{self.__class__.__name__} initialized")

        self.socket_client = socket_client
        self.file_queue = file_queue
        self.shutdown_event = shutdown_event
        self.cancel_event = Event()
        self.active = Event()

        self.file_to_process = None  # Path to the file to process
        self.file_handle = None  # Abstract file reference, managed by context manager

    # Additional abstract properties not in SampleFileProps
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Get the file extension for the specific file type.

        :return: File extension
        :rtype: str
        """
        raise NotImplementedError

    # Abstract methods - must be implemented by subclasses
    @staticmethod
    @abstractmethod
    def _file_context_manager(file_path: str):
        """Get the file context manager for the specific file type.

        :param file_path: Path to the file
        :type file_path: str
        :return: File context manager
        """
        raise NotImplementedError

    @abstractmethod
    def _process_instrument_config(
        self, sample_file_props: SampleFileProps
    ) -> tuple[any, any, any, any]:
        """Fit instrument functions."""
        raise NotImplementedError

    # Common methods - used by all subclasses
    def _check_orphan_sample_file_filestore(self, filename: str) -> bool:
        """Check if file's directory exists in filestore without corresponding database record."""
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
            runtime.logger.error(f"Error checking orphaned filestore {filename}: {e}")
            return False

    def _cleanup_successful_file(self, file_to_process: str, file_basename: str):
        """Handle successful file processing cleanup."""
        try:
            # Delete file from streams folder
            runtime.logger.info("Deleting file from the streams folder")
            os.remove(file_to_process)
            runtime.logger.info(f"Successfully deleted file: {file_to_process}")
        except FileNotFoundError:
            # File already deleted - this is not critical
            runtime.logger.warning(
                f"File {file_to_process} was already deleted from streams folder"
            )
        except PermissionError as e:
            # File locked - this indicates a problem with file handle cleanup
            runtime.logger.warning(f"Could not delete file {file_to_process}: {e}")
            runtime.logger.warning(
                "File will remain in streams folder - manual cleanup may be needed"
            )
            runtime.logger.warning(
                "This may indicate an issue with file handle cleanup in _finalize()"
            )
        except Exception as e:
            # Other deletion errors - log but don't fail
            runtime.logger.error(
                f"Unexpected error during file deletion {file_to_process}: {e}"
            )

        # Always clear context at the end, regardless of file deletion success
        self.socket_client.context_manager.clear_context(file_basename)

    def _compute_peaks(
        self, filename: str, instrument_functions: tuple[any, any, any]
    ) -> None:
        """Compute peaks for the processed file."""
        asyncio.run(compute_peaks(filename, instrument_functions))

    def _copy_file_to_filestore(self, source_path: str, target_dir: str) -> None:
        """Copy raw file to filestore."""
        data_raw_path = os.path.join(target_dir, f"data{self.file_extension}")
        shutil.copy(source_path, data_raw_path)

    def _create_db_record(
        self,
        sample_file_props: SampleFileProps,
        instrument_function_id: str,
    ) -> None:
        """
        Create database record for the sample file.

        :param sample_file_props: File properties
        :type sample_file_props: SampleFileProps
        :param instrument_function_id: FK to instrument config
        :type instrument_function_id: str
        :raises RuntimeError: If database record creation fails
        """
        try:
            file_context = self._get_file_context()
            create_sample_file_db_record(
                sample_file_props,
                instrument_function_id,
                access_token=file_context.access_token,
            )

        except Exception as e:
            error_msg = f"Failed to create database record: {e}"
            runtime.logger.error(error_msg)
            # Delete filestore directory on failure
            filename = sample_file_props.filename
            data_path = parse_path_from_item_filename(filename)
            if os.path.exists(data_path):
                shutil.rmtree(data_path)
            raise RuntimeError(error_msg) from e

    def _create_filestore_directory(
        self, sample_file_props: SampleFileProps, source_file_path: str
    ) -> None:
        """Create filestore directory, write properties, and copy file."""
        filename = sample_file_props.filename
        data_path = parse_path_from_item_filename(filename)

        # Create sample file directory, will raise FileExistsError if directory exists
        os.makedirs(data_path)

        try:
            # Write properties to the sample file
            write_props(filename, sample_file_props.model_dump(by_alias=True))

            # Copy file to the sample file folder using subclass-specific method
            self._copy_file_to_filestore(source_file_path, data_path)

        except Exception:
            # Cleanup directory if file operations fail
            if os.path.exists(data_path):
                shutil.rmtree(data_path)
            raise

    def _create_instrument_config(
        self,
        sample_file_props: SampleFileProps,
    ) -> tuple[str, any, any]:
        """Create instrument config. Fit instrument functions (sub-class specific)
        and write to database

        :rtype: tuple[str, any, any]
        :return: Tuple of (instrument_function_id, peakshape_numpy, resolution_function_partial)
        """
        (
            peakshape,
            resolution_function,
            peakshape_numpy,
            resolution_function_partial,
        ) = self._process_instrument_config(sample_file_props)

        file_context = self._get_file_context()

        instrument_function_id = create_instrument_config_db_record(
            sample_file_props,
            peakshape,
            resolution_function,
            access_token=file_context.access_token,
        )
        return instrument_function_id, peakshape_numpy, resolution_function_partial

    def _emit_progress_notification(self, progress: int):
        """Emit file processing progress notification."""
        file_basename = os.path.basename(self.file_to_process)
        instrument = get_instrument_name(file_basename)

        self.socket_client.emit(
            "file_processing_progress",
            {
                "filename": file_basename,
                "instrument": instrument,
                "progress": progress,
            },
        )

    def _finalize(self):
        """Finalize processing - close file and reset state."""
        self.active.clear()
        self.cancel_event.clear()

    def _get_file_context(self):
        """Get file context for the current file being processed."""
        base_filename = os.path.basename(self.file_to_process)

        if not (
            file_context := self.socket_client.context_manager.get_context(
                base_filename
            )
        ):
            raise RuntimeError(
                f"File {base_filename} not registered in file converter service"
            )
        return file_context

    def _get_sample_file_props(self) -> SampleFileProps:
        """Extract sample file properties from the opened file.

        Note: Properties are dynamically generated by FileProcessorMeta metaclass
        from SampleFileProps schema fields.
        """
        # Dynamic approach - build properties dict from schema fields
        props_data = {}
        schema_fields = SampleFileProps.model_fields

        for field_name in schema_fields.keys():
            # Get the property value using getattr to avoid linter issues
            value = getattr(self, field_name)
            props_data[field_name] = value

        return SampleFileProps(**props_data)

    def _handle_failed_file(self, file_path: str) -> None:
        """Handle failed file - moves file to failed_files folder if possible."""
        runtime.logger.info(
            f"File {file_path} was not processed, moving to the folder of failed files"
        )
        try:
            failed_folder = os.path.join(os.path.dirname(file_path), "failed_files")
            os.makedirs(failed_folder, exist_ok=True)
            # Use full path to enable overwrite if the file already exists
            failed_file = os.path.join(failed_folder, os.path.basename(file_path))
            shutil.move(file_path, failed_file)
            runtime.logger.info(f"Moved failed file to: {failed_file}")
        except PermissionError as e:
            # File is locked - this indicates the file is still being processed
            runtime.logger.warning(f"Could not move locked file {file_path}: {e}")
            runtime.logger.warning(
                "File will remain in streams folder - manual cleanup may be needed"
            )
        except Exception as e:
            runtime.logger.error(f"Failed to move file {file_path} to the error folder")
            runtime.logger.exception(e)

    def _process_file(
        self, sample_file_props: SampleFileProps, file_path: str, retry_count: int = 0
    ) -> None:
        """Process file with orphaned directory handling."""
        filename = sample_file_props.filename
        file_basename = os.path.basename(self.file_to_process)
        instrument = get_instrument_name(filename)

        try:
            self._emit_progress_notification(0)
            # Create filestore directory, write properties, and copy file
            self._create_filestore_directory(sample_file_props, file_path)

            self._emit_progress_notification(10)

            # Fit instrument functions and get the ID
            instrument_function_id, *instrument_functions = (
                self._create_instrument_config(sample_file_props)
            )

            self._emit_progress_notification(25)

            # Compute peak data
            self._compute_peaks(filename, instrument_functions)

            self._emit_progress_notification(90)

            # Create sample file DB record with instrument config FK
            self._create_db_record(sample_file_props, instrument_function_id)

            self._emit_progress_notification(100)

        except FileExistsError as exc:
            # Check if filestore exists without database record (orphaned)
            if self._check_orphan_sample_file_filestore(filename):
                if retry_count >= 1:
                    runtime.logger.error(
                        f"Retry limit reached for orphaned filestore cleanup: {filename}"
                    )
                    raise exc
                runtime.logger.info(
                    f"Found orphaned filestore for {filename}, cleaning up and retrying..."
                )

                self._remove_orphaned_filestore(filename)

                # Retry after cleanup
                self._process_file(
                    sample_file_props, file_path, retry_count=retry_count + 1
                )
            else:
                runtime.logger.error(
                    f"File already exists in the filestore with valid database record: {filename}"
                )
                raise FileExistsError(
                    "File already exists, please delete the old file, rename the file you want to "
                    "upload or contact the administrator."
                ) from exc

    def _remove_orphaned_filestore(self, filename: str) -> None:
        """Remove orphaned filestore directory and any database record."""
        try:
            file_context = self._get_file_context()
            delete_sample_file_by_filename(filename, file_context.access_token)
        except Exception as e:
            runtime.logger.error(f"Error removing orphaned filestore {filename}: {e}")
            raise

    def _strip_filepath(self, filepath: str) -> str:
        """Strip path and file extension"""
        return os.path.splitext(os.path.basename(filepath))[0]

    def run(self):
        """Main processing loop."""
        runtime.logger.info(f"Running {self.__class__.__name__} ({self.name})")

        # Main loop
        while not self.shutdown_event.is_set():
            try:
                file_basename = None
                instrument = None
                self.file_to_process = self.file_queue.get(timeout=0.1)
                file_basename = os.path.basename(self.file_to_process)
                instrument = get_instrument_name(file_basename)

                # Main processing block
                try:
                    # Set active flag
                    runtime.logger.info(
                        f"Processing file: {Path(self.file_to_process).name}"
                    )
                    self.active.set()

                    # Get sample file properties using subclass implementation
                    sample_file_props = self._get_sample_file_props()

                    # Process file (raises exceptions on failure)
                    self._process_file(sample_file_props, self.file_to_process)

                    runtime.logger.info(
                        f"Finished processing file: {Path(self.file_to_process).name}"
                    )

                    # CRITICAL: Finalize BEFORE cleanup to release file locks
                    self._finalize()

                    self.socket_client.emit(
                        "file_processing_success",
                        {
                            "filename": file_basename,
                            "instrument": instrument,
                        },
                    )

                    # Success: delete file and clear context
                    self._cleanup_successful_file(self.file_to_process, file_basename)

                except Exception as e:
                    error_msg = str(e)
                    runtime.logger.error(
                        f"Failed to process file {Path(self.file_to_process).name}: {e}\n{traceback.format_exc()}"
                    )

                    # CRITICAL: Finalize BEFORE error emission to ensure file is closed
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
                runtime.logger.error(
                    f"Unexpected error in {self.__class__.__name__}: {e}"
                )
                if self.file_to_process is not None and file_basename is not None:
                    # Ensure finalize is called before emission
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
        runtime.logger.info(f"Exiting {self.__class__.__name__} ({self.name})")
