import asyncio
import os
import math
from concurrent.futures import ProcessPoolExecutor
from typing import Iterable
import numpy as np
from scipy.signal._peak_finding_utils import _select_by_peak_distance
from scipy.integrate import simpson
import xarray
import dask

from mascope_file.name import (
    get_sample_file_type,
    get_instrument_type,
)
from mascope_file.io import (
    load_array,
    load_file,
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


def calculate_signal_area(
    filename: str,
    mz_min: float,
    mz_max: float,
    sum_spectrum: xarray.DataArray = None,
    sample_interval: float = None,
) -> float:
    """Calculate signal area in an mz range

    Computes the area as "sum * sample interval" for TOF, and using Simpson's rule for Orbi

    :param filename: Filename of the sample file
    :type filename: str
    :param mz_min: m/z range minimum
    :type mz_min: float
    :param mz_max: m/z range maximum
    :type mz_max: float
    :param sum_spectrum: Sum spectrum array, defaults to None. If None, load from file.
    :type sum_spectrum: xarray.DataArray
    :param sample_interval: TOF sampling interval, optional, defaults to None
    :type sample_interval: float
    :return: Return signal area
    :rtype: float
    """
    if sum_spectrum is None:
        sum_spectrum = get_sum_signal(filename)
    instrument_type = get_instrument_type(filename)
    sum_spectrum_slice = sum_spectrum.sel(mz=slice(mz_min, mz_max))
    if sum_spectrum_slice.shape[0] == 0:
        # No signal in the specified mz range
        return 0
    if instrument_type == "tof":
        if sample_interval is None:
            raise ValueError(
                "Input argument 'sample_interval' must not be None when calculating signal area for TOF data"
            )
        return sum_spectrum_slice.sum(dim="mz").compute().item() * sample_interval
    else:
        # return sum signal full integral in mz space
        return simpson(y=sum_spectrum_slice.values, x=sum_spectrum_slice.mz.values)


def calculate_tic(filename: str) -> float:
    """Calculates the full integral of the signal in TOF or mz space
    depending on signal sampling interval availability in the sample file

    :param filename: name of the sample file
    :type filename: str
    :return: area under the sum signal
    :rtype: float
    """
    sum_spec = get_sum_signal(filename)
    instrument_type = get_instrument_type(filename)
    if instrument_type == "tof":
        # default 0.25 for backwards compatibility
        sample_interval = (
            load_file(filename, vars=[]).attrs["props"].get("sample_interval", 0.25)
        )
        # return sum signal full integral in tof space
        return sum_spec.sum(dim="mz").compute().item() * sample_interval
    else:
        raise RuntimeError("Calculating TIC for an Orbitrap file is not supported")


def segment_spec(sum_spec, threshold: float = 0) -> list:
    """Perform segmentation of Orbitrap spectrum

    :param sum_spec: sum of spectra along time dimension
    :type sum_spec: array-like
    :param threshold: threshold for noise removal, defaults to 0
    :type threshold: float
    :return: list of segment indices
    :rtype: list
    """
    # Remove tiny noise from the sum spectrum
    sum_spec[sum_spec < threshold] = 0
    # Get non-zero indices
    non_zero_indices = np.flatnonzero(sum_spec)
    if len(non_zero_indices) == 0:
        return []  # Return an empty list if there are no non-zero indices
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
    return non_zero_indices


async def detect_peaks(
    filename: str,
    instrument_functions: tuple,
    add_peak_threshold: float,
    u_list: Iterable[float] = None,
    max_n_peaks: int = 5,
    if_exists: str = "fail",  # 'fail', 'append', 'replace'
    dmz: float = 0.5,
    return_peak_mzs: bool = False,
    instrument_type: str = "tof",
) -> xarray.Dataset | tuple:
    """Detect peaks in a sample file sum spectrum

    :param filename: Sample file name
    :type filename: str
    :param instrument_functions: Peak shape and resolution function
    :type instrument_functions: tuple
    :param add_peak_threshold: Threshold for adding a new peak
    :type add_peak_threshold: float
    :param u_list: m/z values to fit, defaults to None
    :type u_list: Iterable[float], optional
    :param max_n_peaks: Max number of peaks per chunk, defaults to 5
    :type max_n_peaks: int, optional
    :param if_exists: Action if peak data exists, defaults to "fail"
    :type if_exists: str, optional
    :param return_peak_mzs: Return fitted peak m/z values, defaults to False
    :type return_peak_mzs: bool, optional
    :param instrument_type: Instrument type, defaults to "tof"
    :type instrument_type: str, optional
    :raises ValueError: if_exists is incorrect
    :raises FileExistsError: Peak data exists and if_exists is "fail"
    :return: Sample file data with peak data, with peak m/z values if return_peak_mzs is True
    :rtype: xarray.Dataset|tuple
    """
    runtime.logger.info(f"Detecting peaks for file {filename}")
    if if_exists not in ["fail", "append", "replace"]:
        raise ValueError(
            """
            Argument 'if_exists' must be one of 'fail', 'append', 'replace'
            """
        )
    peakshape, R = instrument_functions
    sample_file_props = load_file(filename, vars=[]).props
    sample_file_type = get_sample_file_type(filename)
    sum_signal = get_sum_signal(filename)

    # -- Get previously fitted peaks if they exist and list of unit masses to fit -- ##

    try:
        peak_heights_xarr = load_array(filename, "peak_heights").peak_heights
        peak_areas_xarr = load_array(filename, "peak_areas").peak_areas
    except FileNotFoundError:
        peak_heights_xarr, peak_areas_xarr = None, None

    mz_top = sample_file_props["range"][1]

    if u_list is None:
        # Fit all peaks
        u_list = np.arange(10, np.floor(mz_top) + 1)
    else:
        u_list = np.asarray(u_list)
        # Filter out too large values
        u_list = u_list[u_list <= mz_top]

    old_peak_mzs, old_peak_areas, old_peak_heights = [], [], []

    if peak_areas_xarr is not None and if_exists != "replace":
        if if_exists == "fail":
            raise FileExistsError("Peak data exists!")

        runtime.logger.debug(f"Access peak data from {filename}")

        if sample_file_type in ["tof_zarr", "orbi_zarr"]:
            # Drop nans for old files containing signal as zarr
            peak_areas_xarr = peak_areas_xarr.dropna(dim="mz")
            peak_heights_xarr = peak_heights_xarr.dropna(dim="mz")

        # Get previously fitted unit masses
        old_peak_mzs = peak_areas_xarr.mz.values.tolist()
        u_list_fitted = np.unique(np.round(old_peak_mzs))

        if if_exists == "append":
            # Only fit unit masses not already fitted
            u_list = np.setdiff1d(u_list, u_list_fitted)

        if u_list.size == 0:
            # Nothing to fit
            runtime.logger.info("Nothing to fit")
            return load_file(
                filename, vars=["peak_areas", "peak_heights", "sum_signal"]
            )

        runtime.logger.debug("Getting sums of previously fitted peak areas and heights")
        old_peak_areas = peak_areas_xarr.sum(dim="time").compute().values.tolist()
        old_peak_heights = peak_heights_xarr.sum(dim="time").compute().values.tolist()

    runtime.logger.info(f"Fitting {u_list.size} unit masses")

    # Sample interval for peak area calculation in counts vs TOF
    # default 0.25 for backwards compatibility
    sample_interval = (
        sample_file_props.get("sample_interval", 0.25)
        if instrument_type == "tof"
        else None
    )

    # -- Read centroids as peaks directly from RAW file for orbi_raw -- ##

    if sample_file_type == "orbi_raw":
        new_peak_mzs, new_peak_heights, resolutions = get_orbi_centroids(
            filename, u_list
        )
        runtime.logger.debug("The fitted peaks were read from the Thermo file")

        new_peak_areas = []
        runtime.logger.debug("Computing peak areas...")
        mz_arr = sum_signal.mz.values

        # Precompute all mz ranges for peak area calculation
        sigmas = new_peak_mzs / resolutions / SIGMA_MULTIPLIER
        mz_mins = new_peak_mzs - 3 * sigmas
        mz_maxs = new_peak_mzs + 3 * sigmas
        left_indices = np.searchsorted(mz_arr, mz_mins, side="left")
        right_indices = np.searchsorted(mz_arr, mz_maxs, side="right")

        new_peak_areas = [
            calculate_peak_area(
                mz_arr[left_indices[i] : right_indices[i]],
                peakshape,
                (new_peak_mzs[i], new_peak_heights[i], resolutions[i]),
                sample_interval,
            )
            for i in range(len(new_peak_mzs))
        ]

    # -- Fit peaks if sample_file_type is orbi_zarr, tof_zarr, tof_h5  -- ##

    if sample_file_type in ["orbi_zarr", "tof_zarr", "tof_h5"]:
        cpu_cores = os.cpu_count()
        max_workers = max(1, cpu_cores // 2)
        executor = ProcessPoolExecutor(max_workers=max_workers)
        loop = asyncio.get_event_loop()

        specs_to_fit = _segment_spectrum_for_fitting(
            filename, sample_file_type, sum_signal, u_list, dmz
        )

        # Fill in asynchronous operations
        futures = [
            loop.run_in_executor(
                executor,
                fit_n_peaks,
                mz_to_fit,
                spec_to_fit,
                peakshape,
                R(mz_to_fit.mean()),
                add_peak_threshold,
                sample_interval,
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

        executor.shutdown()

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

    ## -- Remove junk from the fitted peaks -- ##

    peak_mzs, peak_areas, peak_heights = _sort_and_filter_peaks(
        sum_signal, all_peak_mzs, all_peak_areas, all_peak_heights
    )

    ## -- Calculate and write peak profiles -- ##

    runtime.logger.debug("Computing peak profiles...")

    peak_profiles_area, peak_profiles_height = _calculate_peak_profiles(
        filename, peak_mzs, sum_signal, peak_areas, peak_heights
    )

    runtime.logger.info(f"Writing peaks to file {filename}")

    overwrite_peak_dataset = if_exists in {"append", "replace"}
    write_peaks(
        peak_profiles_area,
        peak_profiles_height,
        filename,
        overwrite_peak_dataset,
    )

    runtime.logger.info("Complete")
    sample_file_data = load_file(
        filename,
        vars=["peak_areas", "peak_heights", "sum_signal"],
    )
    if return_peak_mzs:
        return (sample_file_data, peak_mzs)
    return sample_file_data


def _segment_spectrum_for_fitting(
    filename: str,
    sample_file_type: str,
    sum_signal: xarray.DataArray,
    u_list: np.ndarray,
    dmz: float,
) -> list:
    """Helper function to segment spectrum for fitting in detect_peaks

    :param filename: Sample file name
    :type filename: str
    :param sample_file_type: Sample file type
    :type sample_file_type: str
    :param sum_signal: Sum signal array
    :type sum_signal: xarray.DataArray
    :param u_list: m/z values to fit
    :type u_list: np.ndarray
    :param dmz: m/z window width for peak detection
    :type dmz: float
    :return: List of tuples containing m/z and spectrum pairs to fit
    :rtype: list
    """
    if sample_file_type == "orbi_zarr":
        runtime.logger.debug("Segment Orbi spectrum for peak detection")
        # Stack mass ranges
        u_range = np.vstack([u_list - 0.5, u_list + 0.5])
        # Broadcast the u_range array to have the same shape as mz
        u_range = u_range[:, :, np.newaxis]
        # Create boolean masks indicating which elements of spec fall within each range
        mask_u_list = (sum_signal.mz.values >= u_range[0]) & (
            sum_signal.mz.values <= u_range[1]
        )
        mask_u_list = mask_u_list.any(axis=0)
        # Update mz and spec
        mz = sum_signal.mz.values[mask_u_list]
        sum_spec = sum_signal.values[mask_u_list]

        if sum_spec.size == 0:
            # Nothing to fit
            specs_to_fit = []
        else:
            # Get mz/spectrum pairs to fit from segmented spectrum
            n_scans = get_scan_timestamps(filename).size
            seg_spec_indices = segment_spec(sum_spec, threshold=n_scans)
            specs_to_fit = [(mz[chunk], sum_spec[chunk]) for chunk in seg_spec_indices]

    if sample_file_type in ["tof_zarr", "tof_h5"]:
        runtime.logger.debug("Segment TOF spectrum for peak detection")
        sum_mz = sum_signal.mz.compute().values
        sum_values = sum_signal.compute().values
        specs_to_fit = [
            (
                sum_mz[(sum_mz >= u - dmz) & (sum_mz <= u + dmz)],
                sum_values[(sum_mz >= u - dmz) & (sum_mz <= u + dmz)],
            )
            for u in u_list
        ]
    return specs_to_fit


def _sort_and_filter_peaks(
    sum_signal: xarray.DataArray,
    all_peak_mzs: np.ndarray,
    all_peak_areas: np.ndarray,
    all_peak_heights: np.ndarray,
) -> tuple:
    """Helper function to sort and filter fitted peak data in detect_peaks

    :param sum_signal: Sum signal array
    :type sum_signal: xarray.DataArray
    :param all_peak_mzs: m/z values of the fitted peaks
    :type all_peak_mzs: np.ndarray
    :param all_peak_areas: Peak areas of the fitted peaks
    :type all_peak_areas: np.ndarray
    :param all_peak_heights: Peak heights of the fitted peaks
    :type all_peak_heights: np.ndarray
    :return: Tuple of fitted peak mzs, areas and height as numpy arrays
    :rtype: tuple
    """
    # Sort fitted peaks by m/z
    sorted_peak_ind = np.argsort(all_peak_mzs)
    all_peak_mzs = all_peak_mzs[sorted_peak_ind]
    all_peak_areas = all_peak_areas[sorted_peak_ind]
    all_peak_heights = all_peak_heights[sorted_peak_ind]

    # lmfit returns peaks with negative or zero heights, which are not valid
    # filter out zero height peaks to prevent division by zero in peak profiles
    peak_mz_coord = sum_signal.mz.sel(
        mz=all_peak_mzs,
        method="nearest",
    )
    valid_indices = sum_signal.sel(mz=peak_mz_coord, method="nearest").values > 0
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
    filename: str,
    all_peak_mzs: np.ndarray,
    sum_signal: xarray.DataArray,
    peak_areas: np.ndarray,
    peak_heights: np.ndarray,
) -> tuple:
    """Helper function to calculate peak profiles in detect_peaks

    :param filename: Sample file name
    :type filename: str
    :param all_peak_mzs: m/z values of the fitted peaks
    :type all_peak_mzs: np.ndarray
    :param sum_signal: Sum signal array
    :type sum_signal: xarray.DataArray
    :param peak_areas: Peak areas of the fitted peaks
    :type peak_areas: np.ndarray
    :param peak_heights: Peak heights of the fitted peaks
    :type peak_heights: np.ndarray
    :return: Tuple of peak profiles area and height (vs scan/time)
    :rtype: tuple
    """
    # Get the tof values corresponding to the peak mzs
    tofs = np.arange(len(sum_signal.mz)).astype(np.float32)
    indices = np.searchsorted(sum_signal.mz.values, all_peak_mzs)
    indices = np.clip(indices, 0, len(tofs) - 1)  # Ensure indices are within bounds
    unique_tofs = tofs[indices]

    peak_profiles = get_peak_profiles(filename, all_peak_mzs).assign_coords(
        tof=("mz", unique_tofs)
    )
    # Normalize peak profile intensities to 1
    peak_profiles_norm = peak_profiles / peak_profiles.sum(dim="time")
    peak_profiles_norm = peak_profiles_norm.fillna(0)

    # Restore peak profiles intensities using peak areas and heights of the fitted peaks,
    # that are, presumably, the correct integral of the peak profiles
    peak_profiles_area = peak_profiles_norm * peak_areas.reshape(-1, 1)
    peak_profiles_height = peak_profiles_norm * peak_heights.reshape(-1, 1)

    return peak_profiles_area, peak_profiles_height


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
