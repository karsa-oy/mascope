import fnmatch
import json
import os
import glob
from shutil import rmtree
import numpy as np
import xarray as xr
import zarr


from mascope_file.name import parse_path_from_item_filename, filename_to_zarr_path
from mascope_file.runtime import runtime

# READ


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
        zarrs.append(var.removesuffix(".zarr"))
    return zarrs


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
    runtime.logger.debug(f"Loading array {base_filename} : {var}")
    var_path = filename_to_zarr_path(base_filename, var)

    if not os.path.exists(var_path):
        if var == "signal":
            runtime.logger.error("Use load_signal to access signal array")
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
            runtime.logger.error("Use load_signal to access signal array")
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


def load_peak_data(base_filename, drop_bad_peaks=True):
    """Load peak data from sample file

    :param base_filename: Sample file filename
    :type base_filename: str
    :param drop_bad_peaks: Flag to drop weak and satellite peaks, defaults to True
    :type drop_bad_peaks: bool, optional
    :return: Loaded peak data
    :rtype: xr.Dataset
    """
    peak_data = load_file(base_filename, vars=["peak_timeseries"])
    if drop_bad_peaks:
        bad_peak_mask = peak_data.is_weak | peak_data.is_satellite
        peak_data = peak_data.sel(mz=peak_data.mz.values[~bad_peak_mask])
    return peak_data


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

    filepath = parse_path_from_item_filename(base_filename)
    if not os.path.exists(filepath):
        runtime.logger.warning(f"File not found: {filepath}")
        raise FileNotFoundError(filepath)
    if vars is None:
        # Get all saved variable names
        zarrs = get_file_data_vars(filepath)
        vars = [zarr.removesuffix(".zarr") for zarr in zarrs]
    if "signal" in vars:
        runtime.logger.error(
            "Loading signal with load_file is depricated. Use load_signal instead."
        )
        vars.pop(vars.index("signal"))
    # Load arrays from mfzarrs
    runtime.logger.info(f"Loading {', '.join(vars)} from {base_filename}")
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
            runtime.logger.warning(f"[load_file] {var} not found for {base_filename}:")
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
            runtime.logger.debug(f"group {g} already loaded")
            groups.remove(g)
    if not groups:
        runtime.logger.debug("no new groups")
        return prev_array
    runtime.logger.debug(f"loading groups: {groups}")
    x = xr.concat(
        [xr.open_zarr(path, g, consolidated=False, synchronizer=sync) for g in groups],
        concat_dim,
    )
    if prev_array is not None:
        x = xr.concat([prev_array.to_dataset(), x], concat_dim)
    x.attrs = z.attrs.asdict()
    x.attrs["zarr_groups"] = groups
    return x


def read_props(base_filename: str) -> dict:
    """Read properties from a sample file's .props JSON.

    :param base_filename: Sample file filename
    :type base_filename: str
    :return: Properties dictionary
    :rtype: dict
    """
    prop_path = os.path.join(parse_path_from_item_filename(base_filename), ".props")
    with open(prop_path, "r") as f:
        return json.load(f)


# WRITE


def write_props(base_filename, props):
    """Write properties into sample file.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param props: Properties to write
    :type props: dict
    """
    sample_data_path = parse_path_from_item_filename(base_filename)
    # Write properties
    prop_path = os.path.join(sample_data_path, ".props")
    with open(prop_path, "w") as f:
        json.dump(props, f, indent=4)


def update_props(base_filename, props_to_update):
    """Update sample file properties and write to file. Properties given are updated, rest (if any) remain as is.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param props_to_update: Properties to update,
    :type props_to_update: dict
    """
    sample_data_path = parse_path_from_item_filename(base_filename)
    # Update properties
    prop_path = os.path.join(sample_data_path, ".props")
    with open(prop_path, "r") as f:
        props = json.load(f)
    props.update(props_to_update)
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


