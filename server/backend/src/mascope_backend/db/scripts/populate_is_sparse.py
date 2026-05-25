"""
Maintenance script to backfill the 'is_sparse' variable in peak_timeseries.zarr
for all existing sample files.

For each sample file in the database, checks if 'is_sparse' exists in its
peak_timeseries.zarr. If missing, computes and writes it using the migration
function from mascope_file.io.

This script is idempotent — safe to re-run at any time. It does not interfere
with the lazy migration in load_peak_data which handles the same case on-demand.

Usage:
    mascope dev db script run populate_is_sparse
    mascope prod db script run populate_is_sparse

Date: 2026-05-25
"""

import asyncio

from sqlalchemy import select

from mascope_backend.db import SampleFile, async_session, configure_database_engine
from mascope_backend.runtime import runtime

import mascope_file.io as m_io


PROGRESS_LOG_INTERVAL = 500


async def populate_is_sparse() -> dict:
    """Backfill 'is_sparse' for all sample files where it is missing.

    :return: Summary counts {"total": int, "migrated": int, "skipped": int, "errors": int}
    :rtype: dict
    """
    async with async_session() as session:
        result = await session.execute(select(SampleFile.filename))
        filenames = [row[0] for row in result.all()]

    total = len(filenames)
    runtime.logger.info(f"Found {total} sample file(s) to check for 'is_sparse'")

    if total == 0:
        return {"total": 0, "migrated": 0, "skipped": 0, "errors": 0}

    migrated = 0
    skipped = 0
    errors = 0

    for i, filename in enumerate(filenames, 1):
        try:
            was_created = m_io.ensure_is_sparse_exists(filename)
            if was_created:
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            runtime.logger.warning(
                f"Error processing {filename!r}: {type(e).__name__}: {e}"
            )

        if i % PROGRESS_LOG_INTERVAL == 0:
            runtime.logger.info(
                f"Progress: {i}/{total} "
                f"(migrated={migrated}, skipped={skipped}, errors={errors})"
            )

    return {"total": total, "migrated": migrated, "skipped": skipped, "errors": errors}


async def run() -> None:
    """Initialise the database and run the backfill."""
    await configure_database_engine()

    result = await populate_is_sparse()

    runtime.logger.info("=" * 80)
    runtime.logger.info("POPULATE IS_SPARSE COMPLETE")
    runtime.logger.info(f"Total sample files checked : {result['total']}")
    runtime.logger.info(f"Migrated (is_sparse added) : {result['migrated']}")
    runtime.logger.info(f"Skipped (already present)  : {result['skipped']}")
    runtime.logger.info(f"Errors (file issues)       : {result['errors']}")
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the backfill script."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        runtime.logger.info("Cancelled by user (Ctrl+C)")
    except Exception as e:
        runtime.logger.exception(f"Script failed: {e}")
        raise


if __name__ == "__main__":
    main()
