import fnmatch
import json
import os
import glob
import sys
from ctypes import ArgumentError
from datetime import datetime, timezone
from shutil import rmtree
from typing import Iterable, Optional
import dask.array as da
import numpy as np
import xarray
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


from .structs import ExtendableDataArray
from .util import parse_path_from_item_filename
from .instrument import resolve_instrument_type


class zarr_sdk:
    @staticmethod
    def finalize_signal_dataset(data, sample_file):
        filename = data["filename"]
        try:
            final_length = float(
                sample_file["signal"].time[-1] + sample_file["signal_period"][-1]
            )
        except Exception as e:
            lib_runtime.logger.error(
                f"""
                [finalize_signal_dataset] Warning: {e.__class__.__name__}({str(e)})
            """
            )
            final_length = sample_file["props"]["length"]

        # Update properties
        final_length = min(final_length, sample_file["props"]["length"])
        sample_file["props"].update(
            {
                "committed_length": final_length,
                "length": final_length,
                "tic": data["tic"],
            }
        )
        # Write properties
        update_props(filename, sample_file["props"])
        # flush arrays
        arrays = [sample_file["signal"], sample_file["signal_period"]]
        for a in arrays:
            if isinstance(a, ExtendableDataArray):
                a.flush()
        # write sum signal array
        zarr_sdk.write_sum_signal_dataset(sample_file)

    @staticmethod
    def init_centroid_dataset(data, item):
        filename = filename_to_zarr_path(data["filename"], "centroids")
        centroid_array = ExtendableDataArray(path=filename, array_module=da)
        centroid_array.init_array(
            dims=("mz", "time"), coords=[[], []], name="centroids"
        )
        item.update({"centroids": centroid_array})

    @staticmethod
    def init_signal_dataset(data, overwrite=False):
        # First filesystem operation in acquisition api sequence:
        #   init_signal_dataset - init_tps_dataset - init_viz_dataset -
        #   update_signal_dataset - update_tps_dataset
        #   - finalize_signal_dataset
        # Returns acquisition item shared through the acquisiiton api
        base_path = get_filestore_path()
        filename = data.get("filename")
        mz = np.frombuffer(data["mz"], dtype=np.float32)
        single_ion_signal = data.get("single_ion_signal")
        t_range = data["t_range"]
        mz_calibration = data.get("mz_calibration")
        polarity = data.get("polarity")
        sample_interval = data.get("sample_interval")
        method_file = data.get("method_file")

        try:
            data_path = parse_path_from_item_filename(filename, base_path)
        except Exception as e:
            raise NameError(f"Error parsing filename: {e}") from e
        if os.path.exists(data_path):
            if overwrite:
                rmtree(data_path)
            else:
                raise FileExistsError(data_path)
        filename_signal = filename_to_zarr_path(filename, "signal")
        signal_array = ExtendableDataArray(path=filename_signal, array_module=da)
        signal_array.init_array(dims=("mz", "time"), coords=[mz, []], name="signal")
        filename_period = filename_to_zarr_path(filename, "signal_period")
        period_array = ExtendableDataArray(path=filename_period, array_module=np)
        period_array.init_array(dims=("time"), coords=[[]], name="signal_period")
        t = datetime.now()
        utc_offset = (t - t.astimezone(timezone.utc).replace(tzinfo=None)).seconds
        properties = {
            "filename": filename,
            "length": float(t_range[1]),
            "committed_length": 0.0,
            "range": [float(mz[0]), float(mz[-1])],
            "mz_calibration": mz_calibration,
            "single_ion_signal": single_ion_signal,
            "polarity": polarity,
            "sample_interval": sample_interval,
            "utc_offset": utc_offset,
            "method_file": method_file,
        }
        write_props(filename, properties)

        return {
            "signal": signal_array,
            "signal_period": period_array,
            "props": properties,
        }

    @staticmethod
    def update_signal_dataset(data, item):
        base_path = get_filestore_path()
        ti = np.array([data["t"]], dtype=np.float32)
        period = np.array([data["period"]], dtype=np.float32)
        lib_runtime.logger.debug(ti.item())
        spec = np.frombuffer(data["spec"], dtype=np.float32)
        spec = spec.reshape(-1, 1)
        if "mz" in data:
            # mz coordinates provided with data (Orbitrap)
            mz = np.frombuffer(data["mz"], dtype=np.float32)
            mz = mz.reshape(
                -1,
            )
        else:
            # Use mz coordinates from signal_array (TOF)
            mz = item["signal"]["mz"]
        # Extend data arrays (write to file)
        item["signal"].extend_array(spec, [mz, ti], "time")
        item["signal_period"].extend_array(period, [ti], "time")
        # Update committed_length in .props, when new chunk is committed
        if item["signal"].delayed_write is None:
            committed_length = float(
                item["signal"].time[-1] + item["signal_period"][-1]
            )
            item["props"].update({"committed_length": committed_length})
            prop_path = os.path.join(
                parse_path_from_item_filename(data["filename"], base_path), ".props"
            )
            with open(prop_path, "w") as f:
                json.dump(item["props"], f, indent=4)


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


