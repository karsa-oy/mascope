from bisect import bisect_left

from .molmass import Formula


def get_exact_mz(formula_str):
    return Formula(formula_str).mz

def get_exact_isotope_mzs(formula_str):
    return Formula(formula_str).mz_spectrum()

def match_mz(mz, mz_list, tolerance=0):
    ''' Find matching m/z values from a sorted list for a given m/z, within tolerance.

    Parameters
    ----------
    mz : float
        m/z value to match.
    mz_list : list
        SORTED list of m/z values to find matches from.
    tolerance : float, optional
        Match tolerance [ppm], by default 0.
    
    Returns
    -------
    matches : tuple
        Tuple containing two lists: indices and mz values from 'mz_list',
        matching 'mz' within given tolerance.
    '''
    dmz = tolerance*1e-6 * mz # ppm to absolute diff
    lo, hi = (mz-dmz, mz+dmz)
    i = bisect_left(mz_list, lo)
    match_mzs = []
    match_is = []
    while i < len(mz_list) and mz_list[i] <= hi:
        match_mzs.append(mz_list[i])
        match_is.append(i)
        i += 1
    return match_is, match_mzs