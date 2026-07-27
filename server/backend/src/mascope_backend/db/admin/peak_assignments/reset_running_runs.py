"""
Database operation for reconciling peak assignment runs stuck in 'running'.

A ``PeakAssignmentRun`` is created in ``running`` and moved to ``completed`` or
``failed`` by the engine's own success/failure paths. Neither path survives the
process dying underneath it - a worker restart, an OOM kill, or a cancelled
background task (``CancelledError`` is a ``BaseException``, so the engine's
``except Exception`` finalizer does not run). Such a run stays ``running``
forever: invisible to the read model (which only serves the latest *completed*
run) but never cleaned up either.

This resets them at startup, mirroring
:func:`~mascope_backend.db.admin.batch.reset_processing_status.reset_stuck_processing_batches`.
Startup runs in the main process before any worker is spawned, so nothing can
legitimately be ``running`` at that moment - every such row is a leftover.

They are marked ``failed`` rather than adopted as ``completed``. The engine
writes its whole ledger in a single insert, so "this run has rows" does imply
"its ledger committed in full" - but not the converse: a run whose sample
yielded no assignments at all skips the insert entirely, and is then
indistinguishable from one that died before reaching it. ``failed`` is also the
recoverable direction (re-run the sample) where a wrongly-claimed ``completed``
is not, and the rows an interrupted run left behind are reclaimed by
``prune_peak_assignment_runs`` rather than kept alive by adopting the run.

Entry Points:
- Async: `reset_running_peak_assignment_runs()` for use in async code
- Sync: `run_reset_running_peak_assignment_runs()` for CLI and scripts
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import update

from mascope_backend.db import PeakAssignmentRun, async_session
from mascope_backend.runtime import runtime


STUCK_RUN_ERROR = "Interrupted: the server restarted while this run was in progress."


async def reset_running_peak_assignment_runs() -> dict:
    """
    Mark peak assignment runs left in 'running' as failed.

    Called at application startup to recover from abnormal termination during a
    run. Safe to call when there is nothing to reset.

    :return: Operation results with the count of reset runs
    :rtype: dict
    """
    async with async_session() as session:
        update_result = await session.execute(
            update(PeakAssignmentRun)
            .where(PeakAssignmentRun.status == "running")
            .values(
                status="failed",
                error=STUCK_RUN_ERROR,
                peak_assignment_run_utc_completed=datetime.now(timezone.utc),
            )
        )

        reset_count = update_result.rowcount
        await session.commit()

        if reset_count == 0:
            message = "No interrupted peak assignment runs found"
        else:
            message = (
                f"Reset {reset_count} interrupted peak assignment run(s) to 'failed'"
            )
        runtime.logger.debug(message)

        return {
            "status": "success",
            "message": message,
            "data": {
                "reset_count": reset_count,
            },
        }


def run_reset_running_peak_assignment_runs() -> dict:
    """
    Synchronous wrapper for CLI and script entry points.

    :return: Operation results with the count of reset runs
    :rtype: dict
    """
    return asyncio.run(reset_running_peak_assignment_runs())
