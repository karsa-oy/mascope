from pathlib import Path
from contextlib import contextmanager
from typing import Iterable
import h5py
import numpy as np
import xarray as xr
import dask.array as da
from mascope_hardware.runtime import hardware_runtime


@contextmanager
def open_h5_file(datafile_path: str):
    """Context manager for safely opening and closing Tofwerk h5-files.

    :param datafile_path: Path to the Tofwerk HDF5 file (.h5) containing the data.
    :type datafile_path: str
    :yield: h5py File object
    """
    try:
        h5_file = h5py.File(datafile_path, "r")
        try:
            yield h5_file
        finally:
            # Ensure file is always closed
            if h5_file is not None:
                h5_file.close()
    except Exception as e:
        err_message = f"Failed to open the file {Path(datafile_path).name}: {e}"
        hardware_runtime.logger.error(err_message)
        raise Exception(err_message) from e


def get_signal(datafile_path: str, t1=None, t2=None):
    """
    Retrieve a full time-windowed signal from an HDF5 file.

    If start or end time (or both) are provided, returns signal time slice.
    t1=None is equal to t1=t_min, t2=None is equal to t2=t_max.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param t1: Optional start time in seconds (default is None).
    :type t1: float, optional
    :param t2: Optional end time in seconds (default is None).
    :type t2: float, optional
    :raises IndexError: If start time is greater than end time.
    :return: An xarray Dataset containing the signal data.
    :rtype: xr.Dataset
    """
    with open_h5_file(datafile_path) as h5_file:
        # Get signal HDF5 dataset reference
        signal_ref = h5_file["FullSpectra"]["TofData"]
        # Get m/z scale
        all_mzs = h5_file["FullSpectra"]["MassAxis"][:]
        # Get time scale
        scan_time = h5_file["TimingData"]["BufTimes"][:].reshape(-1)
        last_non_zero_scan = np.where(scan_time != 0)[0][-1]
        # Cut out zero scans
        scan_time = scan_time[: last_non_zero_scan + 1]
        # Total number of scans
        n_scans = scan_time.size

        if t1 is None and t2 is None:
            # Return full signal
            # Get signal array first, cut out zero scans
            signal_array = signal_ref[:].reshape(-1, signal_ref.shape[-1])[
                : last_non_zero_scan + 1, :
            ]
            # Convert to dask array
            signal_dask = da.from_array(signal_array, chunks="auto")
            # Init and return xarray Dataset with swapped dimensions
            return xr.Dataset(
                {"signal": (("mz", "time"), signal_dask.T)},
                coords={"mz": all_mzs, "time": scan_time},
            )

        if t1 > t2:
            err_message = f"Invalid time range: {t1} > {t2}"
            hardware_runtime.logger.error(err_message)
            raise ValueError(err_message)

        # Extract number of samples (of m/z points)
        n_samples = signal_ref.shape[-1]

        # Update start and end if are not provided
        start = 0 if t1 is None else np.abs(scan_time - t1).argmin()
        end = n_scans if t2 is None else np.abs(scan_time - t2).argmin() + 1

        # 1. flatten n_writes, n_bufs, n_segments dimensions
        # 2. group dimension coordinates
        # 3. get coordinate groups of the required scans in start:end range
        coordinates = np.indices(signal_ref.shape[:-1]).reshape(3, -1).T[start:end]

        # Preallocate output array
        signal_slice = np.empty((end - start, n_samples), dtype=signal_ref.dtype)

        # Populate result by iterating over the first three dimensions
        for ind, coord in enumerate(coordinates):
            signal_slice[ind, :] = signal_ref[coord[0], coord[1], coord[2], :]

        # Convert to dask array
        signal_dask = da.from_array(signal_slice, chunks="auto")

        # Init and return xarray Dataset with swapped dimensions
        return xr.Dataset(
            {"signal": (("mz", "time"), signal_dask.T)},
            coords={"mz": all_mzs, "time": scan_time[start:end]},
        )


def compute_sum_signal_in_time_range(
    datafile_path: str,
    t1: float = None,
    t2: float = None,
    average: bool = False,
) -> xr.core.dataarray.DataArray:
    """Computes sum signal in (t1, t2) time range

    t1=None is equal to t1=t_min, t2=None is equal to t2=t_max.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param t1: Optional start time in seconds (default is None).
    :type t1: float, optional
    :param t2: Optional end time in seconds (default is None).
    :type t2: float, optional
    :param average: If spectrum should be averaged, defaults to False
    :type average: bool, optional
    :return: Sum signal
    :rtype: xr.core.dataarray.DataArray
    """
    signal = get_signal(datafile_path, t1, t2)
    if average:
        return signal.mean(dim="time").signal.rename("sum_signal")
    return signal.sum(dim="time").signal.rename("sum_signal")


def get_tic_per_scan(
    datafile_path: str, timestamps: Iterable[float] | None = None
) -> tuple:
    """Calculate TIC per scan from HDF5 file.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param timestamps: Optional list of timestamps to filter TIC values.
    :type timestamps: Iterable[float], optional
    :return: Tuple of time and TIC values as numpy arrays
    :rtype: tuple
    """
    with open_h5_file(datafile_path) as h5_file:
        # Get signal HDF5 dataset reference
        signal_ref = h5_file["FullSpectra"]["TofData"]
        # Get time scale
        scan_timestamp = h5_file["TimingData"]["BufTimes"][:].reshape(-1)
        # Total number of non-zero scans
        n_scans = np.where(scan_timestamp != 0)[0][-1] + 1
        # Cut out zero scans
        scan_timestamp = scan_timestamp[:n_scans]
        # Prealocate scan_tic array
        scan_tic = np.empty(n_scans)
        # 1. flatten n_writes, n_bufs, n_segments dimensions
        # 2. group dimension coordinates
        # 3. get coordinate groups
        coordinates = np.indices(signal_ref.shape[:-1]).reshape(3, -1).T
        coordinates = coordinates[:n_scans]
        # Populate TIC array by iterating over the first three dimensions
        for ind, coord in enumerate(coordinates):
            scan_tic[ind] = signal_ref[coord[0], coord[1], coord[2], :].sum()
        # Get total TIC
        total_tic = h5_file["FullSpectra"]["SumSpectrum"][:].sum()
        # Correct TIC per scan by total TIC
        scan_tic = scan_tic / scan_tic.sum() * total_tic

        if timestamps:
            # Filter TIC values by timestamps
            timestamps = np.asarray(timestamps)
            # Find closest scan index for each timestamp
            scan_indices = np.searchsorted(scan_timestamp, timestamps)
            # Ensure indices are within valid range
            scan_indices = np.clip(scan_indices, 0, len(scan_timestamp) - 1)
            # Extract scan TIC and scan timestamps values for the closest scan index
            scan_tic = scan_tic[scan_indices]
            scan_timestamp = scan_timestamp[scan_indices]

        return scan_timestamp, scan_tic
