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
import asyncio
import fnmatch
import os
import numpy as np

from datetime import datetime
from sqlalchemy import (
    select,
    desc,
)


from mascope_backend.db import init_db, async_session

from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.db.models import InstrumentFunction as InstrumentConfig

from mascope_file.name import get_instrument_type

from mascope_signal.peak import detect_peaks
from mascope_signal.instrument_func.fit import r_orbi


from mascope_backend.runtime import runtime


loop = None


async def get_instrument_functions(
    filename: str,
) -> dict:
    """
    Retrieves a single instrument config either by filename
    """
    async with async_session() as session:
        # 2A: Fetch instrument function by filename
        sample_file = await fetch_sample_file(filename=filename)
        stmt = (
            (
                select(InstrumentConfig)
                .where(
                    InstrumentConfig.method_file == sample_file.method_file,
                    InstrumentConfig.instrument == sample_file.instrument,
                )
                .order_by(desc(InstrumentConfig.datetime_utc))
                .limit(1)
            )
            if sample_file.method_file
            else (
                select(InstrumentConfig)
                .where(
                    InstrumentConfig.instrument == sample_file.instrument,
                )
                .order_by(desc(InstrumentConfig.datetime_utc))
                .limit(1)
            )
        )
        # Step 3: Execute query
        results = await session.execute(stmt)
        instrument_config = results.scalar_one_or_none()

        # Step 4: Check existence
        if not instrument_config:
            raise ValueError(f"Instrument config not found for {filename}")

        instrument_config = instrument_config.to_dict()

    peakshape = instrument_config["peakshape"]
    R_p = instrument_config["resolution_function"]
    if len(R_p) == 1:
        # Use native Orbitrap resolution function
        p1 = R_p[0]

        def R(m):
            return r_orbi(m, p1)

    elif len(R_p) == 2:
        # Use resolution function from Junninen's thesis for TOF
        p1, p2 = R_p

        def R(m):
            return m / (p1 * m + p2)

    elif len(R_p) == 3:
        # Use 2nd order polynomial (backwards compatibility for Orbitrap) TODO: legacy
        R = np.poly1d(R_p)
    return peakshape, R


def sample_file_op(sample_filepath: str, sample_filename: str) -> None:
    """Do something to the sample file

    :param sample_filepath: Full path to the sample file
    :type sample_filepath: str
    :param sample_filename: Name of the sample file
    :type sample_filename: str
    """
    global loop
    try:
        instrument_type = get_instrument_type(sample_filename)
        if instrument_type == "orbi":
            threshold = 0.8
        if instrument_type == "tof":
            threshold = 0.9

        instrument_functions = loop.run_until_complete(
            get_instrument_functions(filename=sample_filename)
        )
        loop.run_until_complete(
            detect_peaks(
                sample_filename,
                instrument_functions,
                threshold,
                if_exists="append",
            )
        )
    except Exception as e:
        print(f"Failed to process sample file {sample_filename}: {e}")


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
        required=True,
    )
    args = parser.parse_args()
    sample_filename_pattern = args.filename_pattern

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())

    print(f"Walking through the filestore at {runtime.filestore()}")
    for dirpath, dirnames, filenames in os.walk(runtime.filestore()):
        # Check if we are in a date directory
        try:
            datetime.strptime(dirpath.split(os.sep)[-1], "%Y.%m.%d")
        except ValueError:
            # Not a date directory
            continue
        # We are in a date directory, dirnames are sample files
        for sample_filename in fnmatch.filter(dirnames, sample_filename_pattern):
            print(f"Processing {sample_filename}")
            sample_filepath = os.path.join(dirpath, sample_filename)
            sample_file_op(sample_filepath, sample_filename)
            # Directories and files inside the sample file
            _, sample_file_arrays, sample_file_attrs = next(os.walk(sample_filepath))
            for sample_file_array in sample_file_arrays:
                sample_file_array_op(sample_filepath, sample_file_array)
            for sample_file_attr in sample_file_attrs:
                sample_file_attr_op(sample_filepath, sample_file_attr)
