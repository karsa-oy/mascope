import asyncio
import math
import os
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor

import dask
import dask.array as da
import numpy as np
import pandas as pd
import xarray
from scipy.signal._peak_finding_utils import _select_by_peak_distance

import mascope_file.io as m_io
import mascope_file.name as m_name
import mascope_signal.compute as m_compute
import mascope_signal.fitting as m_fitting
from mascope_backend.db.id import gen_id
from mascope_match.params import (
    ORBI_FITTING_THRESHOLD,
    TOF_FITTING_THRESHOLD,
)
from mascope_signal.runtime import runtime
from mascope_tools.alignment.utils import flag_satellite_peaks


# Restrict large chunks for dask
dask.config.set(**{"array.slicing.split_large_chunks": True})

cpu_cores = os.cpu_count()
max_workers = max(1, cpu_cores // 2)
_EXECUTOR: ProcessPoolExecutor | None = None
_EXECUTOR_LOCK = threading.Lock()


def _get_executor() -> ProcessPoolExecutor:
    """Get or create the global ProcessPoolExecutor (lazy initialization).

    The external check makes sure we don't acquire the lock unnecessarily
    after the executor is created.

    The internal check is needed to avoid race condition where multiple
    threads pass the first check before the executor is initialized.
    """
    global _EXECUTOR
    if _EXECUTOR is None:
        with _EXECUTOR_LOCK:
            if _EXECUTOR is None:
                _EXECUTOR = ProcessPoolExecutor(max_workers=max_workers)
    return _EXECUTOR


# Define the delta m/z around unit masses for peak detection
DMZ = 0.5
SIGNAL_TO_NOISE_THRESHOLD = 3

PEAK_ID_LENGTH = 20


class PeakDetectionError(Exception):
    """Custom exception for peak detection errors."""

    pass


class BasePeakDetector(ABC):
    def __init__(self, filename: str, instrument_functions: tuple):
        self._filename = filename
        self._peak_shape, self._resolution_function = instrument_functions

        self._sample_file_props = m_io.read_props(self._filename)
        self._sum_signal = m_compute.get_sum_signal(self._filename)

        self.peak_timeseries = None

    @property
    def u_list(self):
        """List of unique integer m/z values in the summed spectrum"""
        mz_values = self._sum_signal.mz.values
        u_list = np.unique(mz_values.astype(int))
        return u_list

    def _allocate_peak_timeseries(self, peaks: xarray.Dataset) -> xarray.Dataset:
        """Allocate peak timeseries dataset structure."""
        # Get the tof values corresponding to the peak mzs
        mz_axis = self._sum_signal.mz.values
        peak_mzs = peaks.mz.values
        # Interpolate the index (tof) for each peak m/z
        unique_tofs = np.interp(peak_mzs, mz_axis, np.arange(len(mz_axis)))

        time_coord = m_compute.get_scan_timestamps(self._filename)
        peak_ids = [gen_id(PEAK_ID_LENGTH) for _ in range(peaks.mz.size)]
        data_coords = {
            "mz": peaks.mz,
            "time": time_coord,
            "tof": (("mz"), unique_tofs),
            "peak_id": (("mz"), peak_ids),
        }

        # Allocate dask arrays for peak areas and heights with NaN initialization
        # to save memory
        data_shape = (peaks.mz.size, time_coord.size)
        peak_areas = da.full(data_shape, np.nan, dtype=np.float64)
        peak_heights = da.full(data_shape, np.nan, dtype=np.float64)
        peak_timeseries_computed = da.full(peaks.mz.size, False, dtype=bool)
        data_vars = {
            "peak_areas": (("mz", "time"), peak_areas),
            "peak_heights": (("mz", "time"), peak_heights),
            "is_timeseries_computed": (("mz"), peak_timeseries_computed),
        }

        peak_timeseries = xarray.Dataset(
            data_vars=data_vars,
            coords=data_coords,
        )
        self.peak_timeseries = xarray.merge([peak_timeseries, peaks])

    async def write_peaks_to_zarr(self, overwrite=True):
        if self.peak_timeseries is None:
            raise PeakDetectionError("No peak timeseries to write to zarr.")

        runtime.logger.info("Writing peak timeseries to the sample file...")
        await m_io.write_peaks(
            self.peak_timeseries,
            self._filename,
            overwrite=overwrite,
        )
        runtime.logger.info("Writing peak timeseries completed.")

    @abstractmethod
    async def detect_peaks(
        self, progress_callback: Callable[[int], None] | None = None
    ):
        raise NotImplementedError("Subclasses must implement detect_peaks method")

    @abstractmethod
    def _flag_weak_peaks(self):
        raise NotImplementedError("Subclasses must implement _flag_weak_peaks method")

    @abstractmethod
    def _flag_satellite_peaks(self):
        raise NotImplementedError(
            "Subclasses must implement _flag_satellite_peaks method"
        )


class OrbiPeakDetector(BasePeakDetector):
    async def detect_peaks(
        self, progress_callback: Callable[[int], None] | None = None, **kwargs
    ):
        """Detect peaks in the summed Orbitrap spectrum.

        :param progress_callback: Optional callback invoked with progress percentage (0-100).
        :type progress_callback: Callable[[int], None] | None
        :return: Sample file data with updated peak information
        :rtype: xarray.Dataset
        """
        # Handle None progress callback by using a no-op function
        progress_callback = progress_callback or (lambda progress: None)

        progress_callback(10)
        runtime.logger.debug("Reading centroids from the Thermo file...")
        # Get CALIBRATED centroids
        try:
            peaks_pos = await self._extract_peaks_for_polarity("+")
        except Exception as e:
            runtime.logger.debug(f"No positive polarity data found: {e}")
            peaks_pos = None
        try:
            peaks_neg = await self._extract_peaks_for_polarity("-")
        except Exception as e:
            runtime.logger.debug(f"No negative polarity data found: {e}")
            peaks_neg = None

        datasets = [ds for ds in [peaks_pos, peaks_neg] if ds is not None]
        peaks = xarray.concat(datasets, dim="mz").sortby("mz")

        progress_callback(80)
        runtime.logger.debug("Computing peak timeseries...")
        self._allocate_peak_timeseries(peaks)
        self._flag_weak_peaks()
        self._flag_satellite_peaks()
        progress_callback(100)

    async def _extract_peaks_for_polarity(self, polarity: str) -> xarray.Dataset:
        """A workaround to extract peaks for a given polarity from Thermo Orbitrap files."""
        (
            peak_mzs,
            peak_heights,
            resolutions,
            signal_to_noise,
        ) = await m_compute.get_orbi_centroids(self._filename, polarity=polarity)

        sigmas = peak_mzs / resolutions / m_fitting.SIGMA_MULTIPLIER
        mz_mins = peak_mzs - 3 * sigmas
        mz_maxs = peak_mzs + 3 * sigmas
        mz_arr = self._sum_signal.mz.values
        left_indices = np.searchsorted(mz_arr, mz_mins, side="left")
        right_indices = np.searchsorted(mz_arr, mz_maxs, side="right")

        peak_areas = np.array(
            [
                m_fitting.calculate_peak_area(
                    mz_arr[left_indices[i] : right_indices[i]],
                    self._peak_shape,
                    (peak_mzs[i], peak_heights[i], resolutions[i]),
                    sample_interval=None,
                )
                for i in range(len(peak_mzs))
            ]
        )

        return xarray.Dataset(
            {
                "sum_peak_areas": (("mz"), peak_areas),
                "sum_peak_heights": (("mz"), peak_heights),
                "signal_to_noise": (("mz"), signal_to_noise),
                "polarity": (("mz"), np.full(peak_mzs.shape, polarity)),
            }
        ).assign_coords(mz=("mz", peak_mzs))

    def _flag_weak_peaks(self):
        """Flag weak peaks based on signal-to-noise ratio."""
        low_snr = (
            self.peak_timeseries.signal_to_noise.values < SIGNAL_TO_NOISE_THRESHOLD
        )
        is_weak = low_snr
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_weak": (("mz"), is_weak)}
        )

    def _flag_satellite_peaks(self):
        peaks_df = pd.DataFrame(
            {
                "mz": self.peak_timeseries.mz.values,
                "intensity": self.peak_timeseries.sum_peak_heights.values,
            }
        )
        peaks_df = flag_satellite_peaks(peaks_df)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_satellite": (("mz"), peaks_df["is_satellite_peak"].values)}
        )


