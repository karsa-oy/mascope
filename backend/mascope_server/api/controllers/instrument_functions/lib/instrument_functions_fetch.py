import numpy as np

from mascope_server.api.controllers.instrument_functions.instrument_functions_controller import (
    get_instrument_function,
)
from mascope_lib.instrument_functions import r_orbi


async def read_instrument_functions(filename):
    """
    Retrieves and processes instrument function parameters for a given sample file.

    This function fetches instrument function details, such as peak shape and resolution function,
    and prepares the resolution function R for use in m/z matching.

    :param filename: Name of the sample file for which instrument functions are required.
    :type filename: str
    :return: A tuple containing peak shape details as a dictionary and a resolution function R as a callable.
             The peak shape details include parameters defining the shape of peaks in the mass spectrum.
             The resolution function R takes a mass (m) and returns the resolution at that mass.
    :rtype: tuple(dict, function)
    """
    instrument_functions = await get_instrument_function(filename)
    peakshape = instrument_functions["peakshape"]
    R_p = instrument_functions["resolution_function"]
    if len(R_p) == 1:
        # Use native Orbitrap resolution function
        p1 = R_p[0]
        R = lambda m: r_orbi(m, p1)
    elif len(R_p) == 2:
        # Use resolution function from Junninen's thesis for TOF
        p1, p2 = R_p
        R = lambda m: m / (p1 * m + p2)
    elif len(R_p) == 3:
        # Use 2nd order polynomial (backwards compatibility for Orbitrap) TODO: legacy
        R = np.poly1d(R_p)
    return peakshape, R
