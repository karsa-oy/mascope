# -*- coding: utf-8 -*-
"""Peak detection and fitting related functions

Created on Wed Apr 17 13:45:17 2019

@author: Oskari Kausiala
"""
import asyncio
import os
from concurrent.futures import ProcessPoolExecutor

import lmfit
import numpy as np
from scipy.signal._peak_finding_utils import _select_by_peak_distance
from scipy.stats import norm
from scipy.integrate import simpson


from mascope_lib.runtime import lib_runtime

from .file_func import load_file, zarr_sdk, get_instrument_type, get_sum_signal


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
            load_file(filename).attrs["props"].get("sample_interval", 0.25)
        )
        # return sum signal full integral in tof space
        return sum_spec.sum(dim="mz").compute().item() * sample_interval
    else:
        # return sum signal full integral in mz space
        return simpson(y=sum_spec.values, x=sum_spec.mz.values)


def segment_spec(sum_spec):
    """Perform segmentation of Orbitrap spectrum

    :param sum_spec: sum of spectra along time dimension
    :type sum_spec: array-like
    :return: list of segment indices
    :rtype: list
    """
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
        non_zero_indices[-1][-1] = non_zero_indices[-1][:-1]
    # Remove short chunks
    non_zero_indices = [chunk for chunk in non_zero_indices if len(chunk) > 4]
    return non_zero_indices


