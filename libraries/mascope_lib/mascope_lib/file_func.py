import fnmatch
import json
import os
import glob
import sys
from shutil import rmtree
from typing import Iterable, Literal
import dask.array as da
import numpy as np
import xarray as xr
import zarr
from pythonnet import load

load("coreclr")
import clr
import mascope_hardware

sys.path.append(os.path.join(mascope_hardware.__path__[0], "./orbitrap/lib/dlls"))

clr.AddReference("ThermoFisher.CommonCore.RawFileReader")
clr.AddReference("ThermoFisher.CommonCore.Data")

from mascope_lib.runtime import lib_runtime
from mascope_hardware.orbitrap import thermo
from mascope_hardware.tofwerk import tofwerk

from .util import parse_path_from_item_filename
from .instrument import resolve_instrument_type


def get_filestore_path() -> str:
    """Return path to the filestore

    In `prod` mode, return the path inside the container, otherwise return the
    path specified in the config `meta.filestore`

    :return: Filestore path
    :rtype: str
    """
    base_path = (
        "/app/runtime/env/prod/filestore"
        if lib_runtime.mode == "prod"
        else lib_runtime.meta.filestore
    )
    return base_path


def get_zarr_synchronizer(zarr_path: str) -> zarr.ProcessSynchronizer:
    """Get zarr synchronizer for a given zarr file

    :param zarr_path: Path to the zarr file
    :type zarr_path: str
    :return: Zarr synchronizer
    :rtype: zarr.ProcessSynchronizer
    """
    parent_dir = os.path.dirname(zarr_path)
    sync_name = zarr_path.split(os.path.sep)[-1].replace(".zarr", ".sync")
    sync_path = os.path.sep.join([parent_dir, sync_name])
    return zarr.ProcessSynchronizer(sync_path)


def write_peaks(
    peak_areas: xr.DataArray,
    peak_heights: xr.DataArray,
    filename: str,
    overwrite: bool = False,
) -> None:
    """Write fitted peak areas and peak heights to zarr files

    :param peak_areas: Data array with peak areas
    :type peak_areas: xr.DataArray
    :param peak_heights: Data array with peak heights
    :type peak_heights: xr.DataArray
    :param filename: Sample file name
    :type filename: str
    :param overwrite: Flag to overwrite peaks if they already exist, defaults to False
    :type overwrite: bool, optional
    :raises FileExistsError: Peak areas or peak heights already exist for the sample file
    :return: None
    """
    # Get paths to peak_areas and peak_heights zarr files
    filename_peak_areas = filename_to_zarr_path(filename, "peak_areas")
    filename_peak_heights = filename_to_zarr_path(filename, "peak_heights")

    # Check if paths exist
    if os.path.exists(filename_peak_areas) or os.path.exists(filename_peak_heights):
        if overwrite:
            rmtree(filename_peak_areas)
            rmtree(filename_peak_heights)
        else:
            raise FileExistsError(
                f"Peak areas or peak heights already exist for {filename}"
            )

    # Set names for peak areas and peak heights
    peak_areas.name = "peak_areas"
    peak_heights.name = "peak_heights"

    # Write peak areas and peak heights to zarr files
    peak_areas.to_zarr(filename_peak_areas)
    peak_heights.to_zarr(filename_peak_heights)


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
        # Write sum signal to zarr file
        sum_signal.to_zarr(filename_sum_signal)

    if average:
        return sum_signal / sample_file.props["length"]
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
    base_path = get_filestore_path()
    sample_path = parse_path_from_item_filename(base_filename, base_path)

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


def filename_to_zarr_path(base_filename, variable):
    """Derive full path to a zarr data array from sample filename and the desired variable

    :param base_filename: Sample file filename
    :type base_filename: str
    :param variable: Variable name inside the sample file
    :type variable: str
    :return: Full path
    :rtype: str
    """
    base_path = get_filestore_path()
    sample_data_path = parse_path_from_item_filename(base_filename, base_path)
    zarr_filename = variable + os.extsep + "zarr"
    return os.path.join(sample_data_path, zarr_filename)


