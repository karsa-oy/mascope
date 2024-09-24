"""
Delete all peak data from the sample files matching the given filename pattern.
"""

import argparse
import fnmatch
import os
import shutil

from datetime import datetime

import mascope_lib.runtime as lib_runtime

lib_runtime.init()

from mascope_lib.file_func import get_filestore_path


instrument_dir = get_filestore_path()


def sample_file_array_op(sample_filepath: str, sample_file_array: str) -> None:
    """Do something to all sample file arrays

    :param sample_filepath: Full path to the sample file
    :type sample_filepath: str
    :param sample_file_array: Name of the sample file array
    :type sample_file_array: str
    """
    if len(fnmatch.filter([sample_file_array], "peak*")) > 0:
        shutil.rmtree(os.path.join(sample_filepath, sample_file_array))


def sample_file_attr_op(sample_filepath: str, sample_file_attr: str) -> None:
    """Do something to all sample file files (currently only .props)

    :param sample_filepath: Full path to the sample file
    :type sample_filepath: str
    :param sample_file_attr: Name of the sample file file
    :type sample_file_attr: str
    """
    pass


if __name__ == "__main__":
    # Handle command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--filename_pattern",
        help="Sample files satisfying this pattern will be operated upon",
        type=str,
        required=True,
    )
    args = parser.parse_args()
    sample_filename_pattern = args.filename_pattern

    print(f"Walking through the filestore at {instrument_dir}")
    for dirpath, dirnames, filenames in os.walk(instrument_dir):
        # Check if we are in a date directory
        try:
            datetime.strptime(dirpath.split(os.sep)[-1], "%Y.%m.%d")
        except ValueError as e:
            # Not a date directory
            continue
        # We are in a date directory, dirnames are sample files
        for sample_filename in fnmatch.filter(dirnames, sample_filename_pattern):
            print(f"Processing {sample_filename}")
            sample_filepath = os.path.join(dirpath, sample_filename)
            # Directories and files inside the sample file
            _, sample_file_arrays, sample_file_attrs = next(os.walk(sample_filepath))
            for sample_file_array in sample_file_arrays:
                sample_file_array_op(sample_filepath, sample_file_array)
            for sample_file_attr in sample_file_attrs:
                sample_file_attr_op(sample_filepath, sample_file_attr)
