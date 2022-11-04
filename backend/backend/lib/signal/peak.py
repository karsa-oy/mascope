# -*- coding: utf-8 -*-
"""Peak detection and fitting related functions

Created on Wed Apr 17 13:45:17 2019

@author: Oskari Kausiala
"""

import numpy as np

import h5sparse
import lmfit

# from matplotlib import pyplot as plt

from scipy.signal._peak_finding import _identify_ridge_lines as find_ridges
from scipy.stats import mode
from scipy.sparse import lil_matrix
from scipy.interpolate import CubicSpline
from sklearn.preprocessing import normalize


def find_peaks_from_code(code, max_dist=1, max_gap=1, min_len=10):
    """Find peaks by detecting ridges from the code. Return peak positions 

    Parameters
    ----------
    code : array_like
        KSignalProcessor result sparse matrix
    max_dist : int, optional
        Peak maximum distance in sample numbers between consecutive spectra,
        by default 1
    max_gap : int, optional
        Maximum allowed length of time-wise gap for a peak, by default 1
    min_len : int, optional
        Minimum length of a ridge ti be considered a peak, by default 10

    Returns
    -------
    list
        List of peaks (sample numbers)
    """

    # Select non-zero columns
    coden = np.array( [code[:, i].toarray().reshape(-1)
                        for i in range(code.shape[1]) 
                        if code[:, i].sum()>0] )
    # Find ridges
    max_dist = [max_dist]*coden.shape[1]
    ridges = find_ridges(coden, max_dist, max_gap)
    # Filter ridges
    good_ridges = []
    for r in ridges:
        if len(r[0]) >= min_len:
            good_ridges.append(r)
    # Choose the mode sample number of a ridge line to be the peak position
    peaks = [ mode(r[1])[0][0] for r in good_ridges ]
    return peaks

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

    sigma = 0.4246609 * (ppos / pres)
    xi = (ps['x'] * sigma) + ppos
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

def gen_peak_dict(kinstrument, u0=None, u1=None, subsampling=1.):
    """Generate peak dictionary.

    Generates a dictionary of peaks (as a sparse matrix) to be utilized
    by the SparseCoder algorithm. It uses the peakshape and resolution
    information from the 'kinstrument' instance and generates a peak
    for every (1 * 'subsampling') sample number.

    Parameters
    ----------
    kinstrument : KInstrument
        KInstrument instance for which to generate the dictionary.
    u0 : int, optional
        First unit mass to include, by default None
    u1 : int, optional
        Last unit mass to include, by default None
    subsampling : float, optional
        Sub-/Supersampling factor, by default 1. Values below 1
        lead to supersampling, whereas above 1 to subsampling.

    Returns
    -------
    csr
        Sparse matrix where each row represents a peak at a certain position.
        The peak position at row 'i' (in sample numbers) is 'i' * 'subsampling'.
    """

    if u0 is None or u1 is None:
        u0 = 32
        u1 = kinstrument.desc.nbrPeaks + 1
    si0 = kinstrument.mz2sno(u0 - 0.5, roundit=True)
    si1 = min(kinstrument.mz2sno(u1 + 0.5, roundit=True), kinstrument.desc.nbrSamples)
    dshape = (int(kinstrument.desc.nbrSamples/subsampling), kinstrument.desc.nbrSamples)
    D = lil_matrix(dshape)
    for s in np.arange(si0, si1, subsampling):
        ps = kinstrument.get_ps(s)
        x = ps['x']
        x, y = gen_peak(x + s, s, 1.0, kinstrument.r_at_3p(s), ps, True)
        ind = x < si1 - 1
        dind = int(s / subsampling)
        D[dind, (x + 1)[ind]] = y[ind]
    return D.tocsr()

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

def load_peak_dict(filename):
    """Load peak dictionary (sparse matrix) from h5 file.

    Parameters
    ----------
    filename : str
        Full file path

    Returns
    -------
    csr
        Peak dictionary (sparse matrix)
    """

    # Load peak dinctionary D in Scipy sparse CSR format from a h5 file
    with h5sparse.File(filename, 'r') as h5f:
        D = h5f['sparse/matrix'].value
    return D

def match_peaks(
        peak_df,
        threshold=0.0,
        mz_err_tol=10,
        min_abu_match=0.99,
        min_iso_corr=0.8,
        apply_params_filter=False):
    """[summary]

    Parameters
    ----------
    peak_df : [type]
        [description]
    threshold : float, optional
        [description], by default 0.0
    mz_err_tol : int, optional
        [description], by default 10
    min_abu_match : float, optional
        [description], by default 0.99
    min_iso_corr : float, optional
        [description], by default 0.8
    apply_params_filter : bool, optional
        [description], by default False

    Returns
    -------
    [type]
        [description]
    """

    peak_df = peak_df.copy()
    peak_df['match'] = [None] * len(peak_df)
    for comp, row in peak_df.iterrows():
        match = True
        # Check signal level
        if apply_params_filter == True:
            print("Filtering with parameters")
            if row['signal'] < threshold:
                match = False
            
            if (np.array(np.abs(row['mass error'])) > mz_err_tol).any():
                match = False
            
            if row['abundance score'] < min_abu_match:
                match = False

            if row['isotope r2'] < min_iso_corr:
                match = False

        else:
            if row['signal'] < row["idPar"][0]:
                match = False

            if (np.array(np.abs(row['mass error'])) > row["idPar"][1]).any():
                match = False

            if row['abundance score'] < row["idPar"][2]:
                match = False
        
            if row['isotope r2'] < row["idPar"][3]:
                match = False
        
        row['match'] = match
    return peak_df

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

def write_peak_dict(D, filename):
    """Write peak dictionary (sparse matrix) to h5 file.

    Parameters
    ----------
    D : csr
        Peak dictionary (sparse matrix)
    filename : str
        Full file path
    """

    # Write peak dictionary D in Scipy sparse CSR format into a h5 file
    with h5sparse.File(filename, 'w') as h5f:
        h5f.create_dataset('sparse/matrix', data=D)
    return
    """[summary]

    NOTE: !!! Deprecated !!!

    Parameters
    ----------
    x : [type]
        [description]
    y : [type]
        [description]
    ps : [type]
        [description]
    plot : bool, optional
        [description], by default False

    Returns
    -------
    [type]
        [description]
    """
    print('Warning: You are calling depreacated function: ''fit_single_peak''')
    # Fit peak position and resolution
    yn = y / np.max(y)
    pss = peakshape_spline(ps)
    ppos0 = x[ np.argmax(y) ]
    pres0 = 10000
    try:
        popt, _ = curve_fit( pss.spline,
                             x,
                             yn,
                             p0=[ppos0, pres0],
                             bounds=(0, np.inf) )
        ppos, pres = popt
        yhat = pss.spline(x, ppos, pres)
        residual = yn - yhat
        resn = norm(residual)
    except:
        print('Peak fit failed')
        ppos = pres = None
        yhat = np.zeros((len(x),))
        residual = yn
        resn = norm(yhat)
    if plot:
        plt.figure()
        plt.plot(x, yn)
        plt.plot(x, yhat)
        plt.plot(x, residual)
    return ppos, pres, resn