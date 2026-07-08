"""
Database operation to remove unmatched (placeholder) match isotopes.

Deletes ``match_isotope`` rows that represent an *unmatched* isotope - a target
isotope with no peak within the match window. These rows carry only constant /
derivable placeholder values (empty ``sample_peak_id``, zero intensity, target m/z,
score 0) and are reconstructed on read from their ``target_isotope``, so persisting
them is pure bloat (historically ~80% of the table). An empty ``sample_peak_id``
(``DEFAULT_UNMATCHED_SAMPLE_PEAK_ID``) is the unambiguous marker; a matched row
always carries a real, non-empty peak id.

The delete is lossless: it only ever removes rows a matched-only backend would
never have written, so higher-level aggregates (match_ion / match_compound / ...)
are unchanged and need no recomputation. It is done in bounded batches so a
multi-hundred-million-row table can be cleaned without one giant transaction /
WAL blowup. Run ``VACUUM FULL match_isotope`` (or pg_repack) afterwards to return
the freed space to the OS.

Entry Points:
- Async: `remove_unmatched_match_isotopes()` for async callers
- CLI:   `mascope dev/prod db script run remove_unmatched_match_isotopes`
"""

import asyncio

from sqlalchemy import text

from mascope_backend.db import async_session
from mascope_backend.runtime import runtime


DEFAULT_BATCH_SIZE = 100_000


async def remove_unmatched_match_isotopes(
    dry_run: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """
    Remove unmatched (empty sample_peak_id) match isotopes in bounded batches.

    Assumes the database engine is already configured.

    :param dry_run: When True, only count what would be deleted; make no changes.
    :type dry_run: bool
    :param batch_size: Rows deleted per committed batch. Keeps each transaction
        (and its WAL) bounded on very large tables.
    :type batch_size: int
    :return: Summary with the total unmatched count and the number deleted.
    :rtype: dict
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    async with async_session() as session:
        total_unmatched = int(
            await session.scalar(
                text("SELECT count(*) FROM match_isotope WHERE sample_peak_id = ''")
            )
        )

        if dry_run or total_unmatched == 0:
            status = "dry_run" if dry_run else "success"
            verb = "Would delete" if dry_run else "Deleted"
            message = f"{verb} {total_unmatched} unmatched match isotopes."
            runtime.logger.info(message)
            return {
                "status": status,
                "message": message,
                "total_unmatched": total_unmatched,
                "deleted": 0,
            }

        # Delete in ctid-bounded batches. Unmatched rows are dense (the majority of
        # the table), so each LIMITed scan is satisfied quickly; committing per
        # batch keeps locks and WAL bounded.
        deleted = 0
        while True:
            result = await session.execute(
                text(
                    "DELETE FROM match_isotope WHERE ctid IN ("
                    "  SELECT ctid FROM match_isotope "
                    "  WHERE sample_peak_id = '' LIMIT :batch_size"
                    ")"
                ),
                {"batch_size": batch_size},
            )
            await session.commit()
            batch_deleted = result.rowcount or 0
            deleted += batch_deleted
            if batch_deleted == 0:
                break
            runtime.logger.info(
                f"Removed {deleted}/{total_unmatched} unmatched match isotopes..."
            )

    message = f"Deleted {deleted} of {total_unmatched} unmatched match isotopes."
    runtime.logger.info(message)
    return {
        "status": "success",
        "message": message,
        "total_unmatched": total_unmatched,
        "deleted": deleted,
    }


def run_remove_unmatched_match_isotopes(
    dry_run: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """
    Synchronous entry point for removing unmatched match isotopes.

    :param dry_run: Report only; make no changes.
    :param batch_size: Rows per committed batch.
    :return: Operation summary.
    :rtype: dict
    """
    return asyncio.run(
        remove_unmatched_match_isotopes(dry_run=dry_run, batch_size=batch_size)
    )
