from abc import ABC, abstractmethod
import asyncio
import os
import math
from concurrent.futures import ProcessPoolExecutor
from typing import Iterable, Literal
import numpy as np
from scipy.signal._peak_finding_utils import _select_by_peak_distance
import xarray
import dask
from mascope_match.params import (
    ORBI_FITTING_THRESHOLD,
    TOF_FITTING_THRESHOLD,
)
from mascope_file.name import (
    get_sample_file_type,
)
from mascope_file.io import (
    load_array,
    load_file,
    read_props,
    write_peaks,
)

from mascope_signal.compute import (
    get_sum_signal,
    get_peak_profiles,
    get_scan_timestamps,
    get_orbi_centroids,
)
from mascope_signal.fitting import (
    fit_n_peaks,
    calculate_peak_area,
    SIGMA_MULTIPLIER,
)
from mascope_signal.runtime import runtime

# Restrict large chunks for dask
dask.config.set(**{"array.slicing.split_large_chunks": True})

# Set up a global ProcessPoolExecutor
cpu_cores = os.cpu_count()
max_workers = max(1, cpu_cores // 2)
EXECUTOR = ProcessPoolExecutor(max_workers=max_workers)

# Define the delta m/z around unit masses for peak detection
DMZ = 0.5


class PeakDetectionError(Exception):
    """Custom exception for peak detection errors."""

    pass


class BasePeakDetector(ABC):
    def __init__(
        self, filename: str, instrument_functions: tuple, u_list: Iterable[float] = None
    ):
        self._filename = filename
        self._peak_shape, self._resolution_function = instrument_functions

        self._u_list = u_list
        self._sample_file_props = read_props(self._filename)
        self._sum_signal = get_sum_signal(self._filename)

    def _load_old_peaks(self, if_exists):
        """Helper function to load old peaks from file if they exist"""
        if if_exists not in ["fail", "append", "replace"]:
            raise PeakDetectionError(
                """
                Argument 'if_exists' must be one of 'fail', 'append', 'replace'
                """
            )
        try:
            peak_heights = load_array(self._filename, "peak_heights").peak_heights
            peak_areas = load_array(self._filename, "peak_areas").peak_areas
        except FileNotFoundError:
            peak_heights, peak_areas = None, None

        old_peak_mzs, old_peak_areas, old_peak_heights = [], [], []

        if peak_areas is not None and if_exists != "replace":

            runtime.logger.debug(f"Access peak data from {self._filename}")

            if get_sample_file_type(self._filename) in ["tof_zarr", "orbi_zarr"]:
                # Drop nans for old files containing signal as zarr
                peak_areas = peak_areas.dropna(dim="mz")
                peak_heights = peak_heights.dropna(dim="mz")

            # Get previously fitted unit masses
            old_peak_mzs = peak_areas.mz.values.tolist()

            runtime.logger.debug(
                "Getting sums of previously fitted peak areas and heights"
            )
            old_peak_areas = peak_areas.sum(dim="time").compute().values.tolist()
            old_peak_heights = peak_heights.sum(dim="time").compute().values.tolist()

        return old_peak_mzs, old_peak_areas, old_peak_heights

    def _update_u_list(self, if_exists, old_peak_mzs):
        """Helper function to update u_list based on existing peaks and if_exists option"""
        mz_top = self._sample_file_props["range"][1]

        if u_list_not_provided := self._u_list is None:
            # Fit all peaks
            self._u_list = np.arange(10, np.floor(mz_top) + 1)
        else:
            # Covert to numpy and filter out too large values
            self._u_list = np.asarray(self._u_list)
            self._u_list = self._u_list[self._u_list <= mz_top]

        u_list_fitted = np.unique(np.round(old_peak_mzs))
        has_old_peaks = len(old_peak_mzs) > 0

        match if_exists:
            case "fail":
                if has_old_peaks:
                    raise PeakDetectionError(
                        "if_exists set to 'fail' but peak data exists!"
                    )
            case "replace":
                if has_old_peaks:
                    runtime.logger.warning(
                        "Old peaks will be overwritten as if_exists is set to 'replace'"
                    )
            case "append":
                # Only fit unit masses not already fitted
                self._u_list = np.setdiff1d(self._u_list, u_list_fitted)
            case _:
                raise PeakDetectionError(
                    "Argument 'if_exists' must be 'fail', 'append' or 'replace'"
                )

    def _validate_u_list(self):
        """Helper function to validate u_list and log info
        returns True if there are unit masses to fit, False otherwise
        """
        if self._u_list.size == 0:
            # Nothing to fit
            runtime.logger.info("Nothing to fit")
            return False
        runtime.logger.info(f"Fitting {self._u_list.size} unit masses")
        return True

    def _sort_and_filter_peaks(
        self,
        all_peak_mzs: np.ndarray,
        all_peak_areas: np.ndarray,
        all_peak_heights: np.ndarray,
    ) -> tuple:
        """Helper function to sort and filter fitted peak data"""
        # Sort fitted peaks by m/z
        sorted_peak_ind = np.argsort(all_peak_mzs)
        all_peak_mzs = all_peak_mzs[sorted_peak_ind]
        all_peak_areas = all_peak_areas[sorted_peak_ind]
        all_peak_heights = all_peak_heights[sorted_peak_ind]

        # lmfit returns peaks with negative or zero heights, which are not valid
        # filter out zero height peaks to prevent division by zero in peak profiles
        peak_mz_coord = self._sum_signal.mz.sel(
            mz=all_peak_mzs,
            method="nearest",
        )
        valid_indices = (
            self._sum_signal.sel(mz=peak_mz_coord, method="nearest").values > 0
        )
        peak_mz_coord = peak_mz_coord[valid_indices]
        all_peak_mzs = all_peak_mzs[valid_indices]
        all_peak_areas = all_peak_areas[valid_indices]
        all_peak_heights = all_peak_heights[valid_indices]

        # Remove duplicate peaks if any
        _, unique_peak_index = np.unique(peak_mz_coord, return_index=True)
        peak_mzs = all_peak_mzs[unique_peak_index]
        peak_areas = all_peak_areas[unique_peak_index]
        peak_heights = all_peak_heights[unique_peak_index]

        return peak_mzs, peak_areas, peak_heights

    def _calculate_peak_profiles(
        self,
        all_peak_mzs: np.ndarray,
        peak_areas: np.ndarray,
        peak_heights: np.ndarray,
    ) -> tuple:
        """Helper function to calculate peak profiles in detect_peaks"""
        # Get the tof values corresponding to the peak mzs
        mz_axis = self._sum_signal.mz.values
        # Interpolate the index (tof) for each peak m/z
        unique_tofs = np.interp(all_peak_mzs, mz_axis, np.arange(len(mz_axis)))

        peak_profiles = get_peak_profiles(self._filename, all_peak_mzs).assign_coords(
            tof=("mz", unique_tofs)
        )

        # Check if peak_profiles is empty along "time" or "mz"
        if (
            peak_profiles.sizes.get("time", 0) == 0
            or peak_profiles.sizes.get("mz", 0) == 0
        ):
            # No data to process, return empty arrays with correct shapes
            peak_profiles_area = peak_profiles.copy(
                data=np.zeros_like(peak_profiles.values)
            )
            peak_profiles_height = peak_profiles.copy(
                data=np.zeros_like(peak_profiles.values)
            )
            return peak_profiles_area, peak_profiles_height

        # NOTE: Instead of filtering out peaks with non-consecutive scans
        # we now remove peaks that have signal in only one scan for a given mz value (see issue #1043).
        def has_more_than_one_positive(arr):
            # arr is a 1D numpy array for a single mz value along time
            return np.sum(arr > 0) > 1

        # Apply along mz axis (i.e., for each mz, check along time)
        has_more_than_one_positive_mask = peak_profiles.reduce(
            lambda x, axis: np.apply_along_axis(has_more_than_one_positive, axis, x),
            dim="time",
        ).values

        # Filter out mz values that do not have consecutive positive values
        peak_profiles = peak_profiles.isel(mz=has_more_than_one_positive_mask)

        peak_areas = peak_areas[has_more_than_one_positive_mask]
        peak_heights = peak_heights[has_more_than_one_positive_mask]

        # Normalize peak profile intensities to 1
        peak_profiles_norm = peak_profiles / peak_profiles.sum(dim="time")
        peak_profiles_norm = peak_profiles_norm.fillna(0)

        # Restore peak profiles intensities using peak areas and heights of the fitted peaks,
        # that are, presumably, the correct integral of the peak profiles
        peak_profiles_area = peak_profiles_norm * peak_areas.reshape(-1, 1)
        peak_profiles_height = peak_profiles_norm * peak_heights.reshape(-1, 1)

        return peak_profiles_area, peak_profiles_height

    def _finalize(self, all_peak_mzs, all_peak_areas, all_peak_heights, if_exists):
        """Helper function to finalize peak detection by:
        - sorting
        - filtering
        - calculating profiles
        - writing to file
        """
        peak_mzs, peak_areas, peak_heights = self._sort_and_filter_peaks(
            all_peak_mzs, all_peak_areas, all_peak_heights
        )

        runtime.logger.debug("Computing peak profiles...")
        peak_profiles_area, peak_profiles_height = self._calculate_peak_profiles(
            peak_mzs, peak_areas, peak_heights
        )

        runtime.logger.info(f"Writing peaks to file {self._filename}")

        overwrite_peak_dataset = if_exists in {"append", "replace"}
        write_peaks(
            peak_profiles_area,
            peak_profiles_height,
            self._filename,
            overwrite_peak_dataset,
        )

        runtime.logger.info("Complete")
        sample_file_data = load_file(
            self._filename,
            vars=["peak_areas", "peak_heights"],
        )
        return sample_file_data

    @abstractmethod
    async def detect_peaks(
        self, if_exists: Literal["fail", "append", "replace"] = "fail"
    ):
        raise NotImplementedError("Subclasses must implement detect_peaks method")


class OrbiPeakDetector(BasePeakDetector):
    async def detect_peaks(
        self, if_exists: Literal["fail", "append", "replace"] = "fail", **kwargs
    ):
        """Detect peaks in the summed Orbitrap spectrum around each unit mass in u_list.

        :param if_exists: What to do if peak data already exists in the file.
        :type if_exists: Literal["fail", "append", "replace"], optional
        :return: Sample file data with updated peak information
        :rtype: xarray.Dataset
        """
        old_peak_mzs, old_peak_areas, old_peak_heights = self._load_old_peaks(if_exists)

        self._update_u_list(if_exists, old_peak_mzs)
        no_peaks_to_fit = not self._validate_u_list()
        if no_peaks_to_fit:
            # Nothing to fit, return existing data
            sample_file_data = load_file(
                self._filename,
                vars=["peak_areas", "peak_heights"],
            )
            return sample_file_data

        runtime.logger.debug("Reading centroids from the Thermo file...")
        # Get CALIBRATED centroids
        new_peak_mzs, new_peak_heights, resolutions, signal_to_noise = (
            get_orbi_centroids(self._filename, self._u_list)
        )

        runtime.logger.debug("Filter centroids by height and resolution...")
        new_peak_mzs, new_peak_heights, resolutions = self._filter_centroids(
            new_peak_mzs, new_peak_heights, resolutions, signal_to_noise
        )

        new_peak_areas = []
        runtime.logger.debug("Computing peak areas...")
        mz_arr = self._sum_signal.mz.values

        # Precompute all mz ranges for peak area calculation
        sigmas = new_peak_mzs / resolutions / SIGMA_MULTIPLIER
        mz_mins = new_peak_mzs - 3 * sigmas
        mz_maxs = new_peak_mzs + 3 * sigmas
        left_indices = np.searchsorted(mz_arr, mz_mins, side="left")
        right_indices = np.searchsorted(mz_arr, mz_maxs, side="right")

        new_peak_areas = [
            calculate_peak_area(
                mz_arr[left_indices[i] : right_indices[i]],
                self._peak_shape,
                (new_peak_mzs[i], new_peak_heights[i], resolutions[i]),
                sample_interval=None,
            )
            for i in range(len(new_peak_mzs))
        ]

        if if_exists == "append":
            # Append new peaks to the old ones
            all_peak_mzs = np.concatenate([old_peak_mzs, new_peak_mzs])
            all_peak_areas = np.concatenate([old_peak_areas, new_peak_areas])
            all_peak_heights = np.concatenate([old_peak_heights, new_peak_heights])
        else:
            # Use only new peaks
            all_peak_mzs = np.array(new_peak_mzs)
            all_peak_areas = np.array(new_peak_areas)
            all_peak_heights = np.array(new_peak_heights)

        sample_file_data = self._finalize(
            all_peak_mzs, all_peak_areas, all_peak_heights, if_exists
        )
        return sample_file_data

    def _filter_centroids(
        self,
        peak_mzs: np.ndarray,
        peak_heights: np.ndarray,
        resolutions: np.ndarray,
        signal_to_noise: np.ndarray,
        signal_to_noise_threshold: int = 3,
    ) -> tuple:
        """Filter centroids less than 1 count and with the S/N ratio less than signal_to_noise_threshold.

        # NOTE: Filtering by resolution and height was removed, see issue #1043
        """
        runtime.logger.debug(f"Found {len(peak_mzs)} peaks")

        # Filter out peaks with signal to noise ratio less than signal_to_noise_threshold
        sn_mask = signal_to_noise >= signal_to_noise_threshold
        peak_mzs = peak_mzs[sn_mask]
        peak_heights = peak_heights[sn_mask]
        resolutions = resolutions[sn_mask]

        runtime.logger.debug(
            f"{len(peak_mzs)} peaks left after filtering by signal to noise ratio >= {signal_to_noise_threshold}"
        )

        if peak_mzs.size == 0:
            runtime.logger.info("No new valid peaks found after filtering by height.")
            return peak_mzs, peak_heights, resolutions

        return peak_mzs, peak_heights, resolutions

    def _finalize(self, all_peak_mzs, all_peak_areas, all_peak_heights, if_exists):
        """Helper function to finalize peak detection by:
        - sorting
        - filtering
        - calculating profiles
        - writing to file
        """
        peak_mzs, peak_areas, peak_heights = self._sort_and_filter_peaks(
            all_peak_mzs, all_peak_areas, all_peak_heights
        )

        runtime.logger.debug("Computing peak profiles...")
        peak_profiles_area, peak_profiles_height = self._calculate_peak_profiles(
            peak_mzs, peak_areas, peak_heights
        )

        runtime.logger.info(f"Writing peaks to file {self._filename}")

        overwrite_peak_dataset = if_exists in {"append", "replace"}
        write_peaks(
            peak_profiles_area,
            peak_profiles_height,
            self._filename,
            overwrite_peak_dataset,
        )

        runtime.logger.info("Complete")
        sample_file_data = load_file(
            self._filename,
            vars=["peak_areas", "peak_heights"],
        )
        return sample_file_data


class TofPeakDetector(BasePeakDetector):
    async def detect_peaks(
        self,
        if_exists: Literal["fail", "append", "replace"] = "fail",
        max_n_peaks: int = 5,
        **kwargs,
    ) -> xarray.Dataset:
        """Detect peaks in the summed TOF spectrum around each unit mass in u_list.

        :param if_exists: What to do if peak data already exists in the file.
        :type if_exists: Literal["fail", "append", "replace"], optional
        :param max_n_peaks: Maximum number of peaks to fit per unit mass, by default 5
        :type max_n_peaks: int, optional
        :return: Sample file data with updated peak information
        :rtype: xarray.Dataset
        """
        old_peak_mzs, old_peak_areas, old_peak_heights = self._load_old_peaks(if_exists)
        self._update_u_list(if_exists, old_peak_mzs)
        no_peaks_to_fit = not self._validate_u_list()
        if no_peaks_to_fit:
            # Nothing to fit, return existing data
            sample_file_data = load_file(
                self._filename,
                vars=["peak_areas", "peak_heights"],
            )
            return sample_file_data
        self._sample_interval = self._sample_file_props.get("sample_interval", 0.25)
        specs_to_fit = self._segment_spectrum_for_fitting()

        loop = asyncio.get_event_loop()

        # Fill in asynchronous operations
        futures = [
            loop.run_in_executor(
                EXECUTOR,
                fit_n_peaks,
                mz_to_fit,
                spec_to_fit,
                self._peak_shape,
                self._resolution_function,
                self.peak_fitting_threshold,
                self._sample_interval,
                max_n_peaks,
            )
            for mz_to_fit, spec_to_fit in specs_to_fit
        ]

        new_peaks = []
        last_progress = None
        fit_warnings = set()
        runtime.logger.debug("Run peak detection")
        for i, future in enumerate(asyncio.as_completed(futures)):
            fit, peaks, captured_warnings = await future
            if fit:
                new_peaks.extend(peaks)
            for warning in captured_warnings:
                fit_warnings.add(warning)
            progress = 100 * (i + 1) / len(futures)
            rounded_progress = math.floor(progress / 10) * 10
            if rounded_progress != last_progress:
                runtime.logger.info(f"Peak detection progress: {rounded_progress}%")
            last_progress = rounded_progress

        # Log unique warnings
        for warning in fit_warnings:
            runtime.logger.debug(f"Peak detection warning: {warning}")

        if len(new_peaks) > 0:
            new_peak_mzs, new_peak_heights, new_peak_areas = zip(
                *[(p[0], p[1], p[3]) for p in new_peaks]
            )
        else:
            # Nothing was fitted
            new_peak_mzs, new_peak_heights, new_peak_areas = [], [], []

        if if_exists == "append":
            # Append new peaks to the old ones
            all_peak_mzs = np.concatenate([old_peak_mzs, new_peak_mzs])
            all_peak_areas = np.concatenate([old_peak_areas, new_peak_areas])
            all_peak_heights = np.concatenate([old_peak_heights, new_peak_heights])
        else:
            # Use only new peaks
            all_peak_mzs = np.array(new_peak_mzs)
            all_peak_areas = np.array(new_peak_areas)
            all_peak_heights = np.array(new_peak_heights)

        sample_file_data = self._finalize(
            all_peak_mzs, all_peak_areas, all_peak_heights, if_exists
        )
        return sample_file_data

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
            for u in self._u_list
        ]
        return specs_to_fit


