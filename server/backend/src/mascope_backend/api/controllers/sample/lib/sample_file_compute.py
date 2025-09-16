from typing import Literal
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_signal.peak import get_peak_detector


async def compute_peaks(
    filename: str, if_exists: Literal["append", "replace"] = "append"
) -> "xarray.Dataset":  # noqa: F821
    """Compute peaks for a sample file.
    This function loads the instrument functions, and then detects peaks in the
    sample file. The detected peaks are returned along with the sample file.

    :param filename: Sample file name
    :type filename: str
    :param if_exists: Whether to append or replace existing peaks, defaults to "append"
    :type if_exists: Literal["append", "replace"], optional
    :return: Returns the sample file.
    :rtype: xarray.Dataset
    """

    # Step 1: Load instrument functions and determine instrument type.
    instrument_functions = await read_instrument_functions(filename=filename)

    # Step 2: Detect peaks in the sample file.
    peak_detector = get_peak_detector(filename, instrument_functions)
    sample_file = await peak_detector.detect_peaks()
    return sample_file
