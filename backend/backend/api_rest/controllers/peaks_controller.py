from lib.file_func import load_file
from lib.peak import get_peaks


async def get_sample_file_peaks(filename: str):
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
):
    try:
        sample_file = load_file(filename, vars=["peak_heights"])
        peaks = get_peaks(sample_file, "height")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file with name {filename} not found",
        )

    peak_timeseries = peaks.sel(mz=peak_mz, method="nearest")
    peak_mz_data = peak_timeseries.mz.item()
    mz_diff = peak_mz_data - peak_mz
    mz_diff_ppm = mz_diff / peak_mz * 1e6
    if abs(mz_diff_ppm) > peak_mz_tolerance_ppm:
        return {}

    return {
        "mz": peak_mz_data,
        "intensity": list(peak_timeseries.values),
        "time": list(peak_timeseries.time.values),
    }
