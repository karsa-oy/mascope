"""
Migration script, the script name shows a new database version.
"""

import os
import shutil

from mascope_file.name import get_sample_file_type
from mascope_file.io import delete_peaks
from mascope_backend.api.controllers.match.match_controller import (
    match_compute_sample,
    match_remove_sample,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    get_sample_items,
)
from mascope_backend.db import configure_database_engine
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.backup import create_db_backup

from mascope_backend.runtime import runtime


async def run():
    """
    Execute the database migration
    """
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    old_version = 25
    new_version = 26
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    sample_item_dict = await get_sample_items()

    # Filter those sample items that do not contain Orbi raw files
    sample_item_list = [
        item
        for item in sample_item_dict["data"]
        if get_sample_file_type(item["filename"]) == "orbi_raw"
    ]

    unique_filenames = set(item["filename"] for item in sample_item_list)
    n_filenames = len(unique_filenames)
    for i, filename in enumerate(unique_filenames):
        runtime.logger.info(
            f"{i+1}/{n_filenames} Delete peaks from the sample file {filename}..."
        )
        try:
            delete_peaks(filename)
        except Exception as e:
            runtime.logger.error(f"Error deleting peaks from {filename}: {e}")
            continue

    n_sample_items = len(sample_item_list)
    for i, sample_item in enumerate(sample_item_list):
        runtime.logger.info(
            f"{i+1}/{n_sample_items} Compute matches for {sample_item["sample_item_name"]}, id={sample_item["sample_item_id"]}..."
        )
        try:
            await match_remove_sample(
                sample_item["sample_item_id"],
                independent_transaction=True,
                sid="",
                process_id="",
            )
            await match_compute_sample(
                sample_item["sample_item_id"],
                independent_transaction=True,
                sid="",
                process_id="",
            )
        except Exception as e:
            runtime.logger.error(
                f"Error computing matches for {sample_item["sample_item_name"]}: {e}"
            )
            continue

    # Clean up the database
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed successfully.")