class TofPeakDetector(BasePeakDetector):
    async def detect_peaks(
        self,
        max_n_peaks: int = 5,
        progress_callback: Callable[[int], None] | None = None,
        **kwargs,
    ) -> xarray.Dataset:
        """Detect peaks in the summed TOF spectrum around each unit mass in u_list.

        :param max_n_peaks: Maximum number of peaks to fit per unit mass, by default 5
        :type max_n_peaks: int, optional
        :param progress_callback: Optional callback invoked with progress percentage (0-100).
        :type progress_callback: Callable[[int], None] | None
        :return: Sample file data with updated peak information
        :rtype: xarray.Dataset
        """
        # Handle None progress callback by using a no-op function
        progress_callback = progress_callback or (lambda progress: None)

        self._sample_interval = self._sample_file_props.get("sample_interval", 0.25)
        specs_to_fit = self._segment_spectrum_for_fitting()

        loop = asyncio.get_event_loop()
        executor = _get_executor()

        # Fill in asynchronous operations
        futures = [
            loop.run_in_executor(
                executor,
                m_fitting.fit_n_peaks,
                mz_chunk,
                spec_chunk,
                self._peak_shape,
                self._resolution_function,
                self.peak_fitting_threshold,
                self._sample_interval,
                max_n_peaks,
            )
            for mz_chunk, spec_chunk in specs_to_fit
        ]

        peaks = []
        last_progress = 0
        fit_warnings = set()
        runtime.logger.debug("Run peak detection")
        for i, future in enumerate(asyncio.as_completed(futures)):
            fit, detected_peaks, captured_warnings = await future
            if fit:
                peaks.extend(detected_peaks)
            for warning in captured_warnings:
                fit_warnings.add(warning)
            progress = 100 * (i + 1) / len(futures)
            rounded_progress = math.floor(progress / 10) * 10
            if rounded_progress != last_progress:
                runtime.logger.info(f"Peak detection progress: {rounded_progress}%")
                progress_callback(rounded_progress)
            last_progress = rounded_progress

        # Log unique warnings
        for warning in fit_warnings:
            runtime.logger.debug(f"Peak detection warning: {warning}")

        if len(peaks) > 0:
            peak_mzs, peak_heights, peak_areas = zip(
                *[(p[0], p[1], p[3]) for p in peaks]
            )
        else:
            # Nothing was fitted
            peak_mzs, peak_heights, peak_areas = [], [], []

        peak_mzs = np.array(peak_mzs)
        peak_heights = np.array(peak_heights)
        peak_areas = np.array(peak_areas)

        positive_mask = (peak_heights > 0) & (peak_areas > 0)
        peak_mzs = peak_mzs[positive_mask]
        peak_heights = peak_heights[positive_mask]
        peak_areas = peak_areas[positive_mask]
        polarity = m_compute.get_polarity_options(self._filename)
        signal_to_noise = self._compute_snr(peak_mzs, peak_heights)
        peaks = xarray.Dataset(
            {
                "sum_peak_areas": (("mz"), peak_areas),
                "sum_peak_heights": (("mz"), peak_heights),
                "signal_to_noise": (("mz"), signal_to_noise),
                "polarity": (("mz"), np.full(peak_mzs.shape, polarity)),
            }
        ).assign_coords(mz=("mz", peak_mzs))
        peaks = peaks.sortby("mz")

        runtime.logger.debug("Computing peak timeseries...")
        self._allocate_peak_timeseries(peaks)
        self._flag_weak_peaks()
        self._flag_satellite_peaks()

    @property
    def peak_fitting_threshold(self):
        return TOF_FITTING_THRESHOLD

    def _segment_spectrum_for_fitting(self):
        """Segment the summed TOF spectrum into chunks around each unit mass in u_list"""
        runtime.logger.debug("Segment TOF spectrum for peak detection")
        sum_mz = self._sum_signal.mz.values
        sum_values = self._sum_signal.values
        specs_to_fit = [
            (
                sum_mz[(sum_mz >= u - DMZ) & (sum_mz <= u + DMZ)],
                sum_values[(sum_mz >= u - DMZ) & (sum_mz <= u + DMZ)],
            )
            for u in self.u_list
        ]
        return specs_to_fit

    def _compute_snr(
        self,
        peak_mzs: np.ndarray,
        peak_heights: np.ndarray,
    ) -> np.ndarray:
        """Compute signal-to-noise ratio for given peaks

        :param peak_mzs: Fitted peak m/z values
        :type peak_mzs: np.ndarray
        :param peak_heights: Fitted peak heights
        :type peak_heights: np.ndarray
        :return: Signal-to-noise ratio array
        :rtype: np.ndarray
        """
        mz_axis = self._sum_signal.mz.values
        signal = self._sum_signal.values
        snr = np.empty(len(peak_mzs), dtype=np.float64)

        # Compute exclusion zone from the resolution function
        resolutions = self._resolution_function(peak_mzs)
        exclusion = peak_mzs / resolutions

        # Compute baseline window as 10 times the exclusion zone
        window = 10 * exclusion

        # Vectorized baseline window calculation
        left_min = peak_mzs - window
        left_max = peak_mzs - exclusion
        right_min = peak_mzs + exclusion
        right_max = peak_mzs + window

        # For each peak, select baseline regions and compute noise std
        for i in range(len(peak_mzs)):
            left_mask = (mz_axis >= left_min[i]) & (mz_axis <= left_max[i])
            right_mask = (mz_axis >= right_min[i]) & (mz_axis <= right_max[i])
            baseline = signal[left_mask | right_mask]
            # Use robust estimator if baseline is non-Gaussian
            noise_std = np.std(baseline) if baseline.size > 0 else np.nan
            snr[i] = peak_heights[i] / noise_std if noise_std > 0 else np.nan

        return snr

    def _flag_weak_peaks(self):
        """Flag weak peaks. Currently no weak peak criteria for TOF data."""
        is_weak = np.full(len(self.peak_timeseries.mz), False, dtype=bool)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_weak": (("mz"), is_weak)}
        )

    def _flag_satellite_peaks(self):
        """Flag satellite peaks. Currently no satellite peak criteria for TOF data."""
        is_satellite = np.full(len(self.peak_timeseries.mz), False, dtype=bool)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_satellite": (("mz"), is_satellite)}
        )