def write_peaks(
    peak_areas: xarray.DataArray,
    peak_heights: xarray.DataArray,
    filename: str,
    overwrite: bool = False,
) -> None:
    """Write fitted peak areas and peak heights to zarr files

    :param peak_areas: Data array with peak areas
    :type peak_areas: xarray.DataArray
    :param peak_heights: Data array with peak heights
    :type peak_heights: xarray.DataArray
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


def get_sum_signal(filename: str, average: bool = False) -> xarray.DataArray:
    """Calculates the sum spectrum of a given filename

    :param filename: Name of the target file
    :type filename: str
    :param average: Return avereage spectrum instead of sum. By default false (return sum).
    :type average: bool
    :return: Sum/average spectrum
    :rtype: xarray.core.dataarray.DataArray
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
) -> xarray.DataArray:
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
    :rtype: xarray.core.dataarray.DataArray
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

            # Convert sum signal to dask array
            sum_signal_dask = da.from_array(
                signal_slice.sum(dim="time").signal.values, chunks="auto"
            )

            # Convert to xarray.DataArray
            sum_signal = xarray.DataArray(
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


def remove_duplicate_mz_values(mz):
    # Sometimes TOF signal mz coordinate contains multiple zeros at the beginning
    # This may cause duplicate coordinate value error in some functions
    # This function fixes the coordinate vector by setting arbitrary small values for
    # the zero coordinates
    mz_unique = mz
    mz_below_10_mask = mz < 10
    if (np.diff(mz[mz_below_10_mask]) == 0).any():
        mz_below_10_maxi = mz_below_10_mask.sum()
        mz_unique[mz_below_10_mask] = np.linspace(
            0, mz[mz_below_10_maxi], mz_below_10_maxi, endpoint=False
        )
    return mz_unique


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


def get_sample_file_type(filename: str) -> Optional[str]:
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


def get_zarr_var_shape(base_filename, var, concat_dim=1):
    """Get the shape of a sample file variable

    :param base_filename: Sample file filename
    :type base_filename: str
    :param var: Variable name
    :type var: str
    :param concat_dim: Concatenation dimension of groups of the variable, defaults to 1
    :type concat_dim: int, optional
    :raises FileNotFoundError: No such sample file or variable
    :raises ArgumentError: Illegal concat_dim
    :return: Shape of the variable
    :rtype: tuple
    """
    path = filename_to_zarr_path(base_filename, var)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Zarr file {path} does not exist")
    sync = ExtendableDataArray.get_zarr_synchronizer(path)
    z = zarr.open(path, mode="r", synchronizer=sync)
    group_shapes = [g[1][var].shape for g in z.groups()]
    dim0, dim1 = zip(*group_shapes)
    if concat_dim == 0:
        shape = (sum(dim0), max(dim1))
    elif concat_dim == 1:
        shape = (max(dim0), sum(dim1))
    else:
        raise ArgumentError(
            """
            Error in 'get_zarr_var_shape()', 'concat_dim' must be 0 or 1
        """
        )
    return shape


def load_array(base_filename, var, prev_array=None):
    """Load a stored mfzarr variable from file into a xarray.Dataset object.
       If the variable receives another chunk of mfzarr data, then subsequent
       load_array calls with non-empty prev_array will update
       previously created dataset from the updated variable.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param var: Sample file variable name
    :type var: str
    :param prev_array: Previously loaded array to update with the updated var, defaults to None
    :type prev_array: xarray.DataArray, optional
    :raises FileNotFoundError: No such sample file or variable in it.
    :return: Loaded sample file object
    :rtype: xarray.Dataset
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

    sync = ExtendableDataArray.get_zarr_synchronizer(var_path)
    if is_multifile():
        # Multi-file (grouped)
        dataset = open_mfzarr(var_path, prev_array=prev_array, sync=sync)
    else:
        # Single file
        dataset = open_zarr(var_path, sync=sync)

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

    sync = ExtendableDataArray.get_zarr_synchronizer(var_path)
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
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    mz_min: Optional[float] = None,
    mz_max: Optional[float] = None,
) -> xarray.Dataset:
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
    :rtype: xarray.Dataset
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
        return xarray.Dataset(
            {
                "signal": (["mz", "time"], np.zeros((0, 0))),
                "mz": (["mz"], np.zeros(0)),
                "time": (["time"], np.zeros(0)),
            }
        )


def load_file(base_filename, vars=None, prev_dataset=None):
    """Load stored mfzarr variables into an xarray.Dataset object.
       If the variables receive another chunk of data, then subsequent
       load_file calls with non-empty prev_dataset will update
       previously created dataset from updated variables.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param vars: List of variable (zarr array) names to load, defaults to None. If None, all variables are loaded.
    :type vars: list, optional
    :param prev_dataset: Previously loaded dataset to update with updated vars, defaults to None.
    :type prev_dataset: xarray.Dataset, optional
    :raises FileNotFoundError: No such sample file
    :return: Loaded sample file object
    :rtype: xarray.Dataset
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
    dataset = xarray.merge(datasets)
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
            sync = ExtendableDataArray.get_zarr_synchronizer(zarr_path)
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
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    polarity: Optional[str] = None,
) -> xarray.DataArray:
    """Get peak profiles for given m/z values in the time range [t_min, t_max]

    :param datafile_path: Path to the data file
    :type datafile_path: str
    :param mzs: List of target m/z values
    :type mzs: Iterable[float]
    :param t_min: Left border of the time range [s], defaults to None
    :type t_min: Optional[float], optional
    :param t_max: Right border of the time range [s], defaults to None
    :type t_max: Optional[float], optional
    :param polarity: Polarity of the scan to extract, defaults to None (get all scans)
    :type polarity: Optional[str], optional
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
    """Load data from a multi-file zarr into a xarray.Dataset

    :param path: Full path to the multi-file zarr array
    :type path: str
    :param sync: Zarr file synchronizer, defaults to None
    :type sync: zarr.ProcessSynchronizer, optional
    :param mode: File mode, defaults to "r"
    :type mode: str, optional
    :param concat_dim: Dimension name along which to concatenate the files, defaults to "time"
    :type concat_dim: str, optional
    :param prev_array: Previously loaded array to update with new mfzarr data chunk, defaults to None
    :type prev_array: xarray.DataArray, optional
    :return: Concatenated data
    :rtype: xarray.Dataset
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
    x = xarray.concat(
        [
            xarray.open_zarr(path, g, consolidated=False, synchronizer=sync)
            for g in groups
        ],
        concat_dim,
    )
    if prev_array is not None:
        x = xarray.concat([prev_array.to_dataset(), x], concat_dim)
    x.attrs = z.attrs.asdict()
    x.attrs["zarr_groups"] = groups
    return x


