from backend.lib.file import load_file, zarr_sdk
#from .hardware.tofwerk.lib.TwTool import TwMassCalibrate, TwTof2Mass

import numpy as np

from scipy.signal import find_peaks
from scipy.signal._peak_finding_utils import (
    _select_by_peak_distance,
)


def detect_peaks(cache_item):
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
    peaks, peak_props = find_peaks(
        sum_spectrum,
        height=0,
        distance=None,
        width=None
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


def get_peaks(
        cache_item
        ):

    peaks = cache_item.peaks
    peaks = peaks.dropna(dim='mz', how='all')

    return peaks.compute()


def filter_peaks(
        cache_item,
        mz_range,
        t_range,
        height=None,
        distance=None,
        width=None
        ):

    peaks = cache_item.peaks.sel(
        mz=slice(*mz_range),
        time=slice(*t_range)
    )
    peaks = peaks.dropna(dim='mz', how='all')
    peak_heights = peaks.sum(dim='time').values

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


def mz_calibrate_tof(peak_tof, peak_mz, exact_mz):
    # Prepare arguments
    mass_calib_mode = 2
    nbr_points = len(peak_tof)
    mass = np.array(exact_mz, dtype=np.double)
    tofs = np.array(peak_tof, dtype=np.double)
    peak_mz = np.array(peak_mz)
    weight = np.ones((nbr_points,)) # TODO: Set weights?
    nbr_params = np.array([3], dtype=np.int)
    mass_calib_par = np.zeros((nbr_params[0],), dtype=np.double)
    legacy_a = legacy_b = np.array([None], dtype=np.double)
    # Calibrate
    ret = TwMassCalibrate(mass_calib_mode,
                          nbr_points,
                          mass,
                          tofs,
                          weight,
                          nbr_params,
                          mass_calib_par,
                          legacy_a,
                          legacy_b
                          )
    
    if ret != 4:
        raise Exception("TwMassCalibrate failed with code: %s" %ret)

    mass_calib = {'mode': mass_calib_mode,
                  'par': list(mass_calib_par)
                  }

    new_peak_mz = np.array([TwTof2Mass(tof, mass_calib_mode, mass_calib_par)
                            for tof in tofs
                            ])
    pre_dmz = (peak_mz - mass) / mass * 1e6
    post_dmz = (new_peak_mz - mass) / mass * 1e6
    pre_dmz_norm = np.linalg.norm(pre_dmz)
    post_dmz_norm = np.linalg.norm(post_dmz)

    stats = {
        'mz': mass,
        'new_mz': new_peak_mz,
        'pre_dmz': pre_dmz,
        'post_dmz': post_dmz,
        'pre_dmz_norm': pre_dmz_norm,
        'post_dmz_norm': post_dmz_norm
    }

    return mass_calib, stats
