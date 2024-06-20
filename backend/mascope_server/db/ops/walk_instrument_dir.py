"""
This is a template script to help implementing database operations to be performed
in `MASCOPE_PRIVATE_INSTRUMENT_DIR`.

It visits each sample file directory inside the directory tree under
`MASCOPE_PRIVATE_INSTRUMENT_DIR`, and has placeholder functions `sample_file_array_op`
and `sample_file_attr_op` to be overridden to perform the desired actions.

It accepts the following command line arguments:
"-f", "--filename_pattern",
    help="Sample files satisfying this pattern will be operated upon",
"""

import argparse
import fnmatch
import os

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
instrument_dir = os.environ["MASCOPE_PRIVATE_INSTRUMENT_DIR"]


def sample_file_op(sample_filepath: str, sample_filename: str) -> None:
    """Do something to the sample file

    :param sample_filepath: Full path to the sample file
    :type sample_filepath: str
    :param sample_filename: Name of the sample file
    :type sample_filename: str
    """
    pass


def sample_file_array_op(sample_filepath: str, sample_file_array: str) -> None:
    """Do something to all sample file arrays

    :param sample_filepath: Full path to the sample file
    :type sample_filepath: str
    :param sample_file_array: Name of the sample file array
    :type sample_file_array: str
    """
    pass


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
        required=False,
        default="*",
    )
    args = parser.parse_args()
    sample_filename_pattern = args.filename_pattern

    for dirpath, dirnames, filenames in os.walk(instrument_dir):
        # Check if we are in a date directory
        try:
            datetime.strptime(dirpath.split(os.sep)[-1], "%Y.%m.%d")
        except ValueError as e:
            # Not a date directory
            continue
        # We are in a date directory, dirnames are sample files
        for sample_filename in fnmatch.filter(dirnames, sample_filename_pattern):
            sample_filepath = os.path.join(dirpath, sample_filename)
            # Sample file
            sample_file_op(sample_filepath, sample_filename)
            # Directories and files inside the sample file
            _, sample_file_arrays, sample_file_attrs = next(os.walk(sample_filepath))
            for sample_file_array in sample_file_arrays:
                sample_file_array_op(sample_filepath, sample_file_array)
            for sample_file_attr in sample_file_attrs:
                sample_file_attr_op(sample_filepath, sample_file_attr)
