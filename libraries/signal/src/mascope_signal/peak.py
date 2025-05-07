import asyncio
import os
import math
from concurrent.futures import ProcessPoolExecutor
from typing import Iterable
import warnings

import lmfit
import numpy as np
from scipy.signal._peak_finding_utils import _select_by_peak_distance
from scipy.stats import norm
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
from mascope_signal.runtime import runtime

# Restrict large chunks for dask
dask.config.set(**{"array.slicing.split_large_chunks": True})

# Precompute sigma multiplier for peak generation
SIGMA_MULTIPLIER = 2 * np.sqrt(2 * np.log(2))


def calculate_peak_area(
    x: np.ndarray, peakshape: dict, peak: tuple, sample_interval: float
) -> float:
    """Calculate the area of a peak.

    This function calculates the area under a peak shape using Simpson's rule.

    :param x: The array of x values corresponding to the peak.
    :type x: numpy.ndarray
    :param peakshape: The median peak shape.
    :type peakshape: dict
    :param peak: A tuple containing the position, height, and resolution of the peak.
    :type peak: tuple
    :return: The area under the peak shape.
    :rtype: float
    """
    pos, hei, res = peak
    peak_y = gen_peak(x, pos, hei, res, peakshape)
    if sample_interval:
        # calculate peak area in TOF space
        return np.sum(peak_y) * sample_interval
    # calculate peak area in mz space
    return simpson(y=peak_y, x=x)


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

    # Restore peak profiles intensities using peak areas and heights of the fitted peaks,
    # that are, presumably, the correct integral of the peak profiles
    peak_profiles_area = peak_profiles_norm * peak_areas.reshape(-1, 1)
    peak_profiles_height = peak_profiles_norm * peak_heights.reshape(-1, 1)

    return peak_profiles_area, peak_profiles_height


def filter_peaks(
    peaks,
    mz_range=None,
    t_range=None,
    intensity=None,
    distance=None,
):
    if mz_range is not None:
        peaks = peaks.sel(mz=slice(*mz_range))
    if t_range is not None:
        peaks = peaks.sel(time=slice(*t_range))
    peaks = peaks.dropna(dim="mz", how="all")
    if "time" in peaks.dims:
        peak_intensities = peaks.sum(dim="time").values
    else:
        peak_intensities = peaks.values

    keep = np.array([True] * len(peaks))

    if intensity is not None:
        # Evaluate height condition
        keep_intensity = peak_intensities > intensity
        keep = np.logical_and(keep, keep_intensity)

    if distance is not None:
        peak_indices = peaks.tof.values
        # Evaluate distance condition
        keep_distance = _select_by_peak_distance(
            peak_indices.astype(np.intp), peak_intensities.astype(np.float64), distance
        )
        keep = np.logical_and(keep, keep_distance)

    return peaks[keep].compute()


def fit_peaks(
    x,
    y,
    ps,
    npeaks,
    ppos,
    phei,
    pres,
    fit_pos=True,
    fit_hei=True,
    fit_res=True,
    dpos=None,
    max_iter=1000,
):
    """Try to fit a set of peaks to signal 'y', minimizing the reconstruction
    residual as defined in the function 'peak_kernel_residual'.

    Parameters
    ----------
    x : array
        Sample numbers
    y : array
        Signal to be fitted
    ps : dict
        Peak shape
    npeaks : int
        Number of peaks to fit
    ppos : list
        Initial guesses for peak positions, must have length 'npeaks'.
        If 'fit_pos' is False, positions are not altered.
    phei : list
        Initial guesses for peak heights, must have length 'npeaks'.
        If 'fit_hei' is False, heights are not altered.
    pres : list
        Initial guesses for peak resolutions, must have length 'npeaks'.
        If 'fit_res' is False, widths are not altered.
    fit_pos : bool, optional
        Whether to optimize peak positions, by default True
    fit_hei : bool, optional
        Whether to optimize peak heights, by default True
    fit_res : bool, optional
        Whether to optimize peak widths, by default True
    dpos : float, optional
        Maximum allowed change in peak position (in one direction)
        during fitting, by default None. If None, only restricted to be
        non-negative.
    max_iter : int, optional
        Maximum number of minimizer iterations, by default 1000.

    Returns
    -------
    dict
        Resulted fit with parameters for each peak and the residual.
    """

    # Normalize y
    ymax = y.max()
    if ymax == 0:
        return None, None
    yn = y / ymax
    # Initialize parameters
    params = lmfit.Parameters()
    params.add("npeaks", value=npeaks, vary=False)
    for p in range(npeaks):
        if dpos is not None:
            posmin = ppos[p] - dpos
            posmax = ppos[p] + dpos
        else:
            posmin = 0
            posmax = np.inf
        params.add(f"peak{p}pos", value=ppos[p], min=posmin, max=posmax, vary=fit_pos)
        params.add(f"peak{p}hei", value=phei[p] / ymax, min=0, vary=fit_hei)
        params.add(f"peak{p}res", value=pres[p], min=0, vary=fit_res)
    # Check if number of varying parameters hit the limit
    num_of_params = npeaks * np.sum([fit_pos, fit_hei, fit_res])
    if num_of_params > len(x):
        return None, None
    # Fit
    minner = lmfit.Minimizer(
        peak_kernel_residual, params, fcn_args=(x, yn, ps), ftol=1e-6, xtol=1e-6
    )
    fit = minner.minimize(method="least_s", max_nfev=max_iter)
    # Rescale fit results
    fit.residual *= ymax
    for par in fit.params:
        if "hei" in par:
            fit.params[par].value *= ymax
            if fit.params[par].stderr is not None:
                fit.params[par].stderr *= ymax
    peaks = [fit.params[par].value for par in fit.params if par.startswith("peak")]
    peaks = [tuple(peaks[i : i + 3]) for i in range(0, len(peaks), 3)]
    return fit, peaks


