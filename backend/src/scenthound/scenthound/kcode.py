# -*- coding: utf-8 -*-
"""SparseCoder output related functions

NOTE: Some of these may be unused, and some may have more general use

Created on Wed Apr 17 10:34:28 2019
"""

import numpy as np

from itertools import groupby
from scipy.signal import find_peaks


def find_extrema(y):
    """Find peaks from y

    Parameters
    ----------
    y : array
        Column of code

    Returns
    -------
    array of bool
        Boolean array, True where there is local extreme in y
    """

    ylen = y.shape[0]
    locs = np.arange(0, ylen)
    extrema = np.ones(y.shape, dtype=bool)
    main = y.take(locs, axis=0, mode='clip')
    for shift in range(1, 2):
        plus = y.take(locs + shift, axis=0, mode='clip')
        minus = y.take(locs - shift, axis=0, mode='clip')
        extrema &= np.greater(main, plus)
        extrema &= np.greater(main, minus)
        if not extrema.any():
            return extrema
    return extrema


def thresholding(y, threshold, hysteresis, fill_gaps):
    """ Thresholding with hysteresis
        
    Parameters
    ----------
    y : array
        Signal for which to do thresholding
    threshold : double
        Threshold value, for negative threshold values the algorithm
        looks for values below abs(threshold)
    hysteresis : double
        If previous value is above threshold, the consecutive one need be
        only above (threshold-hysteresis) to still be counted
    fill_gaps : int
        Connect groups in the output if the gap in between is less or equal
        to this value
    
    Returns
    -------
    ind : array
        Array of boolean values indicating whether the inout signal at
        the index is above (or below) threshold
    """
    
    if threshold < 0:
        method = 'below'
        threshold = -threshold
        ge = y >= (threshold + hysteresis)
        le = y <= max(threshold, 0.0)
    else:
        method = "above"
        ge = y >= threshold
        le = y <= max((threshold - hysteresis), 0.0)

    known_val = ge | le
    known_ind = np.nonzero(known_val)[0]
    acc = np.cumsum(known_val)

    acc_next = acc - 1
    acc_next[acc_next < 0] = 0
    acc_prev = acc + 1
    acc_prev[acc_prev >= len(known_ind)] = len(known_ind) - 1

    if method == "below":
        ind = le[known_ind[acc_next]]  # | le[known_ind[acc_prev]]
    else:
        ind = ge[known_ind[acc_next]]  # | ge[known_ind[acc_prev]]

    if not acc[0]:
        ind[0] = False

    # Fill gaps
    if fill_gaps != 0:
        prev = ind[0]
        j = 1
        for i in range(1, len(ind) - fill_gaps):
            endi = min(len(ind) - 1, j + fill_gaps)
            if prev and not ind[j] and any(ind[j + 1:endi + 1]):
                ind[j:j + fill_gaps] = prev
                j += fill_gaps
            else:
                j += 1
            if j >= len(ind):
                break
            prev = ind[j - 1]
    return ind


def split_signal(y, threshold, hysteresis=0, fill_gaps=0, normalize=False):
    """Split signal 'y' (optionally normalized to 1) where it is above given
       threshold (threshold>0) or below abs(threshold) (if threshold<0)
    
    Parameters
    ----------
    y : array
        Signal to split to groups
    threshold : double
        Threshold value for split, for negative threshold values the algorithm
        looks for values below the set threshold
    hysteresis : double, optional
        If previous value is above threshold, the consecutive one need be
        only above (threshold-hysteresis) to still be counted in the group
    fill_gaps : int, optional
        Connect groups in the output if the gap in between is less or equal
        to this value
    normalize : bool, optional
        Set True to normalize the signal to range [0, 1]
    
    Returns
    -------
    true_groups : list
        List of lists of signal indices, where threshold condition is True
    false_groups : list
        List of lists of signal indices, where threshold condition is False
    """
    
    true_groups = []
    false_groups = []
    y = np.asarray(y)
    # Normalize y
    if normalize:
        y = y / max(y)
    # Do thresholding to find groups
    grp_ind = thresholding(y, threshold, hysteresis, fill_gaps)
    # Return groups
    for k, g in groupby(enumerate(grp_ind), lambda x: x[1]):
        group = list(g)
        group = tuple(zip(*group))
        grp_ind = list(group[0])
        if k:
            true_groups.append(grp_ind)
        else:
            false_groups.append(grp_ind)
    return true_groups, false_groups


def find_code_peaks(y, x=None, min_height=1e-5):
    """Find peaks in signal using the algorithm 'find_peaks'
    from 'scipy.signal'.
    

    Parameters
    ----------
    y : array
        Signal to search for peaks
    x : array, optional
        Dimension of the signal. The default is None.
    min_height : double, optional
        Minimum peak height. The default is 1e-5.

    Returns
    -------
    peaks : array
        Found peak locations in x if given, otherwise as indices of y.
    """
    
    if x is None:
        x = np.asarray(range(len(y)))
    split_thr = np.percentile(y[y > 0], 5)
    tg, fg = split_signal(y, split_thr)
    peaks = []
    for g in tg:
        gy = np.pad(y[g], 1, "constant")
        gpks, props = find_peaks(gy,
                                 height=min_height,
                                 threshold=None,
                                 distance=None,
                                 prominence=None)
        if len(gpks) == 0:
            continue
        else:
            gpks = np.array([g[p - 1] for p in gpks])
            peaks.extend(x[gpks])
    return np.asarray(peaks)


def find_single_peaks(y, min_height=.5, max_width=10):
    """Find well separated peaks from code
    
    Split the input signal into groups, and look for the highest point
    within the group.

    Parameters
    ----------
    y : array
        Input signal
    min_height : double, optional
        Minimum height of a peak. The default is .5.
    max_width : int, optional
        Maximum width of the signal group. The default is 10.

    Returns
    -------
    peaks : list
        List of indices of the found peaks.
    """
    
    peaks = []
    tg, fg = split_signal(y, 5e-3)
    for g in tg:
        if len(g) > max_width:
            continue
        elif np.max(y[g]) < min_height:
            continue
        else:
            peaks.append(g[np.argmax(y[g])])
    return peaks  # Indices of found peaks