def filename_to_datafile_path(base_filename):
    """Derive full path to a h5 or raw data file from sample filename

    :param base_filename: Sample file filename
    :type base_filename: str
    :return: Full path
    :rtype: str
    """
    # Get path to the sample file folder
    base_path = get_filestore_path()
    sample_data_path = parse_path_from_item_filename(base_filename, base_path)

    sample_file_type = get_sample_file_type(base_filename)

    # Get path to the datafile and verify if it exists
    match sample_file_type:
        case "tof_h5":
            return os.path.join(sample_data_path, "data.h5")
        case "orbi_raw":
            return os.path.join(sample_data_path, "data.raw")
        case "tof_zarr" | "orbi_zarr":
            FileNotFoundError(
                f"Sample file {sample_data_path} does not contain h5 or raw datafile"
            )


def get_file_data_vars(filepath):
    """Get list of available variables in a sample file

    :param filepath: Full path to the sample file
    :type filepath: str
    :return: List of available variables
    :rtype: list
    """
    file_dirs = next(os.walk(filepath))[1]
    zarrs = []
    for var in fnmatch.filter(file_dirs, "*.zarr"):
        zarrs.append(var.strip(".zarr"))
    return zarrs


def get_instrument_name(filename: str) -> str:
    """Get instrument name from sample file

    Currently, the sample file name is assumed to begin with the instrument name,
    followed by an underscore.

    :param filename: Sample file name
    :type filename: str
    :return: Instrument name
    :rtype: str
    """
    instrument_name = filename.split("_")[0]
    return instrument_name


def get_instrument_type(filename: str) -> str:
    """Get instrument type (one of {"orbi", "tof"}) from sample file

    :param filename: Sample file name
    :type filename: str
    :raises ValueError: Failed to detect instrument type
    :return: Instrument type, one of {"orbi", "tof"}
    :rtype: str
    """
    instrument_name = get_instrument_name(filename)
    return resolve_instrument_type(instrument_name)


def get_sample_file_type(filename: str) -> str:
    """Get sample file type based on the presence of a datafile
    in sample_data_path.
        *_h5 - h5 file is available
        *_raw - raw file is available
        *_zarr - no source data file.

    :param filename: Sample file name
    :type filename: str
    :return: Sample file type, one of [tof_h5, tof_zarr, orbi_raw, orbi_zarr]
    :rtype: str
    """
    base_path = get_filestore_path()
    sample_data_path = parse_path_from_item_filename(filename, base_path)
    instrument_type = get_instrument_type(filename)

    is_raw = os.path.isfile(os.path.join(sample_data_path, "data.raw"))
    is_h5 = os.path.isfile(os.path.join(sample_data_path, "data.h5"))

    match instrument_type:
        case "tof":
            return "tof_h5" if is_h5 else "tof_zarr"
        case "orbi":
            return "orbi_raw" if is_raw else "orbi_zarr"


def load_array(base_filename, var, prev_array=None):
    """Load a stored mfzarr variable from file into a xr.Dataset object.
       If the variable receives another chunk of mfzarr data, then subsequent
       load_array calls with non-empty prev_array will update
       previously created dataset from the updated variable.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param var: Sample file variable name
    :type var: str
    :param prev_array: Previously loaded array to update with the updated var, defaults to None
    :type prev_array: xr.DataArray, optional
    :raises FileNotFoundError: No such sample file or variable in it.
    :return: Loaded sample file object
    :rtype: xr.Dataset
    """
    lib_runtime.logger.debug(f"Loading array {base_filename} : {var}")
    var_path = filename_to_zarr_path(base_filename, var)

    if not os.path.exists(var_path):
        if var == "signal":
            lib_runtime.logger.error("Use load_signal to access signal array")
        raise FileNotFoundError(var_path)

    # Load data from file
    def is_multifile():
        z = zarr.open(var_path, mode="r", synchronizer=sync)
        groups = list(z.group_keys())
        return bool(len(groups))

    sync = get_zarr_synchronizer(var_path)
    if is_multifile():
        # Multi-file (grouped)
        dataset = open_mfzarr(var_path, prev_array=prev_array, sync=sync)
    else:
        # Single file
        dataset = xr.open_zarr(var_path, synchronizer=sync)

    return dataset


