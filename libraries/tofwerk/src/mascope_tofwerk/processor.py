# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import h5py
import numpy as np

from mascope_backend.api.new.instrument_configs.schemas import (
    PeakShape,
    InstrumentConfigFitParams,
)
from mascope_backend.api.new.instrument_configs.service import fit_instrument_functions
from mascope_backend.file_converter.base_processor import (
    BaseFileProcessor,
    SampleFileProps,
)


class H5Processor(BaseFileProcessor):
    """Read and process TOF h5 files"""

    def __init__(self, socket_client, file_queue, shutdown_event):
        super().__init__(
            socket_client=socket_client,
            file_queue=file_queue,
            shutdown_event=shutdown_event,
        )
        self.h5 = None  # The h5 file reference

    def _open_file(self, file_path: str) -> None:
        """Open h5 file for processing."""
        self.h5 = h5py.File(file_path, "r")
        self.file_handle = self.h5

    def _close_file(self) -> None:
        """Close h5 file and clean up resources."""
        if self.h5:
            self.h5.close()
            self.h5 = None

    @property
    def file_extension(self) -> str:
        """Get the file extension for h5 files

        :return: File extension
        :rtype: str
        """
        return ".h5"

    @property
    def filename(self) -> str:
        """Get the processed filename."""
        return self._strip_filepath(self.file_to_process)

    @property
    def interval(self) -> float:
        """Mean measurement interval in seconds, i.e. length of one spectrum in the sample

        :return: Measurement interval [s]
        :rtype: float
        """
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
    def method_file(self) -> str:
        """TofDaq Recorder configuration file name used in the acquisition.

        :return: Configuration file name
        :rtype: str
        """
        method_file = self.h5.attrs["Configuration File"]
        return (
            method_file.decode() if isinstance(method_file, bytes) else str(method_file)
        ).strip()

    @property
    def mz_calibration(self) -> dict:
        """Mass calibration properties

        :return: Mass calibration properties
        :rtype: dict
        """
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
    def range(self) -> list:
        """m/z range of the sample file

        :return: m/z range
        :rtype: list
        """
        # Return a list of 1st and last m/z values
        return self.h5["FullSpectra"]["MassAxis"][[0, -1]].tolist()

    @property
    def polarity(self) -> str:
        """Polarity option in the sample file.

        :return: '-' for negative, '+' for positive
        :rtype: str
        """
        ion_mode = self.h5.attrs["IonMode"]
        ion_mode_str = (
            ion_mode.decode() if isinstance(ion_mode, bytes) else str(ion_mode)
        )
        ion_mode_str = ion_mode_str.strip().lower()
        if ion_mode_str == "negative":
            return "-"
        elif ion_mode_str == "positive":
            return "+"

    @property
    def sample_interval(self) -> float:
        """Sample interval in nanoseconds

        :return: Sample interval [ns]
        :rtype: float
        """
        return float(
            self.h5["FullSpectra"].attrs["SampleInterval"][0] * 1e9
        )  # [s]->[ns]

    @property
    def single_ion_signal(self) -> float:
        """Single ion signal [mV*ns/ion]

        :return: Single ion signal [mV*ns/ion]
        :rtype: float
        """
        return float(self.h5["FullSpectra"].attrs["Single Ion Signal"][0])

    @property
    def timestamp(self) -> str:
        """Timestamp in isoformat, local timezone

        :return: Timestamp
        :rtype: str
        """
        filetime = float(self.h5["TimingData"].attrs["AcquisitionTimeZero"][0])
        # Windows FILETIME ticks: 100-nanosecond intervals since 1601-01-01
        epoch = datetime(1601, 1, 1)
        python_datetime = epoch + timedelta(
            microseconds=filetime // 10, seconds=self.utc_offset
        )
        # Omit microseconds
        python_datetime = python_datetime.replace(microsecond=0)
        return python_datetime.isoformat()

    @property
    def utc_offset(self) -> float:
        """UTC offset in seconds

        :return: UTC offset in seconds
        :rtype: float
        """
        return float(self.h5["TimingData"].attrs["LocalTimeOffsetToUTC"][0]) * 3600.0

    def _process_instrument_config(
        self, sample_file_props: SampleFileProps
    ) -> tuple[any, any, any, any]:
        """Fit instrument functions"""
        dmz = 0.5
        fit_params = InstrumentConfigFitParams()
        (
            peakshape_numpy,
            resolution_function_partial,
            _,
        ) = fit_instrument_functions(
            sample_file_props.filename, r_sq_thres=fit_params.threshold, dmz=dmz
        )

        # Convert peakshape to lists to be serialized
        peakshape = PeakShape(
            x=peakshape_numpy["x"].tolist(), y=peakshape_numpy["y"].tolist()
        )

        # Get resolution function coefficients
        partial_coefficients = (
            resolution_function_partial.keywords  # pylint: disable=no-member
        )
        resolution_function = [partial_coefficients["a"], partial_coefficients["b"]]

        return (
            peakshape,
            resolution_function,
            peakshape_numpy,
            resolution_function_partial,
        )
