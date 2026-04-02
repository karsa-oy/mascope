import os

import numpy as np
import pandas as pd
import xarray as xr

from mascope_file.io import (
    load_array,
    load_file,
)
from mascope_file.name import filename_to_zarr_path, parse_path_from_item_filename


def csv_to_xarr(csv_path: str, filename: str) -> xr.core.dataarray.DataArray:
    """Read the KECU csv file and parse it into xarray

    :param csv_path: path to CSV file
    :type csv_path: str
    :param filename: zarr sample data file name
    :type filename: str
    :return: data array with parsed data from kecu CSV file
    :rtype: xr.core.dataarray.DataArray
    """
    # Read CSV file to dataframe
    kecu_df = pd.read_csv(csv_path)
    # Get list of parameters to add to DataArray
    kecu_params = np.array([str(i) for i in kecu_df.columns if "timestamp" not in i])
    # Convert non-timestamp data to float32
    kecu_df[kecu_params] = kecu_df[kecu_params].astype(np.float32)

    # Convert timestamp to datetime format
    kecu_df["timestamp (UTC)"] = pd.to_datetime(kecu_df["timestamp (UTC)"])
    kecu_df["timestamp (local)"] = pd.to_datetime(kecu_df["timestamp (local)"])
    # Create a column with relative time in seconds separately to avoid PerformanceWarning
    rel_time = (
        kecu_df["timestamp (UTC)"] - kecu_df["timestamp (UTC)"].iloc[0]
    ).dt.total_seconds()
    # Concatenate the new column to the DataFrame
    kecu_df = pd.concat([kecu_df, rel_time.rename("rel_time")], axis=1)

    # Load xarr file time coordinate
    # TODO replace load_array with load_coords when we get rid of a bug in it
    sample_file_time = load_array(filename, "signal").time.values
    # Calculate absolute difference between each value in time coordinate and 'rel_time' in kecu_df
    time_diff = np.abs(kecu_df["rel_time"].values[:, np.newaxis] - sample_file_time)
    # Find the index of the minimum difference for each row in time_arr
    closest_time_row_ind = time_diff.argmin(axis=0)
    # Update kecu dataframe
    kecu_df = kecu_df.iloc[closest_time_row_ind].reset_index(drop=True)

    # Create a new data variable from kecu_df
    kecu_arr = xr.DataArray(
        kecu_df[kecu_params].values,
        dims=("time", "param"),
        coords={
            "time": sample_file_time,
            "param": kecu_params,
        },
        name="kecu",
    )
    # Assign local and UTC time coordinates from kecu file
    kecu_arr = kecu_arr.assign_coords(
        kecu_UTC_time=("time", kecu_df["timestamp (UTC)"])
    )
    kecu_arr = kecu_arr.assign_coords(
        kecu_local_time=("time", kecu_df["timestamp (local)"])
    )
    return kecu_arr


def merge_data_array_into_dataset(
    kecu_arr: xr.core.dataarray.DataArray, filename: str
) -> xr.core.dataset.Dataset:
    """Add KECU data array to sample data file

    :param kecu_arr: data from KECU file as xarray
    :type kecu_arr: xr.core.dataarray.DataArray
    :param filename: base sample data file name
    :type filename: str
    :return: updated sample data file
    :rtype: xr.core.dataset.Dataset
    """
    # Load target sample file
    sample_file_data = load_file(filename)
    # Add kecu data to sample file data
    sample_file_data = sample_file_data.assign(kecu=kecu_arr)
    return sample_file_data


def write_to_sample_file(kecu_arr: xr.core.dataarray.DataArray, filename: str) -> None:
    """Writes KECU data array to the existing sample data file

    :param kecu_arr: data from KECU file as xarray
    :type kecu_arr: xr.core.dataarray.DataArray
    :param filename: base name of the target sample data file
    :type filename: str
    """

    # Check if proper filename
    try:
        data_path = parse_path_from_item_filename(filename)
    except Exception as e:
        raise Exception(f"Error parsing path from filename {filename}: {e}") from e

    # Check if target sample file exists
    if os.path.exists(data_path):
        zarr_file_path = filename_to_zarr_path(filename, "kecu")
        kecu_arr.to_zarr(zarr_file_path, mode="a")
    else:
        raise FileNotFoundError(f"Path {data_path} does not exist. Check filename.")