def load_coord(base_filename, var, coord_name):
    """Load coordinate array of a sample file

    :param base_filename: Sample file filename
    :type base_filename: str
    :param var: Sample file variable name
    :type var: str
    :param coord_name: Coordinate axis name
    :type coord_name: str
    :return: Requested coordinate array
    :rtype: np.array
    """
    var_path = filename_to_zarr_path(base_filename, var)

    if not os.path.exists(var_path):
        if var == "signal":
            lib_runtime.logger.error("Use load_signal to access signal array")
        raise FileNotFoundError(var_path)

    sync = get_zarr_synchronizer(var_path)
    z = zarr.open(var_path, mode="r", synchronizer=sync)
    coord = z[coord_name]
    coord_array = coord[:]
    # Check if array is empty
    if not coord_array.size:
        # Perhaps the coordinate is hiding in groups
        # Get list of groups
        groups = list(z.group_keys())

        # Load time coordinate from each group and concatenate
        coord_arrays = [z[group][coord_name][:] for group in groups]
        coord_array = np.concatenate(coord_arrays)

    return coord_array


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
    lib_runtime.logger.debug(f"Loading signal from {base_filename}")

    sample_type = get_sample_file_type(base_filename)
    base_path = get_filestore_path()
    sample_path = parse_path_from_item_filename(base_filename, base_path)

    if not os.path.exists(sample_path):
        raise FileNotFoundError(sample_path)

    try:
        match sample_type:
            case "tof_zarr" | "orbi_zarr":
                signal_ds = load_array(base_filename, "signal")

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
        lib_runtime.logger.error(f"Error loading signal from {base_filename}: {e})")
        # Return empty signal dataset with "mz" and "time" coordinates in case of error
        return xr.Dataset(
            {
                "signal": (["mz", "time"], np.zeros((0, 0))),
                "mz": (["mz"], np.zeros(0)),
                "time": (["time"], np.zeros(0)),
            }
        )


