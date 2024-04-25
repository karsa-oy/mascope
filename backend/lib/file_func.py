import fnmatch
import json
import os
from ctypes import ArgumentError
from datetime import datetime, timezone
from shutil import rmtree

import dask.array as da
import numpy as np
import xarray
import zarr

from .structs import ExtendableDataArray
from .util import parse_path_from_item_filename


class zarr_sdk:
    @staticmethod
    def finalize_signal_dataset(data, item):
        filename = data["value"]["filename"]
        try:
            final_length = float(item["signal"].time[-1] + item["signal_period"][-1])
        except Exception as e:
            print(
                f"""
                [finalize_signal_dataset] Warning: {e.__class__.__name__}({str(e)})
            """
            )
            final_length = item["props"]["length"]

        # Update properties
        final_length = min(final_length, item["props"]["length"])
        item["props"].update({"committed_length": final_length})
        item["props"].update({"length": final_length})
        # Write properties
        update_props(filename, item["props"])
        # flush arrays
        arrays = [item["signal"], item["signal_period"]]
        for a in arrays:
            if isinstance(a, ExtendableDataArray):
                a.flush()
        # write sum signal array
        zarr_sdk.write_sum_signal_dataset(item)

    @staticmethod
    def init_centroid_dataset(data, item):
        value = data["value"]
        filename = filename_to_zarr_path(value["filename"], "centroids")
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
        value = data["value"]
        filename = value.get("filename")
        mz = np.frombuffer(value["mz"], dtype=np.float32)
        single_ion_signal = value.get("single_ion_signal")
        t_range = value["t_range"]
        mz_calibration = value.get("mz_calibration")
        polarity = value.get("polarity")

        base_path = get_base_path()
        try:
            data_path = parse_path_from_item_filename(filename, base_path)
        except Exception as e:
            raise Exception("Error parsing filename")
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
            "utc_offset": utc_offset,
        }
        write_props(filename, properties)

        return {
            "signal": signal_array,
            "signal_period": period_array,
            "props": properties,
        }

    @staticmethod
    def init_tps_dataset(data, item):
        value = data["value"]
        filename = filename_to_zarr_path(value["filename"], "tps")
        if os.path.exists(filename):
            raise FileExistsError(filename)
        tps_info = value["tps_info"]
        tps_array = ExtendableDataArray(path=filename, array_module=da)
        tps_array.init_array(
            dims=("parameter", "time"), coords=[tps_info, []], name="tps"
        )
        item.update({"tps": tps_array})

    @staticmethod
    def init_viz_dataset(filename_base, viz_type, item):
        # initialize viz_type mfzarr
        filename_viz = filename_to_zarr_path(filename_base, viz_type)
        viz_array = ExtendableDataArray(
            path=filename_viz,
            array_module=np,
            dtype=object,
            chunk_size=1,
        )
        viz_array.init_array(dims=("time",), coords=[[]], name=viz_type)
        viz_period = viz_type + "_period"
        filename_viz_period = filename_to_zarr_path(filename_base, viz_period)
        viz_period_array = ExtendableDataArray(
            path=filename_viz_period,
            array_module=np,
            dtype=object,
            chunk_size=1,
        )
        viz_period_array.init_array(dims=("time",), coords=[[]], name=viz_period)
        item.update({viz_type: viz_array, viz_period: viz_period_array})

    @staticmethod
    def update_centroid_dataset(data, item):
        value = data["value"]
        ti = np.array([value["t"]], dtype=np.float32)
        # print(ti.item())
        c_y = np.frombuffer(value["peak_intensity"], dtype=np.float32)
        c_y = c_y.reshape(-1, 1)
        c_mz = np.frombuffer(value["peak_mz"], dtype=np.float32)
        c_mz = c_mz.reshape(
            -1,
        )

        # Extend data arrays (write to file)
        item["centroids"].extend_array(c_y, [c_mz, ti], "time")

    @staticmethod
    def update_signal_dataset(data, item):
        base_path = get_base_path()
        value = data["value"]
        ti = np.array([value["t"]], dtype=np.float32)
        period = np.array([value["period"]], dtype=np.float32)
        # print(ti.item())
        spec = np.frombuffer(value["spec"], dtype=np.float32)
        spec = spec.reshape(-1, 1)
        if "mz" in value:
            # mz coordinates provided with data (Orbitrap)
            mz = np.frombuffer(value["mz"], dtype=np.float32)
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
                parse_path_from_item_filename(value["filename"], base_path), ".props"
            )
            with open(prop_path, "w") as f:
                json.dump(item["props"], f, indent=4)

    @staticmethod
    def update_tps_dataset(data, item):
        value = data["value"]
        ti = np.array([value.get("t")], dtype=np.float32)
        tps_data = np.frombuffer(value.get("data"), dtype=np.float32)
        tps_data = tps_data.reshape(-1, 1)
        tps_info = item["tps"]["parameter"]
        item["tps"].extend_array(tps_data, [tps_info, ti], "time")

    @staticmethod
    def write_peaks(peak_areas, peak_heights, item, overwrite=False):
        filename_base = item.props["filename"]
        # Write peak areas
        filename_peak_areas = filename_to_zarr_path(filename_base, "peak_areas")
        if os.path.exists(filename_peak_areas):
            if overwrite:
                rmtree(filename_peak_areas)
            else:
                raise FileExistsError(filename_peak_areas)

        peak_areas_array = ExtendableDataArray(path=filename_peak_areas)
        peak_areas_array.init_array(
            dims=("mz", "time"),
            data=peak_areas.values,
            coords={
                "mz": peak_areas.mz.values,
                "time": peak_areas.time.values,
                "tof": ("mz", peak_areas.tof.values),
            },
            name="peak_areas",
        )
        # Write peak heights
        filename_peak_heights = filename_to_zarr_path(filename_base, "peak_heights")
        if os.path.exists(filename_peak_heights):
            if overwrite:
                rmtree(filename_peak_heights)
            else:
                raise FileExistsError(filename_peak_heights)

        peak_heights_array = ExtendableDataArray(path=filename_peak_heights)
        peak_heights_array.init_array(
            dims=("mz", "time"),
            data=peak_heights.values,
            coords={
                "mz": peak_heights.mz.values,
                "time": peak_heights.time.values,
                "tof": ("mz", peak_heights.tof.values),
            },
            name="peak_heights",
        )

    @staticmethod
    def write_sum_signal_dataset(item):
        filename_base = item.props["filename"]
        filename_sum_signal = filename_to_zarr_path(filename_base, "sum_signal")
        sample_file = load_file(filename_base, vars=["signal"])
        sum_signal = sample_file.signal.sum(dim="time").compute()
        sum_signal_array = ExtendableDataArray(
            path=filename_sum_signal, array_module=np
        )
        sum_signal_array.init_array(
            dims=("mz",),
            data=sum_signal.values,
            coords={
                "mz": sum_signal.mz.values,
            },
            name="sum_signal",
        )


