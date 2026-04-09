"""
Maintenance script to set all batches to 'rematch' status.

Issue #183 - Minimum isotope abundance threshold was removed. All new samples will be
matched against "all" isotopes. However, existing samples that were matched with a
threshold may have incomplete matches.
To show the user that the existing batches are not up to date with the new matching
logic, we will set all batches to 'rematch' status.
This script fetches all batch IDs from the database, prompts the user for confirmation,
then sets their status to 'rematch'.

Usage:
    mascope dev db script run set_batches_to_rematch_status
    mascope prod db script run set_batches_to_rematch_status

Date: 2026-02-09
Issue: #183
"""

import asyncio

from sqlalchemy import select

from mascope_backend.api.controllers.sample.batches.status.service import (
    update_sample_batch_status,
)
from mascope_backend.db import SampleBatch, async_session, configure_database_engine
from mascope_backend.runtime import runtime


async def fetch_batch_ids() -> list[str]:
    """Fetch all batch IDs from the database.

    :return: List of all batch ids in the database
    :rtype: list[str]
    """
    async with async_session() as session:
        query = select(SampleBatch)
        result = await session.execute(query)
        batches = result.scalars().all()

    sample_batch_ids = [batch.sample_batch_id for batch in batches]

    return sample_batch_ids


async def set_batches_to_rematch_status() -> None:
    """Set all existing sample batches to 'rematch' status."""

    await configure_database_engine()

    sample_batch_ids = await fetch_batch_ids()

    if not sample_batch_ids:
        runtime.logger.info("No batches found. Nothing to update.")
        return

    runtime.logger.info("Setting batch statuses to rematch...")

    try:
        await update_sample_batch_status(
            sample_batch_ids=sample_batch_ids,
            status="rematch",
            independent_transaction=False,
        )
    except Exception as e:
        runtime.logger.error(f"Error setting rematch status: {e}")
        raise

    runtime.logger.info(
        f"Finished setting {len(sample_batch_ids)} batches to 'rematch' status"
    )


def main() -> None:
    """Entry point for the script."""

    try:
        asyncio.run(set_batches_to_rematch_status())
    except KeyboardInterrupt:
        runtime.logger.info(
            "Setting batch statuses to rematch was cancelled by user (Ctrl+C)"
        )
    except Exception as e:
        runtime.logger.exception(f"Script failed: {e}")
        raise


if __name__ == "__main__":
    main()
