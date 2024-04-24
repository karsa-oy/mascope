# -*- coding: utf-8 -*-
"""Peak detection and fitting related functions

Created on Wed Apr 17 13:45:17 2019

@author: Oskari Kausiala
"""
import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from itertools import compress

import lmfit
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal._peak_finding_utils import _select_by_peak_distance
from scipy.stats import norm

from .file_func import load_file, zarr_sdk


def calculate_peak_area(x, peakshape, peak):
    pos, hei, res = peak
    return sum(gen_peak(x, pos, hei, res, peakshape))


def calculate_tic(filename):
    try:
        sample_file_data = load_file(filename, vars=["sum_signal"])
        sum_spectrum = sample_file_data.sum_signal
    except FileNotFoundError:
        sample_file_data = load_file(filename, vars=["signal"])
        sum_spectrum = sample_file_data.signal.sum(dim="time")
    tic = sum_spectrum.sum(dim="mz").compute().item()
    return tic


def segment_spec(sum_spec):
    """Perform segmentation of Orbitrap spectrum

    :param sum_spec: sum of spectra along time dimension
    :type sum_spec: array-like
    :return: list of segment indices
    :rtype: list
    """
    # Get non-zero indices
    non_zero_indices = np.flatnonzero(sum_spec)
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
    print(f"Detecting peaks for file {filename}")
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
    sample_file_data = load_file(filename, vars=["peak_areas", "peak_heights"])
    mz_top = sample_file_data.props["range"][1]

    if u_list is None:
        # Fit all peaks
        u_list = range(10, int(np.floor(mz_top)) + 1)

    # Fit peaks to given unit masses
    if "peak_areas" in sample_file_data:
        if if_exists == "fail":
            raise FileExistsError("Peak data exists!")
        old_peak_mzs = list(sample_file_data.peak_areas.mz.values)
        old_peak_areas = list(sample_file_data.peak_areas.sum(dim="time").values)
        old_peak_heights = list(sample_file_data.peak_heights.sum(dim="time").values)
        u_list_fitted = list(np.unique(np.round(old_peak_mzs)))
    else:
        u_list_fitted = []

    if if_exists == "append":
        # Only fit unit masses not already fitted
        u_list = [u for u in u_list if u not in u_list_fitted]
    # Filter out too large values
    u_list = [u for u in u_list if u <= mz_top]

    if len(u_list) == 0:
        # Nothing to fit
        return sample_file_data

    print(f"Fitting unit masses: {u_list}")

    sample_file_data = load_file(filename, vars=["signal"])

    mz = sample_file_data.mz
    sum_spec = sample_file_data.signal.sum(dim="time").compute()
    cpu_cores = os.cpu_count()
    max_workers = max(1, cpu_cores // 2)
    executor = ProcessPoolExecutor(max_workers=max_workers)
    loop = asyncio.get_event_loop()

    if instrument_type == "orbi":
        # Segment sum spectrum
        non_zero_indices = segment_spec(sum_spec)
        # Get mz/spectrum pairs to fit
        specs_to_fit = [
            (mz[chunk].values, sum_spec[chunk].values) for chunk in non_zero_indices
        ]
        u_list_np = np.array(u_list)
        mask_u_list = []
        for mz_to_fit, spec_to_fit in specs_to_fit:
            # Mask for chunks crossing u_list ranges (u+-0.5)
            mask_u_list.append(
                np.any(np.abs(mz_to_fit - u_list_np.reshape(-1, 1)) <= 0.5)
            )
        # Filter list of chunks to fit based on mask_u_list boolean values
        specs_to_fit = compress(specs_to_fit, mask_u_list)
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
            max_n_peaks,
        )
        for mz_to_fit, spec_to_fit in specs_to_fit
    ]

    new_peaks = []
    for i, future in enumerate(asyncio.as_completed(futures)):
        fit, peaks = await future
        if fit:
            new_peaks.extend(peaks)
        print(f"Peak detection progress: {(i+1)/len(futures):.2f}")
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
    peak_profiles = sample_file_data.signal.sel(mz=peak_mzs, method="nearest")
    peak_profiles["mz"] = peak_mzs
    peak_profiles_norm = peak_profiles / peak_profiles.sum(dim="time")
    peak_profiles_area = peak_profiles_norm * peak_areas.reshape(-1, 1)
    peak_profiles_height = peak_profiles_norm * peak_heights.reshape(-1, 1)
    print(f"Writing peaks to file {filename}")
    overwrite_peak_dataset = if_exists in {"append", "replace"}
    zarr_sdk.write_peaks(
        peak_profiles_area,
        peak_profiles_height,
        sample_file_data,
        overwrite_peak_dataset,
    )
    print("Complete")
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
    ymax = max(y)
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
    num_of_params = npeaks * sum([fit_pos, fit_hei, fit_res])
    if num_of_params > len(x):
        return None, None
    # Fit
    minner = lmfit.Minimizer(peak_kernel_residual, params, fcn_args=(x, yn, ps))
    fit = minner.leastsq(max_nfev=max_iter)
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
            dpos=0.1,
            max_iter=1000,
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
    peaks = [(*peak, calculate_peak_area(x, peak_shape, peak)) for peak in peaks]
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

    sigma = ppos / pres / (2 * np.sqrt(2 * np.log(2)))
    xi = (np.array(ps["x"]) * sigma) + ppos
    yi = ps["y"] / np.max(ps["y"]) * phei
    spline = CubicSpline(xi, yi, extrapolate=False)
    peak = spline(x)
    peak[np.isnan(peak)] = 0
    peak[peak < 0] = 0
    if trim_borders:
        thr = 1e-5
        i = 0
        while peak[i] < thr:
            i += 1
        j = -1
        while peak[j] < thr:
            j -= 1
        if j == -1:
            j = -2
        return x[i : j + 1], peak[i : j + 1]
    else:
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

    kernel = np.zeros((len(x),))
    npeaks = params["npeaks"]
    for p in range(int(npeaks)):
        ppos = params["peak%spos" % p]
        phei = params["peak%shei" % p]
        pres = params["peak%sres" % p]
        peak = gen_peak(x, ppos, phei, pres, ps)
        kernel += peak
    return kernel


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
