"""
Batch-level peak assignment orchestration.

Runs the peak-centric assignment engine over every sample in a sample batch,
mirroring the targeted ``match_compute_batch`` controller. Each sample gets its
own PeakAssignmentRun (the engine is per-sample); this layer only sequences the
samples, isolates per-sample failures, tracks progress, and aggregates a batch
status.

Deliberately orthogonal to the targeted-match batch-status machine: assignment
is additive and does NOT take the SampleBatch 'processing' lock, so it can run
alongside (or independently of) matching.
"""

from sqlalchemy import select

from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.lib.api_features import api_controller_background_task
from mascope_backend.api.new.peak_assignments.config import PeakAssignmentConfig
from mascope_backend.api.new.peak_assignments.service import assign_sample_peaks
from mascope_backend.db import Sample, async_session
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("peak_assignment", "sample_batch_id")],
    error_notification_rooms=["sample_batch_id"],
    error_reload=[("peak_assignment", "sample_batch_id")],
)
async def assign_sample_batch_peaks(
    sample_batch_id: str,
    config: PeakAssignmentConfig | None = None,
    independent_transaction: bool = False,
    user_id: int | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Run the peak assignment engine over every sample in a sample batch.

    Each sample is assigned in sequence with its own PeakAssignmentRun. A single
    failing sample (corrupt file, unreadable metadata, transient DB error) fails
    only that sample, never the rest of the batch. Blank samples (no peaks) are
    skipped by the engine and counted as skipped here.

    :param sample_batch_id: ID of the sample batch to assign
    :param config: Optional run configuration applied to every sample; engine
        defaults (Stage A + Stage B) are used when omitted, since a batch
        assignment is a deliberate user-initiated operation
    :param independent_transaction: Flag for transaction/event handling
    :param user_id: Current user triggered operation (for user notifications)
    :param process_id: Process identifier for progress tracking
    :param parent_id: Parent process identifier
    :return: Batch data with per-sample counts and a status message
    """
    sample_batch = await fetch_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch.sample_batch_name

    async with async_session() as session:
        samples = (
            (
                await session.execute(
                    select(Sample).where(Sample.sample_batch_id == sample_batch_id)
                )
            )
            .scalars()
            .all()
        )

    total_samples_count = len(samples)
    if total_samples_count == 0:
        message = f"Sample batch '{sample_batch_name}' has no samples to assign."
        runtime.logger.info(message)
        return {
            "status": "skipped",
            "message": message,
            "data": {
                "assigned_samples_count": 0,
                "failed_samples_count": 0,
                "skipped_samples_count": 0,
                "total_samples_count": 0,
            },
            "_notification_data": {"sample_batch_id": sample_batch_id},
        }

    runtime.logger.info(
        f"Assigning peaks for sample batch '{sample_batch_name}' "
        f"({total_samples_count} samples)"
    )

    assigned_samples: list[str] = []
    failed_samples: list[str] = []
    skipped_samples: list[str] = []
    for item_index, sample in enumerate(samples):
        notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="assign_sample_batch_peaks",
            status="pending",
            message=(
                f"Assigning peaks for sample {item_index + 1}/{total_samples_count} "
                f"in sample batch '{sample_batch_name}'."
            ),
            data={
                "sample_batch_id": sample_batch_id,
                "_room_ids": [sample_batch_id],
                "_user_id": user_id,
                "_total_samples": total_samples_count,
                "_item_index": item_index,
            },
        )
        await send_progress_user_notification(notification)

        try:
            result = await assign_sample_peaks(
                sample_item_id=sample.sample_item_id,
                config=config,
                independent_transaction=False,
                user_id=user_id,
                process_id=gen_id(8),
                parent_id=process_id,
            )
            if result.get("status") == "skipped":
                skipped_samples.append(sample.sample_item_id)
            else:
                assigned_samples.append(sample.sample_item_id)
        except Exception as e:
            # A per-sample failure must not abort assignment for the rest of the
            # batch. CancelledError is a BaseException and is not caught.
            runtime.logger.warning(
                f"Peak assignment for sample '{sample.sample_item_name}' failed: {e}"
            )
            failed_samples.append(sample.sample_item_id)

        await send_progress_user_notification(notification, 1.0)

    assigned_count = len(assigned_samples)
    failed_count = len(failed_samples)
    skipped_count = len(skipped_samples)

    if failed_count > 0 and assigned_count == 0:
        status = "failed"
    elif failed_count > 0 and assigned_count > 0:
        status = "partial"
    elif assigned_count == 0 and skipped_count > 0:
        status = "skipped"
    else:
        status = "success"

    message = (
        f"Finished assigning peaks ({status}) for sample batch "
        f"'{sample_batch_name}'. {assigned_count} sample"
        f"{'s' if assigned_count != 1 else ''} assigned, "
        f"{failed_count} failed, {skipped_count} skipped."
    )
    runtime.logger.info(message)

    return {
        "status": status,
        "message": message,
        "data": {
            "assigned_samples_count": assigned_count,
            "failed_samples_count": failed_count,
            "skipped_samples_count": skipped_count,
            "total_samples_count": total_samples_count,
        },
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }
