import os
from typing import Iterable, Literal

import dask.array as da
import numpy as np
import xarray as xr
import zarr

from mascope_file.name import (
    parse_path_from_item_filename,
    filename_to_zarr_path,
    get_sample_file_type,
    filename_to_datafile_path,
)
from mascope_file.io import load_file, get_zarr_synchronizer, load_array, load_coord
from mascope_thermo import thermo
from mascope_tofwerk import tofwerk

from mascope_signal.runtime import runtime


def get_scan_timestamps(base_filename: str) -> np.ndarray:
    """
    Retrieve scan timestamps from a given file based on its type.

    :param base_filename: Sample file name.
    :type base_filename: str
    :return: An array of scan timestamps extracted from the sample file.
    """
    sample_type = get_sample_file_type(base_filename)
    match sample_type:
        case "tof_zarr" | "orbi_zarr":
            signal_path = filename_to_zarr_path(base_filename, "signal")

            sync = get_zarr_synchronizer(signal_path)
            z = zarr.open(signal_path, mode="r", synchronizer=sync)
            time_array = z["time"][:]
            if not time_array.size:
                # Perhaps the coordinate is hiding in groups
                groups = list(z.group_keys())
                # Load time coordinate from each group and concatenate
                time_arrays = [z[group]["time"][:] for group in groups]
                time_array = np.concatenate(time_arrays)
            return time_array
        case "orbi_raw":
            datafile_path = os.path.join(
                parse_path_from_item_filename(base_filename), "data.raw"
            )
            return thermo.get_scan_timestamps(datafile_path)
        case "tof_h5":
            datafile_path = os.path.join(
                parse_path_from_item_filename(base_filename), "data.h5"
            )
            return tofwerk.get_scan_timestamps(datafile_path)


def get_sum_signal(filename: str, average: bool = False) -> xr.DataArray:
    """Calculates the sum spectrum of a given filename

    :param filename: Name of the target file
    :type filename: str
    :param average: Return avereage spectrum instead of sum. By default false (return sum).
    :type average: bool
    :return: Sum/average spectrum
    :rtype: xr.core.dataarray.DataArray
    """
    try:
        # Load precomputed sum spectrum from zarr file
        sample_file = load_file(filename, vars=["sum_signal"])
        sum_signal = sample_file.sum_signal
    except (AttributeError, FileNotFoundError):
        base_filename = sample_file.props["filename"]
        sum_signal = sum_signal_for_time_range(base_filename)
        filename_sum_signal = filename_to_zarr_path(base_filename, "sum_signal")

        try:
            sum_signal.to_zarr(filename_sum_signal)
        except FileNotFoundError as e:
            if ".partial" in str(e):
                raise Exception(
                    f"The path is probably too long: {filename_sum_signal}"
                ) from e
            else:
                raise

    if average:
        base_filename = sample_file.props["filename"]
        time_coord = get_scan_timestamps(base_filename)
        return sum_signal / time_coord.size
    else:
        return sum_signal


def sum_signal_for_time_range(
    base_filename: str, t_min: float = None, t_max: float = None, average: bool = False
) -> xr.DataArray:
    """Calculates the sum spectrum of a given filename in given time range [t_min, t_max]

    :param base_filename: Name of the target file
    :type base_filename: str
    :param t_min: Min time value [s], defaults to None (takes the first time coord available)
    :type t_min: float, optional
    :param t_max: Max time value [s], defaults to None (takes the last time coord available)
    :type t_max: float, optional
    :param average: Return avereage spectrum instead of sum. By default false (return sum).
    :type average: bool, optional
    :raises NotImplementedError: The case for h5 TOF files is not implemented
    :return: Sum/average spectrum in a time range
    :rtype: xr.core.dataarray.DataArray
    """
    sample_type = get_sample_file_type(base_filename)
    sample_path = parse_path_from_item_filename(base_filename)

    match sample_type:
        case "tof_zarr" | "orbi_zarr":
            # Load the 'signal' data for specific time range
            signal = load_signal(base_filename)

            # Find the closest time points in the data to the provided time range
            closest_t_min = (
                signal.time.sel(time=t_min, method="nearest").item()
                if t_min is not None
                else signal.time.min()
            )
            closest_t_max = (
                signal.time.sel(time=t_max, method="nearest").item()
                if t_max is not None
                else signal.time.max()
            )

            # Slice the dataset for the time range
            signal_slice = signal.sel(time=slice(closest_t_min, closest_t_max))

            # Get the number of data points in the time coordinate
            time_data_points = signal_slice.sizes["time"]

            # Interpolate missing values
            signal_slice = signal_slice.interpolate_na(dim="mz", method="linear")
            # Fill the remaining nan values with zeros if any
            signal_slice = signal_slice.fillna(0)

            sum_signal_dask = da.from_array(
                signal_slice.sum(dim="time").signal.values, chunks="auto"
            )

            sum_signal = xr.DataArray(
                data=sum_signal_dask,
                dims=["mz"],
                coords={"mz": signal_slice.mz},
                name="sum_signal",
            )
            if average:
                sum_signal /= time_data_points
        case "orbi_raw":
            datafile_path = os.path.join(sample_path, "data.raw")
            sum_signal = thermo.compute_sum_signal_in_time_range(
                datafile_path, t_min, t_max, average
            )
        case "tof_h5":
            datafile_path = os.path.join(sample_path, "data.h5")
            sum_signal = tofwerk.compute_sum_signal_in_time_range(
                datafile_path, t_min, t_max, average
            )
    return sum_signal