async def detect_peaks(
    filename,
    instrument_functions,
    add_peak_threshold,
    u_list=None,
    max_n_peaks=5,
    if_exists="fail",  # 'fail', 'append', 'replace'
    dmz=0.5,
    return_peak_mzs=False,
    instrument_type="tof",
):
    lib_runtime.logger.info(f"Detecting peaks for file {filename}")
    if if_exists not in ["fail", "append", "replace"]:
        raise ValueError(
            """
            Argument 'if_exists' must be one of 'fail', 'append', 'replace'
            """
        )
    peakshape, R = instrument_functions
    old_peak_mzs = []
    old_peak_areas = []
    old_peak_heights = []
    sample_file_data = load_file(
        filename, vars=["signal", "peak_areas", "peak_heights"]
    )
    mz_top = sample_file_data.props["range"][1]

    if u_list is None:
        # Fit all peaks
        u_list = np.arange(10, np.floor(mz_top) + 1)

    # Fit peaks to given unit masses
    if "peak_areas" in sample_file_data:
        if if_exists == "fail":
            raise FileExistsError("Peak data exists!")
        peak_areas = sample_file_data.peak_areas.dropna(dim="mz")
        peak_heights = sample_file_data.peak_heights.dropna(dim="mz")
        old_peak_mzs = list(peak_areas.mz.values)
        old_peak_areas = list(peak_areas.sum(dim="time").values)
        old_peak_heights = list(peak_heights.sum(dim="time").values)
        u_list_fitted = np.unique(np.round(old_peak_mzs))
    else:
        u_list_fitted = np.array([])

    if if_exists == "append":
        # Only fit unit masses not already fitted
        u_list = np.setdiff1d(u_list, u_list_fitted)
    # Filter out too large values
    u_list = u_list[u_list <= mz_top]

    if len(u_list) == 0:
        # Nothing to fit
        lib_runtime.logger.info("Nothing to fit")
        return sample_file_data

    lib_runtime.logger.info(f"Fitting unit masses: {u_list}")

    sum_spec = get_sum_signal(filename)
    mz = sum_spec.mz
    # Sample interval for peak area calculation in counts vs TOF
    if instrument_type == "tof":
        # default 0.25 for backwards compatibility
        sample_interval = (
            load_file(filename).attrs["props"].get("sample_interval", 0.25)
        )
    else:
        sample_interval = None

    cpu_cores = os.cpu_count()
    max_workers = max(1, cpu_cores // 2)
    executor = ProcessPoolExecutor(max_workers=max_workers)
    loop = asyncio.get_event_loop()

    if instrument_type == "orbi":
        # Stack mass ranges
        u_range = np.vstack([u_list - 0.5, u_list + 0.5])
        # Broadcast the u_range array to have the same shape as mz
        u_range = u_range[:, :, np.newaxis]
        # Create boolean masks indicating which elements of spec fall within each range
        mask_u_list = (mz.values >= u_range[0]) & (mz.values <= u_range[1])
        mask_u_list = mask_u_list.any(axis=0)
        # Update mz and spec
        mz = mz.values[mask_u_list]
        sum_spec = sum_spec.values[mask_u_list]

        if sum_spec.size == 0:
            # Nothing to fit
            specs_to_fit = []
        else:
            # Get mz/spectrum pairs to fit from segmented spectrum
            seg_spec_indices = segment_spec(sum_spec)
            specs_to_fit = [(mz[chunk], sum_spec[chunk]) for chunk in seg_spec_indices]
    if instrument_type == "tof":
        specs_to_fit = [
            (
                mz.sel(mz=slice(u - dmz, u + dmz)).compute().values,
                sum_spec.sel(mz=slice(u - dmz, u + dmz)).compute().values,
            )
            for u in u_list
        ]

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
    for i, future in enumerate(asyncio.as_completed(futures)):
        fit, peaks = await future
        if fit:
            new_peaks.extend(peaks)
        lib_runtime.logger.info(f"Peak detection progress: {(i+1)/len(futures):.2f}")
    executor.shutdown()
    sample_file_data = sample_file_data.assign_coords(
        tof=("mz", np.arange(len(sample_file_data.mz)).astype(np.float32))
    )
    if len(new_peaks) > 0:
        new_peak_mzs = list(zip(*new_peaks))[0]
        new_peak_heights = list(zip(*new_peaks))[1]
        new_peak_areas = list(zip(*new_peaks))[3]
    else:
        new_peak_mzs = []
        new_peak_areas = []
        new_peak_heights = []

    if if_exists == "append":
        all_peak_mzs = [*old_peak_mzs, *new_peak_mzs]
        all_peak_areas = [*old_peak_areas, *new_peak_areas]
        all_peak_heights = [*old_peak_heights, *new_peak_heights]
    else:
        all_peak_mzs = new_peak_mzs
        all_peak_areas = new_peak_areas
        all_peak_heights = new_peak_heights

    all_peak_ind = np.argsort(all_peak_mzs)
    all_peak_mzs = np.array(all_peak_mzs)[all_peak_ind]
    all_peak_areas = np.array(all_peak_areas)[all_peak_ind]
    all_peak_heights = np.array(all_peak_heights)[all_peak_ind]

    peak_mz_coord = sample_file_data.mz.sel(
        mz=all_peak_mzs,
        method="nearest",
    )
    peak_mzs, unique_peak_index = np.unique(peak_mz_coord, return_index=True)
    all_peak_mzs = all_peak_mzs[unique_peak_index]

    # Difference between fitted peak positions and binded to the mz grid
    peak_mz_diff = np.abs(all_peak_mzs - peak_mzs)
    # Recalculate peak position difference to ppm
    peak_mz_diff_ppm = 1e6 * peak_mz_diff / all_peak_mzs
    # Find where ppm difference is > 1 ppm
    peak_mz_mask = np.where(peak_mz_diff_ppm > 1)
    # Replace mz values where ppm > 1 with exact fitted peak positions
    peak_mzs[peak_mz_mask] = all_peak_mzs[peak_mz_mask]

    peak_areas = all_peak_areas[unique_peak_index]
    peak_heights = all_peak_heights[unique_peak_index]
    peak_profiles = sample_file_data.signal.interpolate_na(
        dim="mz", method="linear"
    ).sel(mz=peak_mzs, method="nearest")
    peak_profiles["mz"] = peak_mzs
    peak_profiles_norm = peak_profiles / peak_profiles.sum(dim="time")
    peak_profiles_area = peak_profiles_norm * peak_areas.reshape(-1, 1)
    peak_profiles_height = peak_profiles_norm * peak_heights.reshape(-1, 1)
    lib_runtime.logger.info(f"Writing peaks to file {filename}")
    overwrite_peak_dataset = if_exists in {"append", "replace"}
    zarr_sdk.write_peaks(
        peak_profiles_area,
        peak_profiles_height,
        sample_file_data,
        overwrite_peak_dataset,
    )
    lib_runtime.logger.info("Complete")
    sample_file_data = load_file(
        filename, vars=["peak_areas"], prev_dataset=sample_file_data
    )
    if return_peak_mzs:
        return (sample_file_data, all_peak_mzs)
    return sample_file_data


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
    x,
    y,
    peak_shape,
    resolution_function,
    threshold,
    sample_interval=None,
    max_n_peaks=5,
    fit_pos=True,
    fit_hei=True,
    fit_res=False,
):
    """Fit a priori unknown number of peaks of known shape and width into signal y.

    Parameters
    ----------
    x : array
        y coordinates
    y : array
        signal to deconvolve
    peak_shape : dict
        peak shape {x: array, y: array}
    resolution_function : callable or float
        function to calculate the width of the peak
    sample_interval : float
        signal sampling interval, by default None
    max_n_peaks : int, optional
        maximum number of peaks to fit, by default 5
    threshold : float, optional
        to add a new peak, the fit must improve at least by this factor,
        by default 0.9
    fit_pos : bool, optional
        fit peak positions, by default True
    fit_hei : bool, optional
        fit peak heights, by default True
    fit_res : bool, optional
        fit peak widths, by default False

    Returns
    -------
    tuple
        returns (lmfit result, peaks)
    """
    if not len(y):
        return None, None

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
        if not fit:
            return None, []
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
    return fit, peaks


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
    peaks = peaks.dropna(dim="mz", how="all")
    return peaks.compute()


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
