"""
Service to handle the status of sample batches.
"""

from datetime import datetime, timezone

from sqlalchemy import select, update, case, exists

from mascope_backend.db import async_session
from mascope_backend.db.models import SampleBatch, SampleItem
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.models.sample.batches.config import sample_batch_config

from mascope_backend.runtime import runtime


# TODO_reload - should emit affected batches ids to the workspace rooms
@api_controller(
    success_reload_events=[
        ("sample_batch_reload", "affected_workspace_ids"),
    ],
    error_reload_events=[
        ("sample_batch_reload", "affected_workspace_ids"),
    ],
)
async def update_sample_batch_status(
    sample_batch_ids: list[str],
    status: str,
    independent_transaction: bool = False,
) -> dict:
    """
    Updates the status of multiple sample batches.

    :param sample_batch_ids: List of sample batch IDs to update
    :type sample_batch_ids: list[str]
    :param status: New status to set for all specified batches
    :type status: str
    :param independent_transaction: Flag indicating if operation is independent transaction
    :type independent_transaction: bool
    :raises NotFoundException: When batches are not found
    :raises ValueError: When status is invalid
    :return: Update results with count of affected batches
    :rtype: dict
    """
    if status not in sample_batch_config.SAMPLE_BATCH_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sample_batch_config.SAMPLE_BATCH_STATUSES)}"
        )

    async with async_session() as session:
        result = await session.execute(
            update(SampleBatch)
            .where(
                SampleBatch.sample_batch_id.in_(sample_batch_ids),
                # update if current status would change
                SampleBatch.status
                != case(
                    (
                        exists().where(
                            SampleItem.sample_batch_id == SampleBatch.sample_batch_id
                        ),
                        status,
                    ),
                    else_="ready",
                ),
            )
            .values(
                status=case(
                    (
                        exists().where(
                            SampleItem.sample_batch_id == SampleBatch.sample_batch_id
                        ),
                        status,  # has samples: use requested status
                    ),
                    else_="ready",  # no samples: always set to "ready"
                ),
                sample_batch_utc_modified=datetime.now(timezone.utc),
            )
        )

        updated_count = result.rowcount

        await session.commit()

        skipped_count = len(sample_batch_ids) - updated_count
        message = f"Updated {updated_count}/{len(sample_batch_ids)} batches to status '{status}'"

        if updated_count > 0:
            runtime.logger.info(message)

        affected_workspace_ids = list(
            (
                await session.execute(
                    select(SampleBatch.workspace_id)
                    .where(SampleBatch.sample_batch_id.in_(sample_batch_ids))
                    .distinct()
                )
            ).scalars()
        )

        return {
            "status": "success",
            "message": message,
            "data": {
                "total_batches": len(sample_batch_ids),
                "updated_batches": updated_count,
                "skipped_batches": skipped_count,
                "target_status": status,
            },
            "_notification_data": {
                "affected_workspace_ids": affected_workspace_ids,
            },
        }