class OrbiZarrPeakDetector(TofPeakDetector):
    def _segment_spectrum_for_fitting(self):
        """Segment the summed Orbi spectrum into chunks around each unit mass in u_list"""
        runtime.logger.debug("Segment Orbi spectrum for peak detection")
        sum_signal_mz = self._sum_signal.mz.values
        sum_signal = self._sum_signal.values
        # Stack mass ranges
        u_range = np.vstack([self.u_list - DMZ, self.u_list + DMZ])
        # Broadcast the u_range array to have the same shape as mz
        u_range = u_range[:, :, np.newaxis]
        # Create boolean masks indicating which elements of spec fall within each range
        mask_u_list = (sum_signal_mz >= u_range[0]) & (sum_signal_mz <= u_range[1])
        mask_u_list = mask_u_list.any(axis=0)
        # Update mz and spec
        mz = sum_signal_mz[mask_u_list]
        sum_spec = sum_signal[mask_u_list]

        if sum_spec.size == 0:
            # Nothing to fit
            return []

        # Remove tiny noise from the sum spectrum
        threshold = n_scans = m_compute.get_scan_timestamps(  # noqa: F841
            self._filename
        ).size
        sum_spec[sum_spec < threshold] = 0
        # Get non-zero indices
        non_zero_indices = np.flatnonzero(sum_spec)
        if len(non_zero_indices) == 0:
            # Return an empty list if there are no non-zero indices
            return []
        # Split in chunks taking into account repeating zeros
        non_zero_indices = np.split(
            non_zero_indices, np.where(np.diff(non_zero_indices) > 2)[0] + 1
        )
        # Add zeros on chunk borders
        non_zero_indices = [
            np.concatenate(([chunk[0] - 1], chunk, [chunk[-1] + 1]))
            for chunk in non_zero_indices
        ]
        # Check wrong indices on the spectrum ends
        if non_zero_indices[0][0] < 0:
            # Remove negative index in the first chunk
            non_zero_indices[0] = non_zero_indices[0][1:]
        if non_zero_indices[-1][-1] == len(sum_spec):
            # Remove out-of-range index from the last chunk
            non_zero_indices[-1] = non_zero_indices[-1][:-1]
        # Remove short chunks
        non_zero_indices = [chunk for chunk in non_zero_indices if len(chunk) > 4]

        specs_to_fit = [(mz[chunk], sum_spec[chunk]) for chunk in non_zero_indices]

        return specs_to_fit

    @property
    def peak_fitting_threshold(self):
        return ORBI_FITTING_THRESHOLD

    def _flag_satellite_peaks(self):
        peaks_df = pd.DataFrame(
            {
                "mz": self.peak_timeseries.mz.values,
                "intensity": self.peak_timeseries.sum_peak_heights.values,
            }
        )
        peaks_df = flag_satellite_peaks(peaks_df)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_satellite": (("mz"), peaks_df["is_satellite_peak"].values)}
        )


