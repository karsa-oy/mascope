import fnmatch
import json
import os
import glob
from shutil import rmtree
import numpy as np
import xarray as xr
import zarr
import asyncio


import mascope_file.name as m_name
from mascope_file.runtime import runtime


CONCURRENT_WRITE_LIMIT = 2  # Max number of concurrent writes to prevent OutOfMemory


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
    var_path = m_name.filename_to_zarr_path(base_filename, var)

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
    var_path = m_name.filename_to_zarr_path(base_filename, var)

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


def load_peak_data(base_filename: str, drop_bad_peaks: bool = True) -> xr.Dataset:
    """Load peak data from sample file

    :param base_filename: Sample file filename
    :type base_filename: str
    :param drop_bad_peaks: Flag to drop weak and satellite peaks, defaults to True
    :type drop_bad_peaks: bool, optional
    :return: Loaded peak data with sample file properties attached
    :rtype: xr.Dataset
    """
    peak_data = load_array(base_filename, var="peak_timeseries")
    if drop_bad_peaks:
        bad_peak_mask = peak_data.is_weak | peak_data.is_satellite
        peak_data = peak_data.sel(mz=peak_data.mz.values[~bad_peak_mask])
    # Add zarr file properties to attributes for reverse compatibility
    props = read_props(base_filename)
    peak_data.attrs["props"] = props
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

    filepath = m_name.parse_path_from_item_filename(base_filename)
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
    prop_path = os.path.join(
        m_name.parse_path_from_item_filename(base_filename), ".props"
    )
    with open(prop_path, "r") as f:
        return json.load(f)


def write_props(base_filename, props):
    """Write properties into sample file.

    :param base_filename: Sample file filename
    :type base_filename: str
    :param props: Properties to write
    :type props: dict
    """
    sample_data_path = m_name.parse_path_from_item_filename(base_filename)
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
    sample_data_path = m_name.parse_path_from_item_filename(base_filename)
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
    array_path = m_name.filename_to_zarr_path(base_filename, var)
    sync = get_zarr_synchronizer(array_path)
    zarr_array = zarr.open(array_path, mode="a", synchronizer=sync)
    zarr_array[dim][:] = coord
    for group_name, group in zarr_array.groups():
        group[dim][:] = coord


def get_dataset_vars(dataset: xr.Dataset) -> list:
    """Extracts dataset variables and their properties.

    :param dataset: xr.Dataset
    :type dataset: xr.Dataset
    :return: List of variables with their properties
    :rtype: list
    """
    variables = []
    for name, da in dataset.data_vars.items():
        dims = tuple(da.dims)
        dtype = da.dtype
        variables.append({"name": name, "dims": dims, "dtype": dtype})
    return variables


def calculate_mz_chunk_size(
    time_coord_size: int, variables: list, desired_chunk_mb: int = 50
) -> int:
    """Calculates an appropriate chunk size along the 'mz' dimension based on the desired chunk size in MB.

    :param time_coord_size: Size of the 'time' coordinate dimension
    :type time_coord_size: int
    :param variables: List of dataset variables with their properties
    :type variables: list
    :param desired_chunk_mb: Desired chunk size in megabytes, defaults to 50
    :type desired_chunk_mb: int, optional
    :return: Calculated chunk size along 'mz' dimension
    :rtype: int
    """
    desired_bytes = desired_chunk_mb * 1024 * 1024
    bytes_per_mz = 0  # Bytes consumed per mz index across all variables
    for v in variables:
        dtype = np.dtype(v["dtype"])
        if v["dims"] == ("mz", "time") or v["dims"] == ("time", "mz"):
            bytes_per_mz += dtype.itemsize * time_coord_size
        elif v["dims"] == ("mz",):
            bytes_per_mz += dtype.itemsize
        elif dtype.kind == "U":
            if v["dims"] == ("mz",):
                bytes_per_mz += dtype.itemsize
    chunk_mz = desired_bytes // bytes_per_mz
    return int(chunk_mz)


