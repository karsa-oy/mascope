# -*- coding: utf-8 -*-
"""Peak detection and fitting related functions

Created on Wed Apr 17 13:45:17 2019

@author: Oskari Kausiala
"""
import asyncio
import json
import lmfit
import numpy as np
import pandas as pd

from concurrent.futures import ProcessPoolExecutor

from scipy.interpolate import CubicSpline
from scipy.io import loadmat
from scipy.signal import find_peaks
from scipy.signal._peak_finding_utils import (
    _select_by_peak_distance,
)
from scipy.stats import norm

from backend.db.conn import conn

from backend.lib.file import load_file, zarr_sdk
from backend.lib.filter import smooth



def calculate_peak_area(x, peakshape, peak):
    pos, hei, res = peak
    return sum(gen_peak(x, pos, hei, res, peakshape))

async def detect_peaks(
    filename,
    u_list=None,
    max_n_peaks=5,
    add_peak_threshold=.9,
    if_exists='fail', # 'fail', 'append', 'replace'
    ):
    print(f"Detecting peaks for file {filename}")
    if if_exists not in ['fail', 'append', 'replace']:
        raise ValueError("""
            Argument 'if_exists' must be one of 'fail', 'append', 'replace'
        """)
    dmz = .5
    peakshape, R = read_instrument_functions(filename)
    old_peak_mzs = []
    old_peak_heights = []
    sample_file_data = load_file(filename, vars=['peaks'])
    mz_top = sample_file_data.props['range'][1]
    if u_list is not None:
        # Fit peaks to given unit masses
        if 'peaks' in sample_file_data:
            if if_exists == 'fail':
                raise FileExistsError("Peak data exists!")
            old_peak_mzs = list(sample_file_data.peaks.mz.values)
            old_peak_heights = list(sample_file_data.peaks.sum(dim='time').values)
            u_list_fitted = list(np.unique(np.round(old_peak_mzs)))
        else:
            u_list_fitted = []
        if if_exists == 'append':
            # Only fit unit masses not already fitted
            u_list = [u for u in u_list if u not in u_list_fitted]
        # Filter out too large values
        u_list = [u for u in u_list if u <= mz_top]
        if len(u_list) == 0:
            return sample_file_data

    sample_file_data = load_file(filename, vars=['signal'])
    if u_list is None:
        # Fit all peaks
        u_list = range(10, int(np.floor(mz_top))+1)
    print("Fitting unit masses: %s" %u_list)
    mz = sample_file_data.mz
    sum_spec = sample_file_data.signal.sum(dim='time').compute()
    executor = ProcessPoolExecutor()
    loop = asyncio.get_event_loop()
    futures = [
        loop.run_in_executor(
            executor,
            fit_n_peaks,
            mz.sel(mz=slice(u-dmz, u+dmz)).compute().values,
            sum_spec.sel(mz=slice(u-dmz, u+dmz)).compute().values,
            peakshape,
            R(u),
            max_n_peaks,
            add_peak_threshold
        )
        for u in u_list
    ]
    new_peaks = []
    for i, future in enumerate(asyncio.as_completed(futures, loop=loop)):
        fit, peaks = await future
        if fit:
            new_peaks.extend(peaks)
        print(f"Peak detection progress: {(i+1)/len(futures):.2f}")
    executor.shutdown()
    sample_file_data = sample_file_data.assign_coords(
            tof=('mz', np.arange(len(sample_file_data.mz)).astype(np.float32))
        )
    if len(new_peaks): 
        new_peak_mzs = list(zip(*new_peaks))[0]
        new_peak_heights = list(zip(*new_peaks))[1]
        # new_peak_areas = list(zip(*new_peaks))[3]
    else:
        new_peak_mzs = []
        new_peak_heights = []

    if if_exists == 'append':
        all_peak_mzs = [*old_peak_mzs, *new_peak_mzs]
        all_peak_heights = [*old_peak_heights, *new_peak_heights]
    else:
        all_peak_mzs = new_peak_mzs
        all_peak_heights = new_peak_heights

    all_peak_ind = np.argsort(all_peak_mzs)
    all_peak_mzs = np.array(all_peak_mzs)[all_peak_ind]
    all_peak_heights = np.array(all_peak_heights)[all_peak_ind]

    peak_mz_coord = sample_file_data.mz.sel(
        mz=all_peak_mzs,
        method='nearest',
        )
    peak_mzs, unique_peak_index = np.unique(
        peak_mz_coord,
        return_index=True
    )
    peak_heights = all_peak_heights[unique_peak_index]
    peak_profiles = sample_file_data.signal.sel(
        mz=peak_mzs,
        method='nearest'
    )
    peak_profiles_norm = peak_profiles / peak_profiles.sum(dim='time')
    peak_profiles_scaled = peak_profiles_norm * peak_heights.reshape(-1,1)
    print(f"Writing peaks to file {filename}")
    overwrite_peak_dataset = (if_exists == 'append' or if_exists == 'replace')
    zarr_sdk.write_peak_dataset(peak_profiles_scaled, sample_file_data, overwrite_peak_dataset)
    print("Complete")
    sample_file_data = load_file(
        filename,
        vars=['peaks'],
        prev_dataset=sample_file_data
    )
    return sample_file_data

def detect_peaks_old(
    cache_item,
    smooth_window=None,
    peak_height=None,
    peak_distance=None,
    peak_width=None,
    ):
    """NOTE: Deprecated, left here for reference.
    TODO: Remove
    """
    if 'signal' not in cache_item:
        # Signal not in cache, load
        cache_item = load_file(
            cache_item.props['filename'],
            vars=['signal'],
            prev_dataset=cache_item
        )
    sum_spectrum = (
        cache_item
        .signal.sum(dim='time').compute()
        .interpolate_na(  # Interpolate NaNs for smoothing
            dim='mz',
            method='linear',
            limit=None,
            max_gap=2,
        )
    )

    if smooth_window:
        sum_spectrum = smooth(sum_spectrum, window_len=smooth_window)
    
    peaks, peak_props = find_peaks(
        sum_spectrum,
        height=peak_height,
        distance=peak_distance,
        width=peak_width
    )
    cache_item = (
        cache_item
        .assign_coords(
            tof=('mz', np.arange(len(cache_item.mz)).astype(np.float32))
        )
    )

    peak_profiles = cache_item.signal[peaks]

    zarr_sdk.write_peak_dataset(peak_profiles, cache_item)

    cache_item = load_file(
        cache_item.props['filename'],
        vars=['peaks'],
        prev_dataset=cache_item
    )
    return cache_item

def filter_peaks(
        peaks,
        mz_range=None,
        t_range=None,
        height=None,
        distance=None,
        ):

    if mz_range is not None:
        peaks = peaks.sel(
            mz=slice(*mz_range)
            )
    if t_range is not None:
        peaks = peaks.sel(
            time=slice(*t_range)
            )
    peaks = peaks.dropna(dim='mz', how='all')
    if 'time' in peaks.dims:
        peak_heights = peaks.sum(dim='time').values
    else:
        peak_heights = peaks.values

    keep = np.array([True]*len(peaks))

    if height is not None:
        # Evaluate height condition
        keep_height = peak_heights > height
        keep = np.logical_and(keep, keep_height)

    if distance is not None:
        peak_indices = peaks.tof.values
        # Evaluate distance condition
        keep_distance = _select_by_peak_distance(
            peak_indices.astype(np.intp),
            peak_heights.astype(np.float64),
            distance
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
        max_iter=1000):
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
    params.add('npeaks', value=npeaks, vary=False)
    for p in range(npeaks):
        if dpos is not None:
            posmin = ppos[p] - dpos
            posmax = ppos[p] + dpos
        else:
            posmin = 0
            posmax = np.inf
        params.add(
            'peak%spos' %
            p,
            value=ppos[p],
            min=posmin,
            max=posmax,
            vary=fit_pos)
        params.add('peak%shei' % p, value=phei[p] / ymax, min=0, vary=fit_hei)
        params.add('peak%sres' % p, value=pres[p], min=0, vary=fit_res)
    # Fit
    minner = lmfit.Minimizer(
        peak_kernel_residual,
        params,
        fcn_args=(
            x,
            yn,
            ps
        )
    )
    fit = minner.leastsq(max_nfev=max_iter)
    # Rescale fit results
    fit.residual *= ymax
    for par in fit.params:
        if 'hei' in par:
            fit.params[par].value *= ymax
            if fit.params[par].stderr is not None:
                fit.params[par].stderr *= ymax
    peaks = [
        fit.params[par].value
        for par in fit.params if par.startswith('peak')
        ]
    peaks = [ tuple(peaks[i:i+3]) for i in range(0, len(peaks), 3) ]
    return fit, peaks

def fit_n_peaks(
    x,
    y,
    peak_shape,
    resolution_function,
    max_n_peaks=5,
    threshold=0.9,
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
    spec_norm = np.linalg.norm(y)
    residual_norm = spec_norm
    prev_fit = None
    prev_peaks = []
    for i in range(max_n_peaks):
        if i == 0:
            # Initialize first peak
            max_ind = np.argmax(y)
            init_pos = [ x[max_ind] ]
            init_hei = [ y[max_ind] ]
            init_res = [ 
                resolution_function(x[max_ind])
                if callable(resolution_function)
                else resolution_function
                ]
            
        fit, peaks = fit_peaks(
            x,
            y,
            peak_shape,
            i+1,
            init_pos,
            init_hei,
            init_res,
            fit_pos,
            fit_hei,
            fit_res,
            dpos=0.1,
            max_iter=1000
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
                if (max_residual_mz > (peak_pos - hwhm)
                    and max_residual_mz < (peak_pos + hwhm)
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
    peaks = [ (*peak, calculate_peak_area(x, peak_shape, peak)) for peak in peaks ]
    return fit, peaks

def fwhm_to_sigma(fwhm):
    return 0.4246609 * fwhm

def gen_gaussian_peakshape():
    x = np.linspace(-30, 30, 601)
    y = norm.pdf(x, 0, 1)
    y_norm = y / max(y)
    
    return {
        'x': x,
        'y': y_norm
        }

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

    sigma = fwhm_to_sigma(ppos / pres)
    xi = (np.array(ps['x']) * sigma) + ppos
    yi = ps['y'] / np.max(ps['y']) * phei
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
        return x[i:j + 1], peak[i:j + 1]
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
    npeaks = params['npeaks']
    for p in range(int(npeaks)):
        ppos = params['peak%spos' %p]
        phei = params['peak%shei' %p]
        pres = params['peak%sres' %p]
        peak = gen_peak(x, ppos, phei, pres, ps)
        kernel += peak
    return kernel

def get_batch_u_list(sample_batch_id):
    # get sample batch
    with conn:
        [sample_batch] = pd.read_sql(f"""
            SELECT build_params
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            ).to_dict('records')
    build_params = json.loads(sample_batch['build_params'])
    calibration_collection_id = build_params['calibration_collection']
    ion_mechanism_ids = build_params['ion_mechanisms']
    with conn:
        target_collection_ids = pd.read_sql(f"""
            SELECT target_collection_id
            FROM target_collection_in_sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            )['target_collection_id'].tolist()
    target_collection_ids.append(calibration_collection_id)
    with conn:
        target_collection_id_refs = ','.join('?'*len(target_collection_ids))
        ion_mechanism_id_refs = ','.join('?'*len(ion_mechanism_ids))
        target_isotope_mzs = pd.read_sql(f"""
            SELECT mz
            FROM target_compound_in_target_collection
            NATURAL JOIN target_compound
            NATURAL JOIN target_ion
            NATURAL JOIN target_isotope
            WHERE target_collection_id IN ({target_collection_id_refs})
            AND ionization_mechanism_id IN ({ion_mechanism_id_refs})
            """,
            conn,
            params=[*target_collection_ids, *ion_mechanism_ids]
            )['mz'].tolist()
    return np.unique(np.round(target_isotope_mzs))

def get_peaks(cache_item):
    peaks = cache_item.peaks
    peaks = peaks.dropna(dim='mz', how='all')
    return peaks.compute()

def load_peakshape_mat(peakshape_file):
    """Load peakshape from a file generated by tofTools
    """
    ps_mat = loadmat(peakshape_file)
    ps_struct = ps_mat['peakShape']
    ps = ps_struct['dat'][0][0]
    x = ps[:, 0]
    y = ps[:, 1]
    y = y / max(y)
    return {'x': x, 'y': y}

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

def read_instrument_functions(filename):
    with conn:
        sample_file_df = pd.read_sql(f"""
            SELECT
                datetime_utc,
                instrument
            FROM
                sample_file
            WHERE
                filename = ?
            """,
            conn,
            params=[filename]
            )
        [instrument] = sample_file_df.instrument
        [file_timestamp] = sample_file_df.datetime_utc
        instrument_function_df = pd.read_sql(f"""
            SELECT
                peakshape,
                resolution_function
            FROM
                instrument_function
            WHERE
                instrument = ?
                AND
                datetime_utc = (
                    SELECT
                         MAX(datetime_utc)
                    FROM
                        instrument_function
                    WHERE datetime_utc < ?
                    AND instrument = ?
                    LIMIT 1
                )
            """,
            conn,
            params=[instrument, file_timestamp, instrument]
        )
    if not len(instrument_function_df):
        raise ValueError(f"""
            Instrument functions not found for instrument {instrument}
            before date {file_timestamp}.
            """
            )
    peakshape = json.loads(instrument_function_df.peakshape[0])
    p1, p2 = json.loads(instrument_function_df.resolution_function[0])
    R = lambda m: m / (p1 * m + p2)
    return peakshape, R