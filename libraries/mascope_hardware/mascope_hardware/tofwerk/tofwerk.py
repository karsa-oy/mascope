from pathlib import Path
from contextlib import contextmanager
from typing import Iterable, Optional, Tuple
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
            if h5_file is not None:
                h5_file.close()
    except Exception as e:
        err_message = f"Failed to open the file {Path(datafile_path).name}: {e}"
        hardware_runtime.logger.error(err_message)
        raise Exception(err_message) from e


def get_signal(
    datafile_path: str,
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    mz_min: Optional[float] = None,
    mz_max: Optional[float] = None,
) -> xr.Dataset:
    """
    Retrieve a full time-windowed signal from an HDF5 file. Allows slicing by time and m/z range.

    t_min=None is equal to min scan time, t_max=None is equal to max scan time.
    mz_min=None is equal to min m/z, mz_max=None is equal to max m/z.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param t_min: Optional start time in seconds (default is None).
    :type t_min: float, optional
    :param t_max: Optional end time in seconds (default is None).
    :type t_max: float, optional
    :param mz_min: Optional start m/z value (default is None).
    :type mz_min: float, optional
    :param mz_max: Optional end m/z value (default is None).
    :type mz_max: float, optional
    :raises ValueError: If start time is greater than end time, or start m/z is greater than end m/z.
    :raises Exception: If an error occurs while opening the HDF5 file.
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

        # Determine m/z range
        mz_min = min(all_mzs) if mz_min is None else mz_min
        mz_max = max(all_mzs) if mz_max is None else mz_max

        # Check m/z range
        if mz_min > mz_max:
            raise ValueError(f"Invalid m/z range: {mz_min} > {mz_max}")
        # Check if provided mzs have intersection with the mzs in the file
        if mz_min > all_mzs[-1] or mz_max < all_mzs[0]:
            raise ValueError(
                f"Provided m/z range ({mz_min}, {mz_max}) is out of the sample file m/z range ({all_mzs[0]:.1f}, {all_mzs[-1]:.1f})"
            )

        # Find indices of m/z range
        mz_start_ind = np.abs(all_mzs - mz_min).argmin()
        mz_end_ind = np.abs(all_mzs - mz_max).argmin()

        # Calculate number of samples (of m/z points)
        n_samples = mz_end_ind - mz_start_ind + 1

        if t_min is None and t_max is None:
            # Slice the signal between mz_start_ind and mz_end_ind
            signal_array = signal_ref[:, :, :, mz_start_ind : mz_end_ind + 1]
            # Reshape the signal array to 2D
            signal_array = signal_array.reshape(-1, signal_array.shape[-1])[
                : last_non_zero_scan + 1, :
            ]
            # Convert to dask array
            signal_dask = da.from_array(signal_array, chunks="auto")
            # Init and return xarray Dataset with swapped dimensions
            return xr.Dataset(
                {"signal": (("mz", "time"), signal_dask.T)},
                coords={
                    "mz": all_mzs[mz_start_ind : mz_end_ind + 1],
                    "time": scan_time,
                },
            )

        if t_min is not None and t_max is not None and t_min > t_max:
            raise ValueError(f"Invalid time range: {t_min} > {t_max}")

        # Find indices of time range
        t_start_ind = 0 if t_min is None else np.abs(scan_time - t_min).argmin()
        t_end_ind = n_scans - 1 if t_max is None else np.abs(scan_time - t_max).argmin()

        # 1. flatten n_writes, n_bufs, n_segments dimensions
        # 2. group dimension coordinates
        # 3. get coordinate groups of the required scans in start:end range
        coordinates = (
            np.indices(signal_ref.shape[:-1])
            .reshape(3, -1)
            .T[t_start_ind : t_end_ind + 1]
        )
        # Preallocate output array
        signal_slice = np.empty(
            (t_end_ind - t_start_ind + 1, n_samples), dtype=signal_ref.dtype
        )
        # Populate result by iterating over the first three dimensions
        for ind, coord in enumerate(coordinates):
            signal_slice[ind, :] = signal_ref[
                coord[0], coord[1], coord[2], mz_start_ind : mz_end_ind + 1
            ]

        signal_dask = da.from_array(signal_slice, chunks="auto")
        # Init and return xarray Dataset with swapped dimensions
        return xr.Dataset(
            {"signal": (("mz", "time"), signal_dask.T)},
            coords={
                "mz": all_mzs[mz_start_ind : mz_end_ind + 1],
                "time": scan_time[t_start_ind : t_end_ind + 1],
            },
        )


def compute_sum_signal_in_time_range(
    datafile_path: str,
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    average: bool = False,
) -> xr.core.dataarray.DataArray:
    """
    Computes sum signal in (t_min, t_max) time range.

    t_min=None is equal to min scan time, t_max=None is equal to max scan time.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param t_min: Optional start time in seconds (default is None).
    :type t_min: float, optional
    :param t_max: Optional end time in seconds (default is None).
    :type t_max: float, optional
    :param average: If spectrum should be averaged, defaults to False.
    :type average: bool, optional
    :return: Sum signal.
    :rtype: xr.core.dataarray.DataArray
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

        # Determine time range
        t_start_ind = 0 if t_min is None else np.abs(scan_time - t_min).argmin()
        t_end_ind = n_scans - 1 if t_max is None else np.abs(scan_time - t_max).argmin()

        # 1. flatten n_writes, n_bufs, n_segments dimensions
        # 2. group dimension coordinates
        # 3. get coordinate groups of the scans
        coordinates = np.indices(signal_ref.shape[:-1]).reshape(3, -1).T
        start_coord = coordinates[t_start_ind]
        end_coord = coordinates[t_end_ind]

        # Initialize sum signal array
        sum_signal = np.zeros_like(all_mzs)

        # Process the signal in chunks to save memory
        for i in range(start_coord[0], end_coord[0]):
            chunk = signal_ref[i, :, :, :]
            # Sum the signal within the chunk
            chunk_sum = chunk.sum(axis=(0, 1))
            sum_signal += chunk_sum

        # Sum the signal within the last chunk
        last_chunk = signal_ref[end_coord[0], : end_coord[1] + 1, : end_coord[2] + 1, :]
        last_chunk_sum = last_chunk.sum(axis=(0, 1))
        sum_signal += last_chunk_sum

        if average:
            sum_signal /= t_end_ind - t_start_ind + 1

        sum_signal_da = xr.DataArray(sum_signal, dims=["mz"], coords={"mz": all_mzs})
        return sum_signal_da.rename("sum_signal")


def get_tic_per_scan(
    datafile_path: str, timestamps: Optional[Iterable[float]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate TIC per scan from HDF5 file.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param timestamps: Optional list of timestamps to filter TIC values.
    :type timestamps: Iterable[float], optional
    :return: Tuple of time and TIC values as numpy arrays.
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

        # 1. flatten n_writes, n_bufs, n_segments dimensions
        # 2. group dimension coordinates
        # 3. get coordinate groups
        coordinates = np.indices(signal_ref.shape[:-1]).reshape(3, -1).T
        coordinates = coordinates[:n_scans]

        # Prealocate scan_tic array
        scan_tic = np.empty(n_scans)
        # Populate TIC array by iterating over the first three dimensions
        for ind, coord in enumerate(coordinates):
            scan_tic[ind] = signal_ref[coord[0], coord[1], coord[2], :].sum()

        # Get total TIC
        total_tic = h5_file["FullSpectra"]["SumSpectrum"][:].sum()
        # Correct TIC per scan by total TIC
        scan_tic = scan_tic / scan_tic.sum() * total_tic

        if timestamps is not None:
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