async def write_peaks(
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
    peak_timeseries_path = m_name.filename_to_zarr_path(filename, "peak_timeseries")
    synchronizer = get_zarr_synchronizer(peak_timeseries_path)

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
        peak_timeseries.to_zarr(
            peak_timeseries_path, mode="w", synchronizer=synchronizer
        )

    # --- Full overwrite ---
    file_not_processed = not os.path.exists(peak_timeseries_path)
    if overwrite or file_not_processed:
        try:
            await asyncio.to_thread(_full_overwrite)
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

    # Lazy load target dataset metadata to get indexing and chunk info
    all_peak_timeseries = xr.open_zarr(peak_timeseries_path, synchronizer=synchronizer)

    # Calculate mz chunk size
    time_coord_size = all_peak_timeseries.time.size
    variables = get_dataset_vars(peak_timeseries)
    mz_chunk_size = calculate_mz_chunk_size(time_coord_size, variables)

    # Get indexer for input mz values
    try:
        mz_update = peak_timeseries.coords["mz"].values
        indexer = all_peak_timeseries.get_index("mz").get_indexer(mz_update)
    except Exception as e:
        runtime.logger.error(
            "Failed to find provided m/z values in existing peak timeseries."
            "Cannot write peak timeseries."
        )
        raise e

    # Calculate which Zarr chunk index each peak belongs to
    chunk_indices = indexer // mz_chunk_size
    unique_chunks = np.unique(chunk_indices)

    runtime.logger.debug(
        f"Updating {len(indexer)} peaks scattered across {len(unique_chunks)} Zarr chunks."
    )

    # Semaphore to prevent OutOfMemory
    semaphore = asyncio.Semaphore(CONCURRENT_WRITE_LIMIT)

    async def protected_write(chunk_idx):
        async with semaphore:
            # Calculate boundaries of this Zarr chunk
            c_start = int(chunk_idx * mz_chunk_size)
            c_end = int((chunk_idx + 1) * mz_chunk_size)

            # Filter input data that belongs to this specific chunk
            mask = (indexer >= c_start) & (indexer < c_end)
            relevant_indices = indexer[mask]

            # Slice the input dataset to get only data for this chunk
            subset_data = peak_timeseries.isel(mz=np.where(mask)[0])

            # Run the Read-Modify-Write in a thread
            await asyncio.to_thread(
                _process_chunk_sync,
                c_start,
                c_end,
                peak_timeseries_path,
                subset_data,
                relevant_indices,
                synchronizer,
            )

    # --- Create tasks for each chunk update ---
    tasks = [protected_write(c_idx) for c_idx in unique_chunks]

    # --- Execute all chunk updates concurrently ---
    try:
        await asyncio.gather(*tasks)
    except Exception:
        runtime.logger.error("Failed during batched chunk update.")
        raise

    runtime.logger.debug(
        f"Successfully saved peak timeseries for {len(mz_update)} mz values."
    )


def _process_chunk_sync(
    chunk_start: int,
    chunk_end: int,
    peak_timeseries_path: str,
    update_data: xr.Dataset,
    update_indices_in_chunk: np.ndarray,
    synchronizer: zarr.ProcessSynchronizer,
) -> None:
    """Helper to execute chunk processing, to be run in a thread.

    Performs Read-Modify-Write on a single Zarr chunk.

    :param chunk_start: Index of chunk start
    :type chunk_start: int
    :param chunk_end: Index of chunk end
    :type chunk_end: int
    :param peak_timeseries_path: Path to peak timeseries zarr file
    :type peak_timeseries_path: str
    :param update_data: Data to write into this chunk
    :type update_data: xr.Dataset
    :param update_indices_in_chunk: Indices (global) within this chunk to update
    :type update_indices_in_chunk: np.ndarray
    :param synchronizer: Zarr file synchronizer
    :type synchronizer: zarr.ProcessSynchronizer
    """
    # --- Define the region for the whole chunk ---
    full_ds = xr.open_zarr(peak_timeseries_path, synchronizer=synchronizer)
    max_idx = full_ds.mz.size
    current_chunk_end = min(chunk_end, max_idx)

    region_slice = slice(chunk_start, current_chunk_end)
    region_map = {"mz": region_slice, "time": slice(None)}

    # --- READ: Load the existing chunk from Zarr into memory
    ds_chunk = full_ds.isel(mz=region_slice).load()
    full_ds.close()

    # --- MODIFY: Update the specific indices in this chunk ---
    # 'update_data' contains only the new peaks.
    # 'update_indices_in_chunk' are global indices.
    # must map global indices to local chunk indices (0 to chunk_size).
    local_indices = update_indices_in_chunk - chunk_start

    # Iterate variables to update
    for var_name in update_data.data_vars:
        if var_name in ds_chunk:
            arr = ds_chunk[var_name].values
            update_arr = update_data[var_name].values
            if arr.ndim == 1:
                # Variable depends only on 'mz'
                arr[local_indices] = update_arr
            else:
                # Variable depends on 'mz' and 'time'
                arr[local_indices, :] = update_arr

    # --- WRITE: Save the modified chunk back to Zarr ---
    ds_chunk.to_zarr(
        peak_timeseries_path,
        mode="r+",
        region=region_map,
        safe_chunks=False,
        synchronizer=synchronizer,
    )


def delete_peaks(base_filename: str) -> None:
    """Delete sample file peaks.

    :param base_filename: Sample file filename
    :type base_filename: str
    """
    sample_data_path = m_name.parse_path_from_item_filename(base_filename)
    peak_dirs = glob.glob(os.path.join(sample_data_path, "peak_*"))
    for dir in peak_dirs:
        rmtree(dir)


def load_batch_cache(
    sample_batch_id: str,
    zarr_filename: str,
) -> xr.Dataset:
    """Load batch cached data from the zarr file.

    :param sample_batch_id: Sample batch ID
    :type sample_batch_id: str
    :param zarr_filename: Name of a zarr file
    :type zarr_filename: str
    :raises FileNotFoundError: Batch cache file not found
    :return: Loaded batch cache data
    :rtype: xr.Dataset
    """
    batch_path = m_name.get_batch_cache_path(sample_batch_id)
    var_path = os.path.join(batch_path, f"{zarr_filename}.zarr")
    if not os.path.exists(var_path):
        raise FileNotFoundError(f"Batch cache file not found: {var_path}")
    synchronizer = get_zarr_synchronizer(var_path)
    return xr.open_zarr(var_path, synchronizer=synchronizer)


def write_batch_cache(
    sample_batch_id: str,
    zarr_filename: str,
    batch_peaks: xr.Dataset,
) -> None:
    """Write batch cache data to the zarr file.

    :param sample_batch_id: Sample batch ID
    :type sample_batch_id: str
    :param zarr_filename: Name of a zarr file
    :type zarr_filename: str
    :param batch_peaks: Batch cache data to write
    :type batch_peaks: xr.Dataset
    """
    batch_path = m_name.get_batch_cache_path(sample_batch_id)
    var_path = os.path.join(batch_path, f"{zarr_filename}.zarr")
    synchronizer = get_zarr_synchronizer(var_path)
    batch_peaks.to_zarr(var_path, mode="w", synchronizer=synchronizer)


def delete_batch_cache(sample_batch_id: str) -> None:
    """Delete sample batch cache.

    :param sample_batch_id: Sample batch ID
    :type sample_batch_id: str
    """
    batch_path = m_name.get_batch_cache_path(sample_batch_id)
    if os.path.exists(batch_path):
        rmtree(batch_path)
