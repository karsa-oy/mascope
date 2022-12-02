# -*- coding: utf-8 -*-
"""Peak detection and fitting related functions

Created on Wed Apr 17 13:45:17 2019

@author: Oskari Kausiala
"""

import numpy as np
import lmfit

from scipy.interpolate import CubicSpline
from scipy.io import loadmat
from scipy.stats import norm


def calculate_peak_area(x, peakshape, peak):
    pos, hei, res = peak
    return sum(gen_peak(x, pos, hei, res, peakshape))

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
