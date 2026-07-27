"""
Database operation for pruning superseded peak assignment runs.

Every assignment run writes **one row per observed peak** of its sample -
including peaks it could not assign, because the ledger is deliberately
complete. Nothing ever removed them: re-assigning a sample added a whole new
run beside the old one, so a sample assigned n times carried n x (its peak
count) rows forever, and `peak_assignment` grows without bound on any
deployment that re-runs assignment routinely.

This reclaims two kinds of run:

- **Superseded completed runs.** The read model only ever serves the *latest
  completed* run for a sample; older ones are reachable only through the run
  selector, for comparing against a previous result. Keeping the newest
  ``keep_per_sample`` of them preserves that while bounding the total.
- **Non-completed runs** older than ``keep_failed_hours``. A failed or
  interrupted run is invisible to the read model and can never become visible,
  so its rows are pure waste - but a just-failed run is kept briefly so its
  error is still inspectable.

Deleting the run row is enough: ``peak_assignment.peak_assignment_run_id`` is
``ON DELETE CASCADE``, so the ledger goes with it.

Entry Points:
- Async: `prune_peak_assignment_runs()` for use in async code
- Sync: `run_prune_peak_assignment_runs()` for CLI and scripts
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select

from mascope_backend.db import PeakAssignment, PeakAssignmentRun, async_session
from mascope_backend.runtime import runtime


# Newest completed runs kept per sample. More than one so a user can still
# compare a re-run against what it replaced; small enough that the table stays
# proportional to the dataset rather than to how often assignment is re-run.
DEFAULT_KEEP_PER_SAMPLE = 3

# Grace on non-completed runs, so a failure stays inspectable for a day.
DEFAULT_KEEP_FAILED_HOURS = 24

# Runs deleted per committed batch. Each run cascades to one row per peak of its
# sample (thousands), so committing per batch keeps locks and WAL bounded.
DEFAULT_BATCH_SIZE = 25


async def _select_prunable_run_ids(
    session, keep_per_sample: int, keep_failed_hours: int
) -> list[str]:
    """Collect the run ids eligible for pruning.

    :param session: Open async session.
    :param keep_per_sample: Newest completed runs to keep per sample.
    :param keep_failed_hours: Grace period on non-completed runs.
    :return: Run ids to delete.
    """
    prunable: list[str] = []

    # Superseded completed runs: everything past the newest keep_per_sample for
    # each sample. Ranked in Python over an ordered scan rather than a window
    # function, so the same code path works on any supported Postgres and stays
    # readable; the run table is small relative to the assignment table.
    completed = (
        await session.execute(
            select(
                PeakAssignmentRun.peak_assignment_run_id,
                PeakAssignmentRun.sample_item_id,
            )
            .where(PeakAssignmentRun.status == "completed")
            .order_by(
                PeakAssignmentRun.sample_item_id,
                PeakAssignmentRun.peak_assignment_run_utc_created.desc(),
            )
        )
    ).all()

    seen_per_sample: dict[str, int] = {}
    for run_id, sample_item_id in completed:
        rank = seen_per_sample.get(sample_item_id, 0)
        seen_per_sample[sample_item_id] = rank + 1
        if rank >= keep_per_sample:
            prunable.append(run_id)

    # Non-completed runs past the grace period. Falls back to the created
    # timestamp because an interrupted run may never have been given a completed
    # one. A run with neither is treated as ancient rather than skipped: both
    # columns are nullable, and `NULL < cutoff` is NULL, so comparing alone would
    # make such a row immortal - invisible to the read model yet never reclaimed.
    cutoff = datetime.now(timezone.utc) - timedelta(hours=keep_failed_hours)
    age = func.coalesce(
        PeakAssignmentRun.peak_assignment_run_utc_completed,
        PeakAssignmentRun.peak_assignment_run_utc_created,
    )
    stale = (
        await session.execute(
            select(PeakAssignmentRun.peak_assignment_run_id).where(
                PeakAssignmentRun.status != "completed",
                or_(age < cutoff, age.is_(None)),
            )
        )
    ).scalars()
    prunable.extend(stale)

    # A run can qualify under both rules only if it is non-completed, which the
    # first pass never selects - but de-duplicate defensively and keep order
    # stable so a dry run reports exactly what a real run would delete.
    return list(dict.fromkeys(prunable))


async def prune_peak_assignment_runs(
    dry_run: bool = False,
    keep_per_sample: int = DEFAULT_KEEP_PER_SAMPLE,
    keep_failed_hours: int = DEFAULT_KEEP_FAILED_HOURS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """
    Delete superseded and stale peak assignment runs, cascading to their rows.

    Assumes the database engine is already configured.

    :param dry_run: When True, only count what would be deleted; change nothing.
    :type dry_run: bool
    :param keep_per_sample: Newest completed runs to keep per sample.
    :type keep_per_sample: int
    :param keep_failed_hours: Keep non-completed runs younger than this.
    :type keep_failed_hours: int
    :param batch_size: Runs deleted per committed batch.
    :type batch_size: int
    :return: Summary with prunable run count, deleted run count and freed rows.
    :rtype: dict
    """
    if keep_per_sample < 1:
        raise ValueError("keep_per_sample must be at least 1")
    if keep_failed_hours < 0:
        raise ValueError("keep_failed_hours must not be negative")
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    async with async_session() as session:
        prunable = await _select_prunable_run_ids(
            session, keep_per_sample, keep_failed_hours
        )

        if not prunable:
            message = "No superseded peak assignment runs to prune."
            runtime.logger.info(message)
            return {
                "status": "success",
                "message": message,
                "prunable_runs": 0,
                "deleted_runs": 0,
                "deleted_assignments": 0,
            }

        # Count the rows those runs hold, so both a dry run and a real run can
        # report the space actually at stake.
        row_count = int(
            await session.scalar(
                select(func.count())
                .select_from(PeakAssignment)
                .where(PeakAssignment.peak_assignment_run_id.in_(prunable))
            )
            or 0
        )

        if dry_run:
            message = (
                f"Would delete {len(prunable)} peak assignment run(s) and "
                f"{row_count} assignment row(s) "
                f"(keeping the newest {keep_per_sample} completed run(s) per sample)."
            )
            runtime.logger.info(message)
            return {
                "status": "dry_run",
                "message": message,
                "prunable_runs": len(prunable),
                "deleted_runs": 0,
                "deleted_assignments": 0,
            }

        deleted_runs = 0
        for start in range(0, len(prunable), batch_size):
            chunk = prunable[start : start + batch_size]
            result = await session.execute(
                delete(PeakAssignmentRun).where(
                    PeakAssignmentRun.peak_assignment_run_id.in_(chunk)
                )
            )
            await session.commit()
            deleted_runs += result.rowcount or 0

        message = (
            f"Deleted {deleted_runs} peak assignment run(s) and about "
            f"{row_count} assignment row(s) "
            f"(kept the newest {keep_per_sample} completed run(s) per sample)."
        )
        runtime.logger.info(message)
        return {
            "status": "success",
            "message": message,
            "prunable_runs": len(prunable),
            "deleted_runs": deleted_runs,
            "deleted_assignments": row_count,
        }


def run_prune_peak_assignment_runs(
    dry_run: bool = False,
    keep_per_sample: int = DEFAULT_KEEP_PER_SAMPLE,
    keep_failed_hours: int = DEFAULT_KEEP_FAILED_HOURS,
) -> dict:
    """
    Synchronous wrapper for CLI and script entry points.

    :param dry_run: When True, only count what would be deleted.
    :param keep_per_sample: Newest completed runs to keep per sample.
    :param keep_failed_hours: Keep non-completed runs younger than this.
    :return: Prune summary.
    :rtype: dict
    """
    return asyncio.run(
        prune_peak_assignment_runs(
            dry_run=dry_run,
            keep_per_sample=keep_per_sample,
            keep_failed_hours=keep_failed_hours,
        )
    )
