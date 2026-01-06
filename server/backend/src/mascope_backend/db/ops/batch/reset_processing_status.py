"""
Database operation for resetting stuck 'processing' batch statuses.

This operation identifies and resets sample batches that are stuck in
'processing' status (e.g., due to application termination during processing)
back to 'rematch' status, making them available for user operations.

Entry Points:
- Async: `reset_stuck_processing_batches()` for use in async code
- Sync: `run_reset_stuck_processing_batches()` for CLI and scripts
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import update

from mascope_backend.db import SampleBatch, async_session
from mascope_backend.runtime import runtime


async def reset_stuck_processing_batches() -> dict:
    """
    Reset sample batches stuck in 'processing' status to 'rematch'.

    This operation finds all batches with status='processing' and resets them
    to 'rematch' status. This is called at application startup to
    recover from abnormal terminations during batch processing.

    :return: Operation results with count of reset batches
    :rtype: dict
    """
    async with async_session() as session:
        update_result = await session.execute(
            update(SampleBatch)
            .where(SampleBatch.status == "processing")
            .values(
                status="rematch",
                sample_batch_utc_modified=datetime.now(timezone.utc),
            )
        )

        reset_count = update_result.rowcount
        await session.commit()

        if reset_count == 0:
            message = "No stuck 'processing' batches found"
        else:
            message = (
                f"Reset {reset_count} stuck 'processing' batch(es) to 'rematch' status"
            )
        runtime.logger.debug(message)

        return {
            "status": "success",
            "message": message,
            "data": {
                "reset_count": reset_count,
            },
        }


def run_reset_stuck_processing_batches() -> dict:
    """
    Synchronous entry point for resetting stuck processing batches.

    Wrapper around async `reset_stuck_processing_batches()` for use in
    synchronous contexts such as CLI commands or standalone scripts.

    :return: Operation results
    :rtype: dict
    """
    return asyncio.run(reset_stuck_processing_batches())
