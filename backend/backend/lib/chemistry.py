from bisect import bisect_left

from .molmass import Formula


def get_exact_mz(formula_str):
    return Formula(formula_str).mz


def get_exact_isotope_mzs(formula_str):
    return Formula(formula_str).mz_spectrum()


def match_mz(mz, mz_list, tolerance=0.5):
    '''
    Find matching m/z values from a sorted list for a given m/z, within 
    tolerance.

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
    min_mz, max_mz = (mz - tolerance, mz + tolerance)
    i = bisect_left(mz_list, min_mz)
    match_mzs = []
    match_indeces = []
    while i < len(mz_list) and mz_list[i] <= max_mz:
        match_mzs.append(mz_list[i])
        match_indeces.append(i)
        i += 1
    return match_indeces, match_mzs