class OrbiZarrPeakDetector(TofPeakDetector):
    def _segment_spectrum_for_fitting(self):
        """Segment the summed Orbi spectrum into chunks around each unit mass in u_list"""
        runtime.logger.debug("Segment Orbi spectrum for peak detection")
        sum_signal_mz = self._sum_signal.mz.values
        sum_signal = self._sum_signal.values
        # Stack mass ranges
        u_range = np.vstack([self._u_list - DMZ, self._u_list + DMZ])
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
        threshold = n_scans = get_scan_timestamps(self._filename).size
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


class TofZarrPeakDetector(TofPeakDetector):
    pass


def get_peak_detector(
    filename: str,
    instrument_functions: tuple,
    u_list: Iterable[float] = None,
):
    """Factory function to get the appropriate peak detector based on the sample file type.

    :param filename: Path to the sample file.
    :type filename: str
    :param instrument_functions: Tuple containing peak shape and resolution function.
    :type instrument_functions: tuple
    :param u_list: List of unit masses to fit, defaults to None.
    :type u_list: Iterable[float], optional
    :raises PeakDetectionError: If the sample file type is unsupported.
    :return: An instance of the appropriate peak detector.
    :rtype: BasePeakDetector
    """
    sample_file_type = get_sample_file_type(filename)
    match sample_file_type:
        case "orbi_raw":
            return OrbiPeakDetector(filename, instrument_functions, u_list)
        case "tof_h5":
            return TofPeakDetector(filename, instrument_functions, u_list)
        case "orbi_zarr":
            return OrbiZarrPeakDetector(filename, instrument_functions, u_list)
        case "tof_zarr":
            return TofZarrPeakDetector(filename, instrument_functions, u_list)
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
    # Filter by m/z and time ranges
    if mz_range is not None:
        peaks = peaks.sel(mz=slice(*mz_range))
    if t_range is not None:
        peaks = peaks.sel(time=slice(*t_range))

    peaks = peaks.dropna(dim="mz", how="all")

    # Compute peak intensities
    if "time" in peaks.dims:
        peak_intensities = peaks.sum(dim="time").values
    else:
        peak_intensities = peaks.values

    keep = np.ones(len(peaks), dtype=bool)

    # Filter by intensity
    if intensity is not None:
        keep &= peak_intensities > intensity

    # Filter by distance
    if distance is not None:
        peak_indices = peaks.tof.values
        keep &= _select_by_peak_distance(
            peak_indices.astype(np.intp),
            peak_intensities.astype(np.float64),
            distance,
        )

    # Return filtered peaks
    filtered = peaks[keep]
    return filtered.compute() if hasattr(filtered, "compute") else filtered


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
    sample_file_type = get_sample_file_type(sample_file.props["filename"])
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
