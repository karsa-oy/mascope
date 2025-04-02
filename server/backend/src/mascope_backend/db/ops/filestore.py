from __future__ import annotations
import asyncio
import glob
import os
from shutil import rmtree
from typing import Literal

from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_files,
)
from mascope_backend.api.controllers.sample.lib.sample_file_compute import (
    compute_peaks,
)
from mascope_backend.db import init_db
from mascope_backend.runtime import runtime
from mascope_file.name import parse_path_from_item_filename

# Actions


async def delete_sum_signal():
    """Delete "sum_signal" from all sample files in the database."""
    # Get all sample files
    sample_files = await fetch_sample_files()

    # Delete sum_signal from all sample files
    for i, sample_file in enumerate(sample_files):
        runtime.logger.info(
            (
                f"Deleting sum_signal from sample file {sample_file.filename}: ",
                f"{i+1}/{len(sample_files)}",
            )
        )
        sample_data_path = parse_path_from_item_filename(sample_file.filename)
        sum_signal_dirs = glob.glob(os.path.join(sample_data_path, "sum_signal*"))
        for zarr_dir in sum_signal_dirs:
            rmtree(zarr_dir)


async def refit_peaks():
    """Refit all peaks for all sample files in the database."""
    # Get all sample files
    sample_files = await fetch_sample_files()

    # Compute all sample file peaks
    for i, sample_file in enumerate(sample_files):
        runtime.logger.info(
            (
                f"Computing peaks for sample file {sample_file.filename}: ",
                f"{i+1}/{len(sample_files)}",
            )
        )
        try:
            await compute_peaks(
                sample_file.filename,
                if_exists="replace",
            )
        except FileNotFoundError:
            runtime.logger.error(
                f"Error computing peaks for sample file {sample_file.filename}. File not found."
            )
            continue
        except ValueError as e:
            runtime.logger.error(
                f"Error computing peaks for sample file {sample_file.filename}: {e}."
            )
            continue


async def test():
    """Test function to check if the CLI is working."""
    runtime.logger.info("Test function executed successfully.")


# CLI entry point


ACTIONS = {
    "delete_sum_signal": delete_sum_signal,
    "refit_peaks": refit_peaks,
    "test": test,
}
ActionTypes = Literal[tuple(ACTIONS.keys())]


def run_action(action_name: ActionTypes) -> None:
    """Run a specific action based on the action name.

    :param action_name: Name of the action to perform.
    :type action_name: Actions
    """
    asyncio.run(init_db())
    asyncio.run(ACTIONS[action_name]())