def filename_to_zarr_path(base_filename, variable):
    """Derive full path to a zarr data array from sample filename and the desired variable

    :param base_filename: Sample file filename
    :type base_filename: str
    :param variable: Variable name inside the sample file
    :type variable: str
    :return: Full path
    :rtype: str
    """
    base_path = get_base_path()
    sample_data_path = parse_path_from_item_filename(base_filename, base_path)
    zarr_filename = variable + os.extsep + "zarr"
    return os.path.join(sample_data_path, zarr_filename)


def get_base_path():
    """Get path to "instrument" directory

    :return: str
    :rtype: Path
    """
    base_path = os.environ.get("MASCOPE_PRIVATE_INSTRUMENT_DIR", "./instrument")
    return base_path


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
    if "orbi" in instrument_name.lower():
        instrument_type = "orbi"
    elif "tof" in instrument_name.lower():
        instrument_type = "tof"
    else:
        raise ValueError(f"Failed to get instrument type for file {filename}")
    return instrument_type


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

    # print("Loading array %s : %s" %(base_filename, var))
    var_path = filename_to_zarr_path(base_filename, var)
    if not os.path.exists(var_path):
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
    path = filename_to_zarr_path(base_filename, var)
    sync = ExtendableDataArray.get_zarr_synchronizer(path)
    z = zarr.open(path, mode="r", synchronizer=sync)
    coord = z[coord_name]
    return coord[:]


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

    base_path = get_base_path()
    filepath = parse_path_from_item_filename(base_filename, base_path)
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)
    if vars is None:
        # Get all saved variable names
        zarrs = get_file_data_vars(filepath)
        vars = [zarr.strip(".zarr") for zarr in zarrs]
    # Load arrays from mfzarrs
    print(f"Loading {vars} from {base_filename}")
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
        except FileNotFoundError as e:
            print(f"[load_file] Error {base_filename}/{var}:")
            print(f"    {e.__class__.__name__}({str(e)})")
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
            # print('group %s already loaded' %g)
            groups.remove(g)
    if not groups:
        # print('no new groups')
        return prev_array
    # print("loading groups: %s" %groups)
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
    base_path = get_base_path()
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
    base_path = get_base_path()
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