def fit_n_peaks(
    x: Iterable,
    y: Iterable,
    peak_shape: dict,
    resolution_function: callable,
    threshold: float,
    sample_interval: float = None,
    max_n_peaks: int = 5,
    fit_pos: bool = True,
    fit_hei: bool = True,
    fit_res: bool = False,
) -> tuple:
    """Fit a number of peaks to a signal.
    The function tries to fit a number of peaks to the signal 'y' using the
    specified peak shape and resolution function. It iteratively adds peaks
    until the residual norm does not decrease significantly.

    :param x: x-values of the signal (m/z values)
    :type x: Iterable
    :param y: y-values of the signal (intensity values)
    :type y: Iterable
    :param peak_shape: The shape of the peak to be fitted.
    :type peak_shape: dict
    :param resolution_function: A function that returns the resolution of the peak
    :type resolution_function: callable
    :param threshold: Threshold for adding a new peak.
    :type threshold: float
    :param sample_interval: signal sampling interval, defaults to None
    :type sample_interval: float, optional
    :param max_n_peaks: max number of peaks to fit, defaults to 5
    :type max_n_peaks: int, optional
    :param fit_pos: if vary peak positions, defaults to True
    :type fit_pos: bool, optional
    :param fit_hei: if vary peak heights, defaults to True
    :type fit_hei: bool, optional
    :param fit_res: if vary peak resolution, defaults to False
    :type fit_res: bool, optional
    :return: tuple containing the fit result, the fitted peaks, and caught warnings
    :rtype: tuple
    """
    if not len(y):
        return None, None, []

    # Convert peak shape
    peak_shape["x"] = np.array(peak_shape["x"], dtype=np.float64)
    peak_shape["y"] = np.array(peak_shape["y"], dtype=np.float64)

    spec_norm = np.linalg.norm(y)
    residual_norm = spec_norm
    prev_fit = None
    prev_peaks = []
    for i in range(max_n_peaks):
        if i == 0:
            # Initialize first peak
            max_ind = np.argmax(y)
            init_pos = [x[max_ind]]
            init_hei = [y[max_ind]]
            init_res = [
                (
                    resolution_function(x[max_ind])
                    if callable(resolution_function)
                    else resolution_function
                )
            ]

        dpos = x[-1] - x[0]

        # Capture warnings during the fitting process
        captured_warnings = []
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            fit, peaks = fit_peaks(
                x,
                y,
                peak_shape,
                i + 1,
                init_pos,
                init_hei,
                init_res,
                fit_pos,
                fit_hei,
                fit_res,
                dpos=dpos,
                max_iter=100,
            )
            captured_warnings.extend(str(w.message) for w in ws)

        if not fit:
            return None, [], []

        new_residual_norm = np.linalg.norm(fit.residual)
        # Check for add new peak condition
        if new_residual_norm > threshold * residual_norm:
            fit = prev_fit
            peaks = prev_peaks
            break
        residual_norm = new_residual_norm
        prev_fit = fit
        prev_peaks = peaks
        # Find the place to add next peak
        # Loop through already fitted peaks
        max_residual_ind = np.argmax(fit.residual)
        max_residual = fit.residual[max_residual_ind]
        max_residual_mz = x[max_residual_ind]
        for peak_pos, peak_hei, peak_res in peaks:
            while max_residual > 0:
                hwhm = (peak_pos / peak_res) / 2
                # If the maximum of the residual is within the fitted peak, set
                # it to 0 in order to ignore it
                if max_residual_mz > (peak_pos - hwhm) and max_residual_mz < (
                    peak_pos + hwhm
                ):
                    fit.residual[max_residual_ind] = 0
                    max_residual_ind = np.argmax(fit.residual)
                    max_residual = fit.residual[max_residual_ind]
                    max_residual_mz = x[max_residual_ind]
                else:
                    break
        # Set the position of next peak to the maximum of residual
        init_pos.append(max_residual_mz)
        init_hei.append(max_residual)
        init_res.append(
            resolution_function(max_residual_mz)
            if callable(resolution_function)
            else resolution_function
        )
    # Calculate peak areas
    peaks = [
        (*peak, calculate_peak_area(x, peak_shape, peak, sample_interval))
        for peak in peaks
    ]
    return fit, peaks, captured_warnings