def write_peaks(
    peak_timeseries: xr.Dataset,
    filename: str,
    overwrite: bool = False,
) -> None:
    """Write fitted peak areas and peak heights to zarr files

    :param peak_timeseries: Dataset containing peak areas and peak heights
    :type peak_timeseries: xr.Dataset
    :param filename: Sample file name
    :type filename: str
    :param overwrite: Flag to overwrite peaks if they already exist, defaults to False
    :type overwrite: bool, optional
    :return: None
    """
    peak_timeseries_path = filename_to_zarr_path(filename, "peak_timeseries")

    def _full_overwrite():
        """Full-write helper"""
        runtime.logger.debug(
            f"Full overwrite of peak_timeseries at {peak_timeseries_path}"
        )
        if os.path.exists(peak_timeseries_path):
            try:
                rmtree(peak_timeseries_path)
            except Exception:
                runtime.logger.error("Failed to remove existing peak timeseries")
                raise
        peak_timeseries.to_zarr(peak_timeseries_path, mode="w")

    # --- Full overwrite ---
    file_not_processed = not os.path.exists(peak_timeseries_path)
    if overwrite or file_not_processed:
        try:
            _full_overwrite()
            return
        except FileNotFoundError as e:
            if ".partial" in str(e):
                raise Exception(
                    f"The path is probably too long: {peak_timeseries_path}"
                ) from e
            else:
                raise

    # -- Partial update --
    runtime.logger.debug(f"Writing new peak timeseries into {peak_timeseries_path}...")

    all_peak_timeseries = xr.open_zarr(peak_timeseries_path)
    try:
        # Find the integer indices for the (mz, time) region to update
        mz_update = peak_timeseries.coords["mz"].values
        indexer = all_peak_timeseries.get_index("mz").get_indexer(mz_update)
    except KeyError:
        runtime.logger.error(
            "Failed to find exact 'mz' coordinates from input "
            "in peak timeseries. Cannot write new peak timeseries into zarr."
        )
        raise

    # Group contiguous indices in indexer for efficient region writing
    breaks = np.diff(indexer) != 1
    group_starts = np.insert(np.where(breaks)[0] + 1, 0, 0)
    group_ends = np.append(np.where(breaks)[0], indexer.size - 1)
    contiguous_regions = [
        (indexer[start], indexer[end]) for start, end in zip(group_starts, group_ends)
    ]

    total_num_regions = len(contiguous_regions)
    for i, (start_idx, end_idx) in enumerate(contiguous_regions):
        try:
            region = {"mz": slice(start_idx, end_idx + 1), "time": slice(None)}
            region_mask = (indexer >= start_idx) & (indexer <= end_idx)
            update_indices = np.where(region_mask)[0]
            contiguous_mz_data = peak_timeseries.isel(mz=update_indices)
            # Safe chunks disabled because the chunking is known to be compatible
            # otherwise region writing fails because of chunk mis-alignment
            contiguous_mz_data.to_zarr(
                peak_timeseries_path, mode="r+", region=region, safe_chunks=False
            )
            progress_percent = (i + 1) / total_num_regions * 100
            if progress_percent % 10 == 0:
                runtime.logger.debug(
                    f"{progress_percent:.1f}% done writing peak timeseries..."
                )
        except Exception:
            runtime.logger.error(
                "Failed to write peak timeseries for "
                f"mz values {mz_update[start_idx]} to {mz_update[end_idx]}."
            )
            raise

    runtime.logger.debug(
        f"Successfully saved peak timeseries for {len(mz_update)} mz values at {peak_timeseries_path}"
    )


def delete_peaks(base_filename: str):
    """Delete sample file peaks.

    :param base_filename: Sample file filename
    :type base_filename: str
    """
    sample_data_path = parse_path_from_item_filename(base_filename)
    peak_dirs = glob.glob(os.path.join(sample_data_path, "peak_*"))
    for dir in peak_dirs:
        rmtree(dir)
