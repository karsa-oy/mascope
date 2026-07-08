"""
Database operation to remove unmatched (score-0) match isotopes.

Deletes ``match_isotope`` rows with ``match_score = 0`` - isotopes that are not a
real match. A score of 0 means either no peak within the match window, or a peak
whose m/z error (>= 100 ppm) or abundance error (>= 100%) is so large it scores 0
and can never become a match at any read-time tolerance (apply_match_params only
ever zeroes scores, never raises them). Such rows carry no analytical value - they
only ever render 0% - and are reconstructed on read from their ``target_isotope``,
so persisting them is pure bloat. This matches the "found peak" definition used by
export_goldens (``match_score > 0``).

The delete is lossless for higher-level aggregates: a score-0 isotope contributes
0 to every aggregate (score * abundance and, after apply_match_params, intensity),
so match_ion / match_compound / ... are unchanged and need no recomputation. It is
done in bounded batches so a multi-hundred-million-row table can be cleaned without
one giant transaction / WAL blowup. Run ``VACUUM FULL match_isotope`` (or pg_repack)
afterwards to return the freed space to the OS.

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
    Remove unmatched (match_score = 0) match isotopes in bounded batches.

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
                text("SELECT count(*) FROM match_isotope WHERE match_score = 0")
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
                    "  WHERE match_score = 0 LIMIT :batch_size"
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