def fwhm_to_sigma(fwhm):
    return 0.4246609 * fwhm


def gen_gaussian_peakshape():
    x = np.linspace(-30, 30, 601)
    y = norm.pdf(x, 0, 1)
    y_norm = y / max(y)

    return {"x": x, "y": y_norm}


def gen_peak(x, ppos, phei, pres, ps, trim_borders=False):
    """Generate a peak of certain height and with and shape in domain 'x'.

    Parameters
    ----------
    x : array
        Array of sample numbers where to generate the peak
    ppos : float
        Peak position (sample number)
    phei : float
        Peak height
    pres : float
        Peak resolution
    ps : dict
        Peak shape
    trim_borders : bool, optional
        Trim close-to-zero values from edges, by default False

    Returns
    -------
    array or tuple
        If trim_borders=False returns an array of values corresponding to
        input parameter 'x'. Otherwise returns tuple with new x and the peak.
    """
    sigma = ppos / pres / SIGMA_MULTIPLIER

    # Make sure peakshape consists of numpy arrays
    ps["x"] = np.asarray(ps["x"], dtype=np.float64)
    ps["y"] = np.asarray(ps["y"], dtype=np.float64)

    # Rescale peak shape
    xi = ps["x"] * sigma + ppos
    yi = ps["y"] / np.max(ps["y"]) * phei

    # Interpolate to a new x scale
    peak = np.interp(x, xi, yi)

    peak = np.nan_to_num(peak, nan=0.0)
    peak[peak < 0] = 0

    if trim_borders:
        thr = 1e-5
        i = np.argmax(peak >= thr)
        j = np.argmax(peak[::-1] >= thr)
        j = len(x) - j if j > 0 else -1
        return x[i:j], peak[i:j]

    return peak


def gen_peak_kernel(params, x, ps):
    """Return a kernel for a set of peaks in domain 'x'.

    Parameters
    ----------
    params : dict
        Parameters of peaks to be included in the kernel, in the format
        returned by the function 'fit_peaks'.
    x : array
        Array of sample numbers for which to calculate the kernel.
    ps : dict
        Peak shape

    Returns
    -------
    array
        Peak kernel in domain 'x'.
    """
    npeaks = params["npeaks"].value
    peaks = np.zeros((npeaks, len(x)))

    for p in range(npeaks):
        ppos = params[f"peak{p}pos"].value
        phei = params[f"peak{p}hei"].value
        pres = params[f"peak{p}res"].value
        peaks[p] = gen_peak(x, ppos, phei, pres, ps)

    return np.sum(peaks, axis=0)


def get_peaks(sample_file, intensity_mode="area"):
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


def peak_kernel_residual(params, x, y, ps):
    """Generate a kernel of peaks and calculate the residual with regards
    to 'y'. Objective function for the function 'fit_peaks'.

    Parameters
    ----------
    params :  dict
        Parameters of peaks to be included in the kernel, in the format
        returned by the function 'fit_peaks'.
    x : array
        Array of sample numbers for which to calculate the kernel.
    y : array
        The signal regards to which the residual is to be calculated.
    ps : dict
        Peak shape

    Returns
    -------
    array
        The residual 'y - kernel'
    """

    kernel = gen_peak_kernel(params, x, ps)
    return y - kernel
