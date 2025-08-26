from pathlib import Path
from contextlib import contextmanager
from typing import Iterable, Tuple
import h5py
import numpy as np
import xarray as xr
import dask.array as da
from mascope_tofwerk.runtime import runtime


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
        runtime.logger.error(err_message)
        raise Exception(err_message) from e


def get_polarity_options(datafile_path: str) -> str:
    """
    Retrieve the polarity based on the IonMode attribute in the HDF5 file.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :return: polarity value, either "+" or "-".
    :rtype: str
    """
    with open_h5_file(datafile_path) as h5_file:
        ion_mode = h5_file.attrs.get("IonMode", "").lower()
        if ion_mode == b"negative":
            return "-"
        elif ion_mode == b"positive":
            return "+"
        else:
            raise ValueError(f"Unexpected IonMode value: {ion_mode}")


def get_conversion_coefficient(h5_file) -> float:
    """
    Calculate the conversion coefficient to convert signal intensity from [mV] to [ions/sec].

    :param h5_file: Opened HDF5 file object.
    :type h5_file: h5py.File
    :return: Conversion coefficient.
    :rtype: float
    """
    single_ion_signal = (
        h5_file["FullSpectra"].attrs["Single Ion Signal"][0] * 1e-9
    )  # [mV·s/ion]
    sample_interval = h5_file["FullSpectra"].attrs["SampleInterval"][0]  # [s]
    tof_period = h5_file["TimingData"].attrs["TofPeriod"][0] * 1e-9  # [s]
    tof_frequency = 1 / tof_period  # [ext/s]
    n_extractions = h5_file.attrs["NbrWaveforms"][0]  # [ext]

    # Coefficient to convert signal intensity from [mV] -> [ions/sec]
    conversion_coefficient = (
        sample_interval * tof_frequency / single_ion_signal / n_extractions
    )  # [ions/(mV·s)]

    return conversion_coefficient


def get_signal(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
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

        # Coefficient to convert signal intensity from [mV] -> [ions/sec]
        conversion_coefficient = get_conversion_coefficient(h5_file)

        # Convert [mV] -> [ions/sec]
        signal_slice *= conversion_coefficient

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
    t_min: float | None = None,
    t_max: float | None = None,
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
    :return: Sum signal [ions/sec] in the specified time range.
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
            sum_signal = sum_signal / (t_end_ind - t_start_ind + 1)

        # Coefficient to convert signal intensity from [mV] -> [ions/sec]
        conversion_coefficient = get_conversion_coefficient(h5_file)

        # Convert [mV] -> [ions/sec]
        sum_signal *= conversion_coefficient

        sum_signal_da = xr.DataArray(sum_signal, dims=["mz"], coords={"mz": all_mzs})
        return sum_signal_da.rename("sum_signal")


def get_tic_per_scan(
    datafile_path: str, timestamps: Iterable[float] | None = None
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

        sum_spec = h5_file["FullSpectra"]["SumSpectrum"][:]
        # Convert to ions/sec
        sum_spec *= get_conversion_coefficient(h5_file)
        # Get total TIC
        total_tic = sum_spec.sum()
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


def get_scan_timestamps(
    datafile_path: str, t_min: float | None = None, t_max: float | None = None
) -> np.ndarray:
    """
    Retrieve scan timestamps from the HDF5 file, optionally filtering by a time range.

    :param datafile_path: Path to the HDF5 file containing spectrum data.
    :type datafile_path: str
    :param t_min: Optional start time in seconds (default is None).
    :type t_min: float, optional
    :param t_max: Optional end time in seconds (default is None).
    :type t_max: float, optional
    :return: Array of scan timestamps within the specified time range.
    :rtype: np.ndarray
    """
    with open_h5_file(datafile_path) as h5_file:
        # Get time scale
        scan_timestamp = h5_file["TimingData"]["BufTimes"][:].reshape(-1)
        # Total number of non-zero scans
        n_scans = np.where(scan_timestamp != 0)[0][-1] + 1
        # Cut out zero scans
        scan_timestamp = scan_timestamp[:n_scans]

        # Apply time filtering if t_min or t_max is provided
        if t_min is not None:
            scan_timestamp = scan_timestamp[scan_timestamp >= t_min]
        if t_max is not None:
            scan_timestamp = scan_timestamp[scan_timestamp <= t_max]

        return scan_timestamp


def get_peak_profiles(
    datafile_path: str,
    mzs: Iterable[float],
    true_mz_axis: Iterable[float],
    t_min: float | None = None,
    t_max: float | None = None,
) -> xr.Dataset:
    """Extracts the peak profiles for the specified m/z values in the time range (t_min, t_max).

    :param datafile_path: Path to the Tofwerk HDF5 file (.h5) containing the data.
    :type datafile_path: str
    :param mzs: array of m/z values for which peak profiles are required.
    :type mzs: Iterable[float]
    :param true_mz_axis: Calibrated m/z axis values.
    :type true_mz_axis: Iterable[float]
    :param t_min: Start time [s], defaults to None
    :type t_min: float, optional
    :param t_max: End time [s], defaults to None
    :type t_max: float, optional
    :return: An xarray Dataset containing the peak profiles
    :rtype: xr.Dataset
    """
    with open_h5_file(datafile_path) as h5_file:
        # Make sure mzs are numpy array
        mzs = np.asarray(mzs)
        # Get full time range
        scan_time = h5_file["TimingData"]["BufTimes"][:].reshape(-1)
        last_non_zero_scan = np.where(scan_time != 0)[0][-1]
        scan_time = scan_time[: last_non_zero_scan + 1]

        # Coefficient to convert signal intensity from [mV] -> [ions/sec]
        conv_coeff = get_conversion_coefficient(h5_file)

        # Check if t_min and t_max are passed
        t_min = scan_time[0] if t_min is None else t_min
        t_max = scan_time[-1] if t_max is None else t_max

        # Filter by time range
        time_mask = (scan_time >= t_min) & (scan_time <= t_max)
        scan_time = scan_time[time_mask]

        # Get signal HDF5 dataset reference
        signal_ref = h5_file["FullSpectra"]["TofData"]

        # Find indices of m/z range
        mz_start_ind = np.abs(true_mz_axis - mzs.min()).argmin() - 1
        mz_end_ind = np.abs(true_mz_axis - mzs.max()).argmin() + 1
        true_mz_slice = true_mz_axis[mz_start_ind : mz_end_ind + 1]

        # Initialize output array
        peak_profiles = np.zeros((len(mzs), len(scan_time)))

        # Get the coordinates of the scans
        coordinates = np.indices(signal_ref.shape[:-1]).reshape(3, -1).T
        # Keep same subset of coordinates as time_mask (they correspond in order)
        coordinates = coordinates[time_mask]

        # Populate result by iterating over the scans
        for j, coord in enumerate(coordinates):
            spec_segment = signal_ref[
                coord[0], coord[1], coord[2], mz_start_ind : mz_end_ind + 1
            ]

            spec_segment *= conv_coeff
            peak_profiles[:, j] = np.interp(
                mzs, true_mz_slice, spec_segment, left=0.0, right=0.0
            )

        # Convert to dask array
        peak_profiles_dask = da.from_array(peak_profiles, chunks=("auto", "auto"))

        # Export xarray array with time and mz coordinates
        return xr.DataArray(
            peak_profiles_dask,
            dims=("mz", "time"),
            coords={"mz": mzs, "time": scan_time},
            name="signal",
        )