class TofZarrPeakDetector(TofPeakDetector):
    pass


def compute_peaks(
    filename: str,
    instrument_functions: tuple,
    progress_callback: Callable[[int], None] | None = None,
):
    """Compute peaks for a sample file.

    :param filename: Path to the sample file.
    :type filename: str
    :param instrument_functions: Tuple containing peak shape and resolution function.
    :type instrument_functions: tuple
    :param progress_callback: Optional callback invoked with progress percentage (0-100).
    :type progress_callback: Callable[[int], None] | None
    """
    peak_detector = get_peak_detector(filename, instrument_functions)
    asyncio.run(peak_detector.detect_peaks(progress_callback=progress_callback))
    asyncio.run(peak_detector.write_peaks_to_zarr())


def get_peak_detector(
    filename: str,
    instrument_functions: tuple,
):
    """Factory function to get the appropriate peak detector based on the sample file type.

    :param filename: Path to the sample file.
    :type filename: str
    :param instrument_functions: Tuple containing peak shape and resolution function.
    :type instrument_functions: tuple
    :raises PeakDetectionError: If the sample file type is unsupported.
    :return: An instance of the appropriate peak detector.
    :rtype: BasePeakDetector
    """
    sample_file_type = m_name.get_sample_file_type(filename)
    match sample_file_type:
        case "orbi_raw":
            return OrbiPeakDetector(filename, instrument_functions)
        case "tof_h5":
            return TofPeakDetector(filename, instrument_functions)
        case "orbi_zarr":
            return OrbiZarrPeakDetector(filename, instrument_functions)
        case "tof_zarr":
            return TofZarrPeakDetector(filename, instrument_functions)
        case _:
            raise PeakDetectionError(
                f"Unsupported sample file type: {sample_file_type}"
            )


