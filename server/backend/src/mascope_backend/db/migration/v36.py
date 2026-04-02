"""
Fix Orbi calibration
"""

import asyncio
import glob
import json
import os
import shutil
from shutil import rmtree

from sqlalchemy import select

import mascope_file.io as m_io
import mascope_file.name as m_name
from mascope_backend.api.controllers.match.match_controller import rematch_sample
from mascope_backend.db import (
    SampleFile,
    SampleItem,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.runtime import runtime
from mascope_signal.peak import (
    compute_peaks,
)


async def run():
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 35
    new_version = 36
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    orbi_failed_sample_files_flag = await _migrate_orbi_files()
    tof_failed_sample_files_flag = await _migrate_tof_files()
    failed_sample_files_flag = (
        orbi_failed_sample_files_flag or tof_failed_sample_files_flag
    )

    runtime.logger.info(f"Migration to v{new_version} completed.")
    if failed_sample_files_flag:
        runtime.logger.warning(
            "Some sample files failed to update. Please check the logs for details."
        )


async def _migrate_orbi_files():
    """
    Update .props for Orbi files if any: set mz_calibration to None, remove stale sum signals,
    recompute peaks, and rematch samples.
    """
    failed_sample_files_flag = False

    async with async_session() as session:
        stmt = select(SampleFile).where(SampleFile.instrument.ilike("%orbi%"))
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

    num_of_files = len(sample_files)
    failed_sample_files_flag = False
    for i, sample_file in enumerate(sample_files):
        runtime.logger.info(
            f"({i + 1}/{num_of_files}) Checking file {sample_file.filename}"
        )
        try:
            props = m_io.read_props(sample_file.filename)
            mz_calibration = props["mz_calibration"]
            if mz_calibration is None:
                runtime.logger.info(
                    f"File {sample_file.filename} has no calibration; skipping."
                )
                continue

            runtime.logger.info(
                "Delete stale sum signals and calibrations and recompute peaks."
            )
            _remove_sum_signals(sample_file)
            _remove_peaks(sample_file)

            updated_props = props.copy()
            updated_props["mz_calibration"] = None
            _overwrite_props(sample_file.filename, updated_props)

            compute_peaks(sample_file.filename, if_exists="replace")

            runtime.logger.info(f"Rematching samples for file {sample_file.filename}.")
            await _rematch_sample_files_by_id(sample_file.sample_file_id)
        except Exception as e:
            runtime.logger.error(
                f"Failed to update .props for file {sample_file.filename}: {e}"
            )
            failed_sample_files_flag = True

    return failed_sample_files_flag


async def _migrate_tof_files():
    """
    Delete cached sum signals.
    """
    failed_sample_files_flag = False
    async with async_session() as session:
        stmt = select(SampleFile).where(
            SampleFile.instrument.ilike("%tof%") | SampleFile.instrument.ilike("%api%")
        )
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

    num_of_files = len(sample_files)
    for i, sample_file in enumerate(sample_files):
        try:
            runtime.logger.info(
                f"({i + 1}/{num_of_files}) Deleting cached sum signals for file {sample_file.filename}"
            )
            _remove_sum_signals(sample_file, cached=True)
        except Exception as e:
            runtime.logger.error(
                f"Failed to delete cached sum signals for file {sample_file.filename}: {e}"
            )
            failed_sample_files_flag = True

    return failed_sample_files_flag


def _overwrite_props(base_filename, updated_props):
    """Overwrite the .props file with updated_props."""
    sample_data_path = m_name.parse_path_from_item_filename(base_filename)
    props_path = os.path.join(sample_data_path, ".props")
    with open(props_path, "w") as f:
        json.dump(updated_props, f, indent=4)


def _remove_sum_signals(sample_file, cached=False):
    """Remove all sum_signal* directories in the sample data path."""
    sample_data_path = m_name.parse_path_from_item_filename(sample_file.filename)
    pattern = "sum_signal_*" if cached else "sum_signal*"
    sum_signal_dirs = glob.glob(
        os.path.join(
            sample_data_path,
            pattern,
        )
    )
    for zarr_dir in sum_signal_dirs:
        rmtree(zarr_dir)


def _remove_peaks(sample_file):
    """Remove peaks directories in the sample data path."""
    sample_data_path = m_name.parse_path_from_item_filename(sample_file.filename)
    pattern = "peak_*"
    peak_dirs = glob.glob(
        os.path.join(
            sample_data_path,
            pattern,
        )
    )
    for zarr_dir in peak_dirs:
        rmtree(zarr_dir)


async def _rematch_sample_files_by_id(sample_file_id: str):
    async with async_session() as session:
        stmt = select(SampleItem).where(SampleItem.sample_file_id == sample_file_id)
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

    for sample_item in sample_items:
        await rematch_sample(sample_item.sample_item_id)


if __name__ == "__main__":
    asyncio.run(run())
