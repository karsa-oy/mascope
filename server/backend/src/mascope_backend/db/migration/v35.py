"""
Update .props for TOF files if any: rename mass_calibration to mz_calibration.
"""

import asyncio
import json
import os
import shutil

from sqlalchemy import select

import mascope_file.io as m_io
import mascope_file.name as m_name
from mascope_backend.db import SampleFile, async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.runtime import runtime


async def run():
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 34
    new_version = 35
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)
    runtime.logger.info(
        f"Starting v{new_version} migration: update .props for TOF files if any."
    )

    # Get the TOF sample files
    async with async_session() as session:
        stmt = select(SampleFile).where(
            SampleFile.instrument.ilike("%tof%") | SampleFile.instrument.ilike("%api%")
        )
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

    # Update .props for each TOF sample file
    num_of_files = len(sample_files)
    failed_sample_files = []
    for i, sample_file in enumerate(sample_files):
        runtime.logger.info(
            f"({i+1}/{num_of_files}) Updating .props for file {sample_file.filename}"
        )
        try:
            props = m_io.read_props(sample_file.filename)
            updated_props = get_curated_props(props)
            overwrite_props(sample_file.filename, updated_props)
        except Exception as e:
            runtime.logger.error(
                f"Failed to update .props for file {sample_file.filename}: {e}"
            )
            failed_sample_files.append(sample_file.filename)

    # Log summary of migration
    if failed_sample_files:
        runtime.logger.warning(
            f"Failed to update .props for {len(failed_sample_files)} files: {failed_sample_files}"
        )
    runtime.logger.info(f"Migration to v{new_version} completed.")


def get_curated_props(old_props):
    """Update old_props to new format."""
    updated_props = old_props.copy()
    notation = which_calibration_notation(old_props)
    match notation:
        case "both":
            updated_props.pop("mass_calibration")
        case "old":
            updated_props["mz_calibration"] = updated_props.pop("mass_calibration")
        case "new":
            pass
        case None:
            updated_props["mz_calibration"] = None

    return updated_props


def which_calibration_notation(old_props):
    """Determine which calibration notation is used in old_props."""
    keys = list(old_props.keys())
    if "mass_calibration" in keys and "mz_calibration" in keys:
        return "both"
    elif "mass_calibration" in keys:
        return "old"
    elif "mz_calibration" in keys:
        return "new"
    else:
        return None


def overwrite_props(base_filename, updated_props):
    """Overwrite the .props file with updated_props."""
    sample_data_path = m_name.parse_path_from_item_filename(base_filename)
    props_path = os.path.join(sample_data_path, ".props")
    with open(props_path, "w") as f:
        json.dump(updated_props, f, indent=4)


if __name__ == "__main__":
    asyncio.run(run())
