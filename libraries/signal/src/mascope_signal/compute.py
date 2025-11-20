import os
import json
import hashlib
from typing import Iterable, Literal
import asyncio

import dask.array as da
import numpy as np
import xarray as xr
import zarr

import mascope_file.name as m_name
import mascope_file.io as m_io
import mascope_thermo.thermo as m_thermo
import mascope_tofwerk.tofwerk as m_tofwerk
from mascope_tools.alignment.calibration import MassAligner, Spectra

from mascope_signal.runtime import runtime


# Peak alignment parameters
ALIGNMENT_MIN_INTENSITY = 0.0  # Minimum intensity for mass alignment
ALIGNMENT_WINDOW_FACTOR = 1.0  # Mass alignment window factor (times FWHM)
ALIGNMENT_MIN_FRACTION = 1.0  # Minimum fraction of scans for mass alignment


def get_scan_timestamps(
    base_filename: str,
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> np.ndarray:
    """
    Retrieve scan timestamps from a given file based on its type.

    :param base_filename: Sample file name.
    :type base_filename: str
    :param t_min: Minimum time [s], optional, defaults to None
    :type t_min: float
    :param t_max: Maximum time [s], optional, defaults to None
    :type t_max: float
    :return: An array of scan timestamps extracted from the sample file.
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = os.path.join(
                m_name.parse_path_from_item_filename(base_filename), "data.raw"
            )
            return m_thermo.get_scan_timestamps(datafile_path, t_min, t_max, polarity)
        case "tof_h5":
            datafile_path = os.path.join(
                m_name.parse_path_from_item_filename(base_filename), "data.h5"
            )
            return m_tofwerk.get_scan_timestamps(datafile_path, t_min, t_max)
        case "tof_zarr" | "orbi_zarr":
            signal_path = m_name.filename_to_zarr_path(base_filename, "signal")

            sync = m_io.get_zarr_synchronizer(signal_path)
            z = zarr.open(signal_path, mode="r", synchronizer=sync)
            time_array = z["time"][:]
            if not time_array.size:
                # Perhaps the coordinate is hiding in groups
                groups = list(z.group_keys())
                # Load time coordinate from each group and concatenate
                time_arrays = [z[group]["time"][:] for group in groups]
                time_array = np.concatenate(time_arrays)
                # Filter by time if t_min and/or t_max are provided
                # Using epsilon to avoid floating point precision issues
                epsilon = np.finfo(np.float64).eps * max(time_array)
                if t_min is not None:
                    time_array = time_array[time_array >= t_min - epsilon]
                if t_max is not None:
                    time_array = time_array[time_array <= t_max + epsilon]

            return time_array


def get_sum_signal(
    base_filename: str,
    t_min: float = None,
    t_max: float = None,
    polarity: Literal["+", "-"] | None = None,
    average: bool = False,
) -> xr.DataArray:
    """Get sum signal from the sample file for the given time range and polarity.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param t_min: Min time value [s], defaults to None
    :type t_min: float, optional
    :param t_max: Max time value [s], defaults to None
    :type t_max: float, optional
    :param polarity: Polarity of the scan to extract, defaults to None (compute all scans)
    :type polarity: str, optional
    :param average: Whether to return the average signal
    :type average: bool, optional
    :raises RuntimeError: If the sample file is not found or inaccessible
    :return: The sum signal as an xarray DataArray
    :rtype: xr.DataArray
    """

    cached_name = _get_sum_signal_hash_name(t_min, t_max, polarity)
    try:
        sum_signal = _get_cached_sum_signal(base_filename, cached_name)
        if average:
            time_coord = get_scan_timestamps(base_filename, t_min, t_max, polarity)
            averaging_factor = time_coord.size
            return sum_signal / averaging_factor
        return sum_signal
    except FileNotFoundError:
        # case where file doesn't exist in filestore
        runtime.logger.warning(f"Sample file not found: {base_filename}")
        raise RuntimeError(f"Sample file not found or inaccessible: {base_filename}")
    except (KeyError, AttributeError):
        # proceed if sample_file/dataset exists but is missing target sum_signal
        runtime.logger.debug(
            f"No cached sum signal found for {base_filename} with parameters: "
            f"t_min={t_min}, t_max={t_max}, polarity={polarity}, average={average} "
            f"Computing sum signal..."
        )

    sample_path = m_name.parse_path_from_item_filename(base_filename)
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = os.path.join(sample_path, "data.raw")
            sum_signal, averaging_factor = m_thermo.compute_sum_signal(
                datafile_path,
                t_min=t_min,
                t_max=t_max,
                polarity=polarity,
            )
        case "tof_h5":
            datafile_path = os.path.join(sample_path, "data.h5")
            sum_signal, averaging_factor = m_tofwerk.compute_sum_signal(
                datafile_path,
                t_min=t_min,
                t_max=t_max,
            )
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
            averaging_factor = time_data_points

    if cached_name != "sum_signal":
        # Check if calibration factor is available in the sample file properties
        props = m_io.read_props(base_filename)
        calibration = props["mz_calibration"]
        match sample_type:
            case "orbi_raw" | "orbi_zarr":
                if calibration:
                    fit_parameters = calibration["par"]
                    factor = fit_parameters["calibration_factor"]
                    sum_signal = sum_signal.assign_coords(
                        mz=sum_signal.mz.values * factor
                    )
            case "tof_h5" | "tof_zarr":
                if calibration:
                    full_sum_signal = get_sum_signal(base_filename)
                    full_sum_signal_mz = full_sum_signal.mz.values
                    if full_sum_signal_mz.size != sum_signal.mz.size:
                        # Reverse compatibility correction on m/z axis
                        # Leave only sum_signal.mz.size last values in full_sum_signal_mz
                        full_sum_signal_mz = full_sum_signal_mz[-sum_signal.mz.size :]
                    sum_signal = sum_signal.assign_coords(mz=full_sum_signal_mz)

    # Save the computed sum signal to the sample file for future use
    filename_sum_signal = m_name.filename_to_zarr_path(base_filename, cached_name)
    runtime.logger.warning(f"Saving computed sum signal to {filename_sum_signal}")
    try:
        sum_signal.to_zarr(filename_sum_signal)
    except FileNotFoundError as fe:
        if ".partial" in str(fe):
            raise Exception(
                f"The path is probably too long: {filename_sum_signal}"
            ) from fe
        else:
            raise

    if average:
        return sum_signal / averaging_factor

    return sum_signal


def _get_sum_signal_hash_name(t_min, t_max, polarity):
    """Generate a unique hash name for sum signal based on parameters"""
    is_full_sum_signal = t_min is None and t_max is None and polarity is None
    if is_full_sum_signal:
        cached_name = "sum_signal"
    else:
        key_str = json.dumps([t_min, t_max, polarity])
        hash_addition = hashlib.sha1(key_str.encode()).hexdigest()[:12]
        cached_name = f"sum_signal_{hash_addition}"

    return cached_name


def _get_cached_sum_signal(base_filename, cached_name):
    """Helper function to load cached sum signal from the sample file if it exists"""
    sample_file = m_io.load_file(base_filename, vars=[cached_name])
    sum_signal = sample_file.sum_signal
    return sum_signal


def load_signal(
    base_filename: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
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
    :param mz_max: Max m/z value, defaults to None
    :type mz_max: float, optional
    :param polarity: Polarity of the scan to extract, defaults to None (get all scans)
    :type polarity: str, optional
    :return: The signal with m/z and time coordinates
    :rtype: xr.Dataset
    """
    runtime.logger.debug(f"Loading signal from {base_filename}")

    sample_type = m_name.get_sample_file_type(base_filename)
    sample_path = m_name.parse_path_from_item_filename(base_filename)

    if not os.path.exists(sample_path):
        raise FileNotFoundError(sample_path)

    try:
        match sample_type:
            case "orbi_raw":
                datafile_path = os.path.join(sample_path, "data.raw")
                signal = m_thermo.get_signal(
                    datafile_path, t_min, t_max, mz_min, mz_max, polarity
                )
                # Handle m/z axis calibration
                props = m_io.read_props(base_filename)
                calibration = props["mz_calibration"]
                if calibration:
                    fit_parameters = calibration["par"]
                    factor = fit_parameters["calibration_factor"]
                    signal = signal.assign_coords(mz=signal.mz.values * factor)
                return signal
            case "tof_h5":
                datafile_path = os.path.join(sample_path, "data.h5")
                signal = m_tofwerk.get_signal(datafile_path, t_min, t_max)

                # Handle m/z axis calibration, sum_signal m/z values are calibrated
                sum_signal_mz = get_sum_signal(base_filename).mz.values
                mzs_are_equal = np.array_equal(signal.mz.values, sum_signal_mz)
                if not mzs_are_equal:
                    signal = signal.assign_coords(mz=sum_signal_mz)

                signal = signal.sel(mz=slice(mz_min, mz_max))
                return signal
            case "tof_zarr" | "orbi_zarr":
                signal_ds = m_io.load_array(base_filename, "signal")
                signal_ds = signal_ds.chunk(dict(mz=-1, time=-1))
                if sample_type == "tof_zarr":
                    # Correct by scan duration
                    interval_ds = m_io.load_array(base_filename, "signal_period")
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
                return signal_ds_sliced.chunk(dict(mz=-1))
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


def get_tic_per_scan(
    base_filename: str,
    timestamps: Iterable | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> tuple:
    """Get TIC per scan from the sample file depending on the file type

    :param base_filename: Sample file filename
    :type base_filename: str
    :param timestamps: Optional timestamps of the scans, defaults to None
    :type timestamps: Iterable | None
    :param polarity: Polarity of the scan to extract, defaults to None (get all scans)
    :type polarity: str | None
    :return: TIC time and TIC per scan as numpy arrays
    :rtype: tuple
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            tic_time, tic_per_scan = m_thermo.get_tic_per_scan(
                datafile_path, timestamps, polarity
            )
        case "tof_h5":
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            tic_time, tic_per_scan = m_tofwerk.get_tic_per_scan(
                datafile_path, timestamps
            )
        case "tof_zarr" | "orbi_zarr":
            zarr_path = m_name.filename_to_zarr_path(base_filename, "signal")
            sync = m_io.get_zarr_synchronizer(zarr_path)
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
                total_tic = m_io.read_props(base_filename)["tic"]
                tic_per_scan = tic_per_scan / tic_per_scan.sum() * total_tic
            except KeyError:
                runtime.logger.warning(
                    "Total TIC value is not available in the sample file"
                )

            # Get time coordinate as numpy array
            tic_time = m_io.load_coord(base_filename, "signal", "time")

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


async def get_orbi_centroids(
    base_filename: str,
    u_list: Iterable[float] | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> tuple:
    """
    Extract centroided peaks from an Orbitrap (Thermo .raw) file for specified m/z values and time range.

    This function determines the sample type and, if the sample file contains the Orbitrap raw file,
    extracts centroided peaks whose m/z values are within ±0.5 of any value in `u_list` and within the specified
    time range and polarity. Returns the filtered centroid m/z values, their intensities, and resolutions.

    :param base_filename: Sample file name (base, not full path).
    :type base_filename: str
    :param u_list: Iterable of m/z values to select centroid peaks near (within ±0.5), defaults to None.
    :type u_list: Iterable[float]
    :param t_min: Minimum time [s] for scan selection, optional, defaults to None (start of run).
    :type t_min: float | None, optional
    :param t_max: Maximum time [s] for scan selection, optional, defaults to None (end of run).
    :type t_max: float | None, optional
    :param polarity: Polarity of scans to use ('+' or '-'), optional, defaults to None (all polarities).
    :type polarity: Literal['+', '-'], optional
    :return: Tuple of (masses, intensities, resolutions, signal-to-noise) for centroid peaks
    matching the criteria.
    :rtype: tuple
    """
    sample_type = m_name.get_sample_file_type(base_filename)

    match sample_type:
        case "orbi_raw":
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            masses, intensities, resolutions, signal_to_noise = await asyncio.to_thread(
                m_thermo.get_centroids,
                datafile_path,
                u_list,
                t_min,
                t_max,
                polarity=polarity,
            )
            props = m_io.read_props(base_filename)
            calibration = props["mz_calibration"]
            if calibration:
                fit_parameters = calibration["par"]
                factor = fit_parameters["calibration_factor"]
                masses = masses * factor
            if u_list:
                # Create a mask for the masses that are within 0.5 of any value in u_list
                mz_mask = np.zeros_like(masses, dtype=bool)
                for mz in u_list:
                    mz_mask |= (masses >= mz - 0.5) & (masses <= mz + 0.5)
                masses = masses[mz_mask]
                intensities = intensities[mz_mask]
                resolutions = resolutions[mz_mask]
                signal_to_noise = signal_to_noise[mz_mask]
        case _:
            raise NotImplementedError(
                "Centroid extraction is only implemented for Orbitrap raw files."
            )
    return masses, intensities, resolutions, signal_to_noise


def get_orbi_centroids_per_scan(
    base_filename: str,
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> list:
    """
    Extract per-scan centroids from an Orbitrap raw file

    :param base_filename: Sample file name (base, not full path).
    :type base_filename: str
    :param t_min: Minimum time [s] for scan selection, optional, defaults to None (start of run).
    :type t_min: float | None, optional
    :param t_max: Maximum time [s] for scan selection, optional, defaults to None (end of run).
    :type t_max: float | None, optional
    :param polarity: Polarity of scans to use ('+' or '-'), optional, defaults to None (all polarities).
    :type polarity: Literal['+', '-'], optional
    :return: List of dictionaries with per-scan centroid data, each containing
            centroid masses, intensities, resolutions, signal-to-noise ratios, and timestamps.
    :rtype: list
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            centroids_per_scan = m_thermo.get_centroids_per_scan(
                datafile_path, t_min, t_max, polarity=polarity
            )
            props = m_io.read_props(base_filename)
            calibration = props["mz_calibration"]
            if calibration:
                fit_parameters = calibration["par"]
                factor = fit_parameters["calibration_factor"]
                for scan_centroids in centroids_per_scan:
                    scan_centroids["masses"] = scan_centroids["masses"] * factor

            return centroids_per_scan
        case _:
            raise NotImplementedError(
                "Per-scan centroid extraction is only for Orbitrap raw files."
            )


async def load_peak_timeseries(
    base_filename: str,
    mzs: Iterable[float],
) -> xr.Dataset:
    """Loads peak timeseries from the sample file.
    Computes missing peak timeseries if needed.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param mzs: List of target m/z values
    :type mzs: Iterable[float]
    :return: The peak timeseries dataset
    :rtype: xr.Dataset
    """
    # --- Load existing peak timeseries from the sample file ---
    mzs = np.unique(mzs)
    peak_timeseries = m_io.load_peak_data(base_filename).sel(mz=mzs, method="nearest")
    # Remove duplicate m/z values if any
    _, unique_idx = np.unique(peak_timeseries.mz.values, return_index=True)
    peak_timeseries = peak_timeseries.isel(mz=np.sort(unique_idx))

    runtime.logger.debug(
        f"Loading peak timeseries for {peak_timeseries.mz.size} m/z values from {base_filename}"
    )
    to_compute_mask = np.invert(peak_timeseries.is_timeseries_computed.values)
    if not np.any(to_compute_mask):
        runtime.logger.debug(
            f"All peak timeseries are cached in {base_filename}, loading from file."
        )
        return peak_timeseries

    # --- Compute missing peak timeseries ---
    mz_coords = peak_timeseries.mz.values
    mzs_to_compute = mz_coords[to_compute_mask]
    new_peak_timeseries = await get_peak_timeseries(base_filename, mzs_to_compute)

    sum_peak_heights = peak_timeseries.sum_peak_heights.sel(mz=mzs_to_compute).values
    sum_peak_areas = peak_timeseries.sum_peak_areas.sel(mz=mzs_to_compute).values

    # Normalize peak timeseries intensities to 1
    new_peak_timeseries_norm = new_peak_timeseries / new_peak_timeseries.sum(dim="time")
    new_peak_timeseries_norm = new_peak_timeseries_norm.values

    # Restore peak timeseries intensities using fitted peak areas and heights
    new_peak_timeseries_area = new_peak_timeseries_norm * sum_peak_areas[:, np.newaxis]
    new_peak_timeseries_height = (
        new_peak_timeseries_norm * sum_peak_heights[:, np.newaxis]
    )

    # Insert/merge computed timeseries into the cached peak_timeseries dataset
    try:
        # Assign peak_areas and peak_heights for the computed mzs
        peak_timeseries["peak_areas"].loc[dict(mz=mzs_to_compute)] = (
            new_peak_timeseries_area
        )
        peak_timeseries["peak_heights"].loc[dict(mz=mzs_to_compute)] = (
            new_peak_timeseries_height
        )
        # Mark timeseries as computed
        peak_timeseries["is_timeseries_computed"].loc[dict(mz=mzs_to_compute)] = True

    except Exception as e:
        runtime.logger.error(f"Failed to merge computed peak timeseries: {e}")
        raise

    # --- Store new peak timeseries in the sample file ---
    await m_io.write_peaks(peak_timeseries, base_filename)

    return peak_timeseries


async def get_peak_timeseries(
    base_filename: str,
    mzs: Iterable[float],
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> xr.DataArray:
    """Get peak timeseries for given peak m/z values in the time range [t_min, t_max]

    :param base_filename: Sample file filename
    :type base_filename: str
    :param mzs: List of target m/z values
    :type mzs: Iterable[float]
    :param t_min: Left border of the time range [s], defaults to None
    :type t_min: float, optional
    :param t_max: Right border of the time range [s], defaults to None
    :type t_max: float, optional
    :param polarity: Polarity of the scan to extract, defaults to None (get all scans)
    :type polarity: str, optional
    :return: peak timeseries for the given m/z values
    :rtype: xr.DataArray
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = m_name.filename_to_datafile_path(base_filename)

            # Orbitrap raw files store raw data, mzs need to be uncalibrated
            # before extracting peak timeseries
            props = m_io.read_props(base_filename)
            calibration = props["mz_calibration"]
            factor = 1.0
            if calibration:
                fit_parameters = calibration["par"]
                factor = fit_parameters["calibration_factor"]
            uncalibrated_mzs = np.array(mzs) / factor
            peak_timeseries = await asyncio.to_thread(
                m_thermo.get_peak_timeseries,
                datafile_path,
                uncalibrated_mzs,
                t_min,
                t_max,
                polarity,
            )
            # Calibrate m/z coordinate
            return peak_timeseries.assign_coords(mz=peak_timeseries.mz.values * factor)
        case "tof_h5":
            # Get calibrated m/z values
            sum_signal_mz = get_sum_signal(base_filename).mz.values
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            return await asyncio.to_thread(
                m_tofwerk.get_peak_timeseries,
                datafile_path,
                mzs,
                sum_signal_mz,
                t_min,
                t_max,
            )
        case "tof_zarr" | "orbi_zarr":
            signal = load_signal(base_filename, t_min, t_max)
            # Interpolate missing values in mz dimension using linear method.
            signal = signal.interpolate_na(dim="mz", method="linear")
            # Fill the remaining nan values with zeros
            signal = signal.fillna(0)
            # Extract the peak timeseries for the closest m/z values
            return signal.sel(mz=mzs, method="nearest").signal


def get_polarity_options(base_filename: str) -> str:
    """Reads the polarities present in a sample file.

    :param base_filename: Sample file filename
    :type base_filename: str
    :return: Polarity options as "-", "+", or "+-" depending on the data.
    :rtype: str
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    datafile_path = m_name.parse_path_from_item_filename(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = os.path.join(datafile_path, "data.raw")
            return m_thermo.get_polarity_options(datafile_path)
        case "tof_h5":
            datafile_path = os.path.join(datafile_path, "data.h5")
            return m_tofwerk.get_polarity_options(datafile_path)
        case "tof_zarr" | "orbi_zarr":
            polarity = base_filename.split("_")[-1]
            if polarity in ["+", "-"]:
                return polarity
            else:
                # If polarity is not specified, return None (get all scans)
                return None


def get_metadata(
    base_filename: str,
) -> m_thermo.RawFileMetadata | None:
    """Get metadata from the sample file

    :param base_filename: Sample file filename
    :type base_filename: str
    :return: Metadata class instance or None if the file type is not supported
    :rtype: RawFileMetadata | None
    """
    sample_type = m_name.get_sample_file_type(base_filename)
    match sample_type:
        case "orbi_raw":
            datafile_path = m_name.filename_to_datafile_path(base_filename)
            return m_thermo.RawFileMetadata(datafile_path)
        case "tof_h5":
            raise NotImplementedError(
                "Metadata retrieval for h5 files is not implemented"
            )
        case "tof_zarr" | "orbi_zarr":
            raise NotImplementedError(
                "Metadata retrieval for zarr files is not implemented"
            )


def sum_peak_collection(
    peak_collection: Spectra,
) -> tuple[Spectra, float, float]:
    """Aligns and sums provided collection of peak arrays.

    :param peak_collection: Peak collection to align and sum
    :type peak_collection: Spectra
    :raises ValueError: If mass alignment fails
    :return: Tuple of summed aligned peaks, min aligned m/z, max aligned m/z
    :rtype: tuple[Spectra, float, float]
    """
    # Perform alignment using virtual lock mass algorithm
    vlm_corrector = MassAligner(
        min_peak_intensity=ALIGNMENT_MIN_INTENSITY,
        min_fraction=ALIGNMENT_MIN_FRACTION,
        window_factor=ALIGNMENT_WINDOW_FACTOR,
    )
    vlm_corrector.fit(peak_collection)
    aligned_peaks = vlm_corrector.transform(peak_collection)
    if vlm_corrector.points_mz.size < 2:
        raise ValueError(
            "Mass alignment failed: fewer than 2 alignment points found. "
            "Check your filtering parameters and input data quality."
        )

    # Min and max aligned m/z
    vlm_min_mz = vlm_corrector.points_mz.min()
    vlm_max_mz = vlm_corrector.points_mz.max()

    aligned_peak_sum = aligned_peaks.compute_sum_spectrum(
        window_factor=ALIGNMENT_WINDOW_FACTOR, average=True
    )

    return aligned_peak_sum, vlm_min_mz, vlm_max_mz
