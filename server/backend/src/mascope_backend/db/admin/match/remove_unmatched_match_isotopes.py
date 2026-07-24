"""
Database operation to remove unmatched (score-0) match isotopes, keeping one
sentinel row per fully-unmatched ion.

Deletes ``match_isotope`` rows with ``match_score = 0`` - isotopes that are not a
real match - EXCEPT one sentinel row per (sample, ion) whose isotopes all scored
0: the main isotope (highest ``relative_abundance``, ties broken by lowest ``mz``
then ``target_isotope_id``). This converts legacy pre-v1.3.0 data into exactly
the form ``select_match_isotopes_to_persist`` writes today.

The sentinel matters because stored rows double as "this ion was evaluated for
this sample" markers: ``fetch_sample_unmatched_target_isotopes`` skips every
isotope of an ion with any stored row. Deleting ALL zero-score rows (the
pre-sentinel behavior of this script) would erase those markers and make the
next "refresh matches" recompute every unmatched ion of every sample.

A score of 0 means either no peak within the match window, or a peak whose m/z
error (>= 100 ppm) or abundance error (>= 100%) is so large it scores 0 and can
never become a match at any read-time tolerance (apply_match_params only ever
zeroes scores, never raises them). The non-sentinel rows carry no analytical
value - they only ever render 0% - and are reconstructed on read from their
``target_isotope``, so persisting them is pure bloat. This matches the "found
peak" definition used by export_goldens (``match_score > 0``).

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

# Scratch table holding the sentinel rows to keep. UNLOGGED (no WAL) and
# session-independent, so batched deletes work across pooled connections;
# recreated from scratch on every run, dropped on completion.
KEEP_TABLE = "_mascope_keep_sentinel_match_isotopes"

# One sentinel per (sample, ion) whose isotopes ALL scored 0: the main isotope
# (highest relative_abundance, then lowest mz, then target_isotope_id) - the
# same selection rule as select_match_isotopes_to_persist.
SELECT_SENTINELS_SQL = """
SELECT DISTINCT ON (mi.sample_item_id, ti.target_ion_id) mi.match_isotope_id
FROM match_isotope mi
JOIN target_isotope ti ON ti.target_isotope_id = mi.target_isotope_id
WHERE mi.match_score = 0
  AND NOT EXISTS (
    SELECT 1
    FROM match_isotope mi2
    JOIN target_isotope ti2 ON ti2.target_isotope_id = mi2.target_isotope_id
    WHERE mi2.sample_item_id = mi.sample_item_id
      AND ti2.target_ion_id = ti.target_ion_id
      AND mi2.match_score > 0
  )
ORDER BY mi.sample_item_id, ti.target_ion_id,
         ti.relative_abundance DESC, ti.mz ASC, ti.target_isotope_id ASC
"""


async def remove_unmatched_match_isotopes(
    dry_run: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """
    Remove unmatched (match_score = 0) match isotopes in bounded batches,
    keeping one sentinel row per fully-unmatched ion as its evaluated marker.

    Assumes the database engine is already configured.

    :param dry_run: When True, only count what would be deleted; make no changes.
    :type dry_run: bool
    :param batch_size: Rows deleted per committed batch. Keeps each transaction
        (and its WAL) bounded on very large tables.
    :type batch_size: int
    :return: Summary with the zero-score total, sentinel count and deleted count.
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
        sentinel_count = int(
            await session.scalar(
                text(f"SELECT count(*) FROM ({SELECT_SENTINELS_SQL}) AS sentinels")  # noqa: S608
            )
        )
        deletable = total_unmatched - sentinel_count

        if dry_run or deletable == 0:
            status = "dry_run" if dry_run else "success"
            verb = "Would delete" if dry_run else "Deleted"
            message = (
                f"{verb} {deletable} unmatched match isotopes "
                f"(keeping {sentinel_count} evaluated-ion sentinels)."
            )
            runtime.logger.info(message)
            return {
                "status": status,
                "message": message,
                "total_unmatched": total_unmatched,
                "sentinels_kept": sentinel_count,
                "deleted": 0,
            }

        # Materialize the keep-set once; the batched deletes then only need an
        # indexed anti-join. Recreate from scratch so an aborted earlier run
        # cannot leave a stale keep-set behind.
        await session.execute(text(f"DROP TABLE IF EXISTS {KEEP_TABLE}"))
        await session.execute(
            text(f"CREATE UNLOGGED TABLE {KEEP_TABLE} AS {SELECT_SENTINELS_SQL}")  # noqa: S608
        )
        await session.execute(
            text(f"CREATE UNIQUE INDEX ON {KEEP_TABLE} (match_isotope_id)")
        )
        await session.commit()

        # Delete in ctid-bounded batches. Unmatched rows are dense (the majority of
        # the table), so each LIMITed scan is satisfied quickly; committing per
        # batch keeps locks and WAL bounded.
        deleted = 0
        try:
            while True:
                result = await session.execute(
                    text(
                        "DELETE FROM match_isotope WHERE ctid IN ("
                        "  SELECT mi.ctid FROM match_isotope mi"
                        "  WHERE mi.match_score = 0"
                        "  AND NOT EXISTS ("
                        f"    SELECT 1 FROM {KEEP_TABLE} k"
                        "     WHERE k.match_isotope_id = mi.match_isotope_id"
                        "  )"
                        "  LIMIT :batch_size"
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
                    f"Removed {deleted}/{deletable} unmatched match isotopes..."
                )
        finally:
            await session.execute(text(f"DROP TABLE IF EXISTS {KEEP_TABLE}"))
            await session.commit()

    message = (
        f"Deleted {deleted} of {deletable} unmatched match isotopes "
        f"(kept {sentinel_count} evaluated-ion sentinels)."
    )
    runtime.logger.info(message)
    return {
        "status": "success",
        "message": message,
        "total_unmatched": total_unmatched,
        "sentinels_kept": sentinel_count,
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