def load_signal(
    base_filename: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> xr.Dataset:
    """Load signal from the sample file

    Suports m/z and time slicing.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param t_min: Min time value [s], defaults to None
    :type t_min: float, optional
    :param t_max: Max time value [s], defaults to None
    :type t_max: float, optional
    :param mz_min: Min m/z value, defaults to None
    :type mz_min: float, optional
    :return: The signal with m/z and time coordinates
    :rtype: xr.Dataset
    """
    runtime.logger.debug(f"Loading signal from {base_filename}")

    sample_type = get_sample_file_type(base_filename)
    sample_path = parse_path_from_item_filename(base_filename)

    if not os.path.exists(sample_path):
        raise FileNotFoundError(sample_path)

    try:
        match sample_type:
            case "tof_zarr" | "orbi_zarr":
                signal_ds = load_array(base_filename, "signal")
                if sample_type == "tof_zarr":
                    # Correct by scan duration
                    interval_ds = load_array(base_filename, "signal_period")
                    signal_ds = signal_ds / interval_ds.signal_period

                # Check time range
                t_min = signal_ds.time.min() if t_min is None else t_min
                t_max = signal_ds.time.max() if t_max is None else t_max
                if t_min > t_max:
                    raise ValueError(f"Invalid time range: {t_min} > {t_max}")

                # Check m/z range
                mz_min = signal_ds.mz.min() if mz_min is None else mz_min
                mz_max = signal_ds.mz.max() if mz_max is None else mz_max
                if mz_min > mz_max:
                    raise ValueError(f"Invalid m/z range: {mz_min} > {mz_max}")

                signal_ds_sliced = signal_ds.sel(
                    time=slice(t_min, t_max), mz=slice(mz_min, mz_max)
                )
                # Check if sliced signal contains data
                if not signal_ds_sliced.signal.size:
                    raise ValueError(
                        f"""No data found in the specified time or m/z range.
                M/z range of the sample file: {signal_ds.mz.min():.1f} - {signal_ds.mz.max():.1f}
                Time range: {signal_ds.time.min():.1f} - {signal_ds.mz.max():.1f} s.
                """
                    )
                return signal_ds_sliced
            case "orbi_raw":
                datafile_path = os.path.join(sample_path, "data.raw")
                polarity = sample_path.split("_")[-1]
                return thermo.get_signal(
                    datafile_path, t_min, t_max, mz_min, mz_max, polarity
                )
            case "tof_h5":
                datafile_path = os.path.join(sample_path, "data.h5")
                signal = tofwerk.get_signal(datafile_path, t_min, t_max, mz_min, mz_max)
                # Check if m/z axis calibration was applied to sample file
                # by comparing m/z in sum signal and in h5 file
                sum_signal_mz = get_sum_signal(base_filename).mz.values
                if np.array_equal(signal.mz.values, sum_signal_mz):
                    # m/z axis match, no calibration was previously applied
                    return signal
                # M/z in sum signal and in h5 file do not match, replace m/z in signal
                return signal.assign_coords(mz=sum_signal_mz)
    except Exception as e:
        runtime.logger.error(f"Error loading signal from {base_filename}: {e})")
        # Return empty signal dataset with "mz" and "time" coordinates in case of error
        return xr.Dataset(
            {
                "signal": (["mz", "time"], np.zeros((0, 0))),
                "mz": (["mz"], np.zeros(0)),
                "time": (["time"], np.zeros(0)),
            }
        )


def get_tic_per_scan(base_filename: str, timestamps: Iterable | None = None) -> tuple:
    """Get TIC per scan from the sample file depending on the file type

    :param base_filename: Sample file filename
    :type base_filename: str
    :param timestamps: Optional timestamps of the scans, defaults to None
    :type timestamps: Iterable | None
    :return: TIC time and TIC per scan as numpy arrays
    :rtype: tuple
    """
    sample_type = get_sample_file_type(base_filename)
    datafile_path = filename_to_datafile_path(base_filename)
    match sample_type:
        case "tof_h5":
            tic_time, tic_per_scan = tofwerk.get_tic_per_scan(datafile_path, timestamps)
        case "orbi_raw":
            tic_time, tic_per_scan = thermo.get_tic_per_scan(datafile_path, timestamps)
        case "tof_zarr" | "orbi_zarr":
            zarr_path = filename_to_zarr_path(base_filename, "signal")
            sync = get_zarr_synchronizer(zarr_path)
            z = zarr.open(zarr_path, mode="r", synchronizer=sync)

            # Get sum of counts along mz coordinate for each time coordinate
            signal_array = da.from_zarr(z["signal"])
            tic_per_scan = signal_array.sum(axis=0).compute()
            # Check if TIC values are available
            if not tic_per_scan.size:
                # Get list of groups in zarr file
                groups = list(z.group_keys())

                # Load signal to dask arrays for each group
                signal_arrays = [da.from_zarr(z[group]["signal"]) for group in groups]
                # Sum signal arrays along mz coordinate
                group_tic_per_scan = [
                    da.nan_to_num(array, 0.0).sum(axis=0).compute()
                    for array in signal_arrays
                ]
                # Concatenate TIC values from each group
                tic_per_scan = np.concatenate(group_tic_per_scan, axis=0)

            # Correct TIC values by total TIC value if available
            try:
                total_tic = load_file(base_filename, vars=[]).props["tic"]
                tic_per_scan = tic_per_scan / tic_per_scan.sum() * total_tic
            except KeyError:
                runtime.logger.warning(
                    "Total TIC value is not available in the sample file"
                )

            # Get time coordinate as numpy array
            tic_time = load_coord(base_filename, "signal", "time")

            if timestamps:
                # Filter TIC values by timestamps
                timestamps = np.asarray(timestamps)
                # Find closest scan index for each timestamp
                scan_indices = np.searchsorted(tic_time, timestamps)
                # Ensure indices are within valid range
                scan_indices = np.clip(scan_indices, 0, len(tic_time) - 1)
                # Extract scan TIC and scan timestamps values for the closest scan index
                tic_per_scan = tic_per_scan[scan_indices]
                tic_time = tic_time[scan_indices]

    return tic_time, tic_per_scan


def get_peak_profiles(
    base_filename: str,
    mzs: Iterable[float],
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> xr.DataArray:
    """Get peak profiles for given m/z values in the time range [t_min, t_max]

    :param datafile_path: Path to the data file
    :type datafile_path: str
    :param mzs: List of target m/z values
    :type mzs: Iterable[float]
    :param t_min: Left border of the time range [s], defaults to None
    :type t_min: float, optional
    :param t_max: Right border of the time range [s], defaults to None
    :type t_max: float, optional
    :param polarity: Polarity of the scan to extract, defaults to None (get all scans)
    :type polarity: str, optional
    :return: Peak profiles for the given m/z values
    :rtype: xr.DataArray
    """
    sample_type = get_sample_file_type(base_filename)
    datafile_path = filename_to_datafile_path(base_filename)
    match sample_type:
        case "orbi_raw":
            return thermo.get_peak_profiles(datafile_path, mzs, t_min, t_max, polarity)
        case "tof_h5":
            # Get calibrated m/z values
            sum_signal_mz = get_sum_signal(base_filename).mz.values
            return tofwerk.get_peak_profiles(
                datafile_path, mzs, sum_signal_mz, t_min, t_max
            )
        case "tof_zarr" | "orbi_zarr":
            signal = load_signal(base_filename, t_min, t_max)
            # Interpolate missing values in mz dimension using linear method.
            signal = signal.interpolate_na(dim="mz", method="linear")
            # Fill the remaining nan values with zeros
            signal = signal.fillna(0)
            # Extract the peak profiles for the closest m/z values
            return signal.sel(mz=mzs, method="nearest").signal
