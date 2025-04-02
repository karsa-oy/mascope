from __future__ import annotations
import asyncio
import glob
import os
from shutil import rmtree
from typing import Literal

from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    get_sample_files,
    compute_sample_file_peaks,
)
from mascope_backend.runtime import runtime
from mascope_file.name import parse_path_from_item_filename

# Actions


async def delete_sum_signal():
    """Delete "sum_signal" from all sample files in the database."""
    # Get all sample files
    sample_file_data = await get_sample_files()
    sample_files = sample_file_data["data"]

    # Delete sum_signal from all sample files
    for i, sample_file in enumerate(sample_files):
        runtime.logger.info(
            (
                f"Deleting sum_signal from sample file {sample_file['filename']}: ",
                f"{i+1}/{len(sample_files)}",
            )
        )
        sample_data_path = parse_path_from_item_filename(sample_file["filename"])
        sum_signal_dirs = glob.glob(os.path.join(sample_data_path, "sum_signal*"))
        for zarr_dir in sum_signal_dirs:
            rmtree(zarr_dir)


async def refit_peaks():
    """Refit all peaks for all sample files in the database."""
    # Get all sample files
    sample_file_data = await get_sample_files()
    sample_files = sample_file_data["data"]

    # Compute all sample file peaks
    for i, sample_file in enumerate(sample_files):
        runtime.logger.info(
            (
                f"Computing peaks for sample file {sample_file['filename']}: ",
                f"{i+1}/{len(sample_files)}",
            )
        )
        await compute_sample_file_peaks(
            sample_file["sample_file_id"],
            if_exists="replace",
            independent_transaction=True,
        )


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
    asyncio.run(ACTIONS[action_name]())
