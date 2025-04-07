from typing import Literal
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_backend.api.new.match.params.schema import (
    ORBI_FITTING_THRESHOLD,
    TOF_FITTING_THRESHOLD,
)
from mascope_file.name import get_instrument_type
from mascope_signal.peak import detect_peaks


async def compute_peaks(
    filename: str, if_exists: Literal["append", "replace"] = "append"
) -> tuple:
    """Compute peaks for a sample file.
    This function loads the instrument functions, determines the instrument type,
    sets the threshold based on the instrument type, and then detects peaks in the
    sample file. The detected peaks are returned along with the sample file.

    :param filename: Sample file name
    :type filename: str
    :param if_exists: Whether to append or replace existing peaks, defaults to "append"
    :type if_exists: Literal["append", "replace"], optional
    :return: Returns the sample file and a list of detected peaks.
    :rtype: tuple
    """

    # Step 1: Load instrument functions and determine instrument type.
    instrument_functions = await read_instrument_functions(filename=filename)
    instrument_type = get_instrument_type(filename)

    # Step 2: Set threshold based on instrument type.
    if instrument_type == "orbi":
        threshold = ORBI_FITTING_THRESHOLD
    if instrument_type == "tof":
        threshold = TOF_FITTING_THRESHOLD

    # Step 3: Detect peaks.
    sample_file, list_of_peaks = await detect_peaks(
        filename,
        instrument_functions,
        threshold,
        u_list=None,
        if_exists=if_exists,
        return_peak_mzs=True,
        instrument_type=instrument_type,
    )
    return sample_file, list_of_peaks
