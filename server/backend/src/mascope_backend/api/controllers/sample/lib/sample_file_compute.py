from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_signal.peak import get_peak_detector


async def compute_peaks(filename: str):
    """Compute peaks for a sample file.
    This function loads the instrument functions, and then detects peaks in the
    sample file.

    :param filename: Sample file name
    :type filename: str
    """

    # Step 1: Load instrument functions and determine instrument type.
    instrument_functions = await read_instrument_functions(filename=filename)

    # Step 2: Detect peaks in the sample file.
    peak_detector = get_peak_detector(filename, instrument_functions)
    await peak_detector.detect_peaks()
    peak_detector.write_peaks_to_zarr()
