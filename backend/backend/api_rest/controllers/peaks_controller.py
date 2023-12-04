from lib.file_func import load_file
from lib.peak import get_peaks


async def get_sample_file_peaks(filename: str) -> dict:
    """Get peaks of given sample file

    :param filename: Sample file filename
    :type filename: str
    :raises HTTPException: Raised if sample file is not found
    :return: Dictionary with keys:
        "mz": list of m/z of the peaks in sample file
        "intensity": peak intensity (area)
    :rtype: dict
    """
    try:
        sample_file = load_file(filename, vars=["peak_areas"])
        peaks = get_peaks(sample_file, "area").sum(dim="time")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file with name {filename} not found",
        )

    return {
        "mz": list(peaks.mz.values.astype(float)),
        "intensity": list(peaks.values.astype(float)),
    }


async def get_sample_file_peak_timeseries(
    filename: str, peak_mz: float, peak_mz_tolerance_ppm: float
) -> dict:
    """Get timeseries of a given peak in a given sample file.

    Returns the timeseries of a closest peak to a given m/z, if found
    within given m/z tolerance.

    :param filename: Sample file filename
    :type filename: str
    :param peak_mz: m/z of the peak to get timeseries for
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: Tolerance for m/z difference
        for the requested peak and the nearest one found from data
    :type peak_mz_tolerance_ppm: float
    :raises HTTPException: Raised if sample file is not found
    :return: Dictionary with keys:
        "mz": m/z of the peak in sample file
        "intensity": peak height at time points
        "time": time coordinates
    :rtype: dict
    """
    try:
        sample_file = load_file(filename, vars=["peak_heights"])
        peaks = get_peaks(sample_file, "height")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file with name {filename} not found",
        )
    # From sample file peaks, select nearest to requested peak m/z
    peak_timeseries = peaks.sel(mz=peak_mz, method="nearest")
    peak_mz_data = peak_timeseries.mz.item()
    # Calculate difference of the sample peak m/z to requested peak m/z
    mz_diff = peak_mz_data - peak_mz  # [Th]
    mz_diff_ppm = mz_diff / peak_mz * 1e6  # [ppm]
    if abs(mz_diff_ppm) > peak_mz_tolerance_ppm:
        # No peak found within given m/z tolerance
        return {
            "mz": None,
            "intensity": [],
            "time": [],
        }

    return {
        "mz": peak_mz_data,
        "intensity": list(peak_timeseries.values),
        "time": list(peak_timeseries.time.values),
    }