def load_file(base_filename, vars=None, prev_dataset=None):
    """Load stored mfzarr variables into an xr.Dataset object.
       If the variables receive another chunk of data, then subsequent
       load_file calls with non-empty prev_dataset will update
       previously created dataset from updated variables.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param vars: List of variable (zarr array) names to load, defaults to None. If None, all variables are loaded.
    :type vars: list, optional
    :param prev_dataset: Previously loaded dataset to update with updated vars, defaults to None.
    :type prev_dataset: xr.Dataset, optional
    :raises FileNotFoundError: No such sample file
    :return: Loaded sample file object
    :rtype: xr.Dataset
    """

    base_path = get_filestore_path()
    filepath = parse_path_from_item_filename(base_filename, base_path)
    if not os.path.exists(filepath):
        lib_runtime.logger.warning(f"File not found: {filepath}")
        raise FileNotFoundError(filepath)
    if vars is None:
        # Get all saved variable names
        zarrs = get_file_data_vars(filepath)
        vars = [zarr.strip(".zarr") for zarr in zarrs]
    if "signal" in vars:
        lib_runtime.logger.error(
            "Loading signal with load_file is depricated. Use load_signal instead."
        )
        vars.pop(vars.index("signal"))
    # Load arrays from mfzarrs
    lib_runtime.logger.info(f"Loading {', '.join(vars)} from {base_filename}")
    datasets = []
    zarr_groups = {}
    # Load requested data arrays
    for var in vars:
        prev_item = None if prev_dataset is None else prev_dataset.get(var)
        if prev_item is not None:
            prev_item.attrs["zarr_groups"] = prev_dataset.attrs.get(
                "zarr_groups", {}
            ).get(var, [])
        try:
            var_dataset = load_array(base_filename, var, prev_item)
        except FileNotFoundError:
            lib_runtime.logger.warning(
                f"[load_file] {var} not found for {base_filename}:"
            )
            continue
        datasets.append(var_dataset)
        zarr_groups[var] = var_dataset.attrs.get("zarr_groups", [])
    # Add previously loaded arrays
    if prev_dataset is not None:
        for prev_var, prev_var_dataset in prev_dataset.data_vars.items():
            if prev_var not in vars:
                datasets.append(prev_var_dataset)
    # Merge datasets per variable into one dataset
    dataset = xr.merge(datasets)
    # Load properties
    prop_path = os.path.join(filepath, ".props")
    with open(prop_path, "r") as f:
        props = json.load(f)
    # Attach to dataset
    dataset.attrs["props"] = props
    dataset.attrs["zarr_groups"] = zarr_groups
    return dataset


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
                lib_runtime.logger.warning(
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


def open_mfzarr(path, sync=None, mode="r", concat_dim="time", prev_array=None):
    """Load data from a multi-file zarr into a xr.Dataset

    :param path: Full path to the multi-file zarr array
    :type path: str
    :param sync: Zarr file synchronizer, defaults to None
    :type sync: zarr.ProcessSynchronizer, optional
    :param mode: File mode, defaults to "r"
    :type mode: str, optional
    :param concat_dim: Dimension name along which to concatenate the files, defaults to "time"
    :type concat_dim: str, optional
    :param prev_array: Previously loaded array to update with new mfzarr data chunk, defaults to None
    :type prev_array: xr.DataArray, optional
    :return: Concatenated data
    :rtype: xr.Dataset
    """

    z = zarr.open(path, mode=mode, synchronizer=sync)
    groups = list(z.group_keys())

    if prev_array is not None:
        prev_groups = prev_array.attrs.get("zarr_groups", [])
        for g in prev_groups:
            lib_runtime.logger.debug(f"group {g} already loaded")
            groups.remove(g)
    if not groups:
        lib_runtime.logger.debug("no new groups")
        return prev_array
    lib_runtime.logger.debug(f"loading groups: {groups}")
    x = xr.concat(
        [xr.open_zarr(path, g, consolidated=False, synchronizer=sync) for g in groups],
        concat_dim,
    )
    if prev_array is not None:
        x = xr.concat([prev_array.to_dataset(), x], concat_dim)
    x.attrs = z.attrs.asdict()
    x.attrs["zarr_groups"] = groups
    return x


def update_props(base_filename, props_to_update):
    """Update sample file properties and write to file. Properties given are updated, rest (if any) remain as is.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param props_to_update: Properties to update,
    :type props_to_update: dict
    """
    base_path = get_filestore_path()
    sample_data_path = parse_path_from_item_filename(base_filename, base_path)
    # Update properties
    prop_path = os.path.join(sample_data_path, ".props")
    with open(prop_path, "r") as f:
        props = json.load(f)
    props.update(props_to_update)
    with open(prop_path, "w") as f:
        json.dump(props, f, indent=4)


def write_props(base_filename, props):
    """Write properties into sample file.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param props: Properties to write
    :type props: dict
    """
    base_path = get_filestore_path()
    sample_data_path = parse_path_from_item_filename(base_filename, base_path)
    # Write properties
    prop_path = os.path.join(sample_data_path, ".props")
    with open(prop_path, "w") as f:
        json.dump(props, f, indent=4)


def update_zarr_array_coord(base_filename, var, dim, coord):
    """Update coordinates of a zarr array

    :param base_filename: Sample file filename
    :type base_filename: str
    :param var: Sample file variable name
    :type var: str
    :param dim: Name of the coordinate dimension
    :type dim: str
    :param coord: New coordinate array
    :type coord: np.array
    """
    array_path = filename_to_zarr_path(base_filename, var)
    sync = get_zarr_synchronizer(array_path)
    zarr_array = zarr.open(array_path, mode="a", synchronizer=sync)
    zarr_array[dim][:] = coord
    for group_name, group in zarr_array.groups():
        group[dim][:] = coord


def delete_peaks(base_filename: str):
    """Delete sample file peaks.

    :param base_filename: Sample file filename
    :type base_filename: str
    """
    base_path = get_filestore_path()
    sample_data_path = parse_path_from_item_filename(base_filename, base_path)
    peak_dirs = glob.glob(os.path.join(sample_data_path, "peak_*"))
    for dir in peak_dirs:
        rmtree(dir)