def filter_peaks(
    peaks: xarray.DataArray,
    mz_range: tuple = None,
    t_range: tuple = None,
    intensity: float = None,
    distance: float = None,
) -> xarray.DataArray:
    """
    Filter peaks by m/z range, time range, intensity, and minimum distance.

    :param peaks: Peak data array.
    :type peaks: xarray.DataArray
    :param mz_range: Tuple (min_mz, max_mz) to filter m/z, defaults to None.
    :type mz_range: tuple, optional
    :param t_range: Tuple (min_time, max_time) to filter time, defaults to None.
    :type t_range: tuple, optional
    :param intensity: Minimum intensity threshold, defaults to None.
    :type intensity: float, optional
    :param distance: Minimum distance between peaks, defaults to None.
    :type distance: float, optional
    :return: Filtered peaks as xarray.DataArray.
    :rtype: xarray.DataArray
    """
    # --- Lazy coordinate slicing ---
    if mz_range is not None:
        peaks = peaks.sel(mz=slice(*mz_range))
    if t_range is not None:
        peaks = peaks.sel(time=slice(*t_range))

    # Remove empty mz rows
    peaks = peaks.dropna(dim="mz", how="all")

    # --- Compute peak intensities ---
    if "time" in peaks.dims:
        peak_intensities = peaks.sum("time")
    else:
        peak_intensities = peaks

    # --- Intensity filtering ---
    if intensity is not None:
        peaks = peaks.where(peak_intensities > intensity, drop=True)
        peak_intensities = peak_intensities.where(
            peak_intensities > intensity, drop=True
        )

    # --- Distance filtering (here we need numpy arrays, so we materialize) ---
    if distance is not None:
        tof_vals = peaks["tof"].values.astype(np.intp)
        heights = peak_intensities.values.astype(np.float64)
        keep = _select_by_peak_distance(tof_vals, heights, distance)
        peaks = peaks.isel(mz=keep)

    return peaks


def get_peaks(sample_file: xarray.Dataset, intensity_mode="area"):
    """
    Retrieve peak data from a sample file.

    :param sample_file: Sample file dataset containing peak data.
    :type sample_file: xarray.Dataset
    :param intensity_mode: Which intensity to return, "area" or "height". Defaults to "area".
    :type intensity_mode: str, optional
    :raises ValueError: If intensity_mode is not "area" or "height".
    :return: Peak data array (areas or heights).
    :rtype: xarray.DataArray
    """
    if intensity_mode == "area":
        peaks = sample_file.peak_areas
    elif intensity_mode == "height":
        peaks = sample_file.peak_heights
    else:
        raise ValueError("intensity_mode must be either 'height' or 'area'")
    sample_file_type = m_name.get_sample_file_type(sample_file.props["filename"])
    if sample_file_type == "tof_zarr" or sample_file_type == "orbi_zarr":
        peaks = peaks.dropna(dim="mz", how="all")
    return peaks


def find_closest_indices(axis, values):
    # axis and values must be 1D numpy arrays
    idxs = np.searchsorted(axis, values)
    idxs = np.clip(idxs, 1, len(axis) - 1)
    left = axis[idxs - 1]
    right = axis[idxs]
    idxs -= values - left < right - values
    return idxs