def open_zarr(path, sync=None):
    """Open zarr array

    :param path: str
    :type path: Path to the zarr
    :param sync: Zarr file synchronizer, defaults to None
    :type sync: zarr.ProcessSynchronizer, optional
    :raises FileNotFoundError: Such file does not exist
    :return: The opened zarr file
    :rtype: xarray.DataArray
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ds = xarray.open_zarr(path, consolidated=False, synchronizer=sync)
    return ds


def read_zarr_attributes(filepath):
    """Read zarr file attributes

    :param filepath: Path to the zarr file
    :type filepath: str
    :raises FileNotFoundError: No such zarr file
    :return: Attributes dictionary
    :rtype: dict
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Zarr file {filepath} does not exist")
    sync = ExtendableDataArray.get_zarr_synchronizer(filepath)
    z = zarr.open(filepath, mode="r", synchronizer=sync)
    attributes = z.attrs.asdict()
    return attributes


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
    sync = ExtendableDataArray.get_zarr_synchronizer(array_path)
    zarr_array = zarr.open(array_path, mode="a", synchronizer=sync)
    zarr_array[dim][:] = coord
    for group_name, group in zarr_array.groups():
        group[dim][:] = coord


def write_zarr_attributes(filepath, attributes):
    if not os.path.exists(filepath):
        raise ValueError(f"Zarr file {filepath} does not exist")
    sync = ExtendableDataArray.get_zarr_synchronizer(filepath)
    z = zarr.open(filepath, mode="a", synchronizer=sync)
    z.attrs.update(attributes)


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
