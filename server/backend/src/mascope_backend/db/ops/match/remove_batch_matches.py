"""
Database operation for removing matches from multiple sample batches.

This operation provides a reusable function to remove match data from specified
sample batches and optionally set their status to 'rematch'.

Entry Points:
- Async: `remove_batch_matches()` for use in async code
- Sync: `run_remove_batch_matches()` for CLI and scripts
"""

import asyncio

from mascope_backend.api.controllers.match.match_controller import match_remove_batch
from mascope_backend.api.controllers.sample.batches.status.service import (
    update_sample_batch_status,
)
from mascope_backend.runtime import runtime


async def remove_batch_matches(
    sample_batch_ids: list[str],
    full_remove: bool = True,
    set_rematch_status: bool = True,
) -> dict:
    """
    Remove match data from multiple sample batches.

    Iterates through provided batch IDs and removes their match data.
    Optionally sets all batches to 'rematch' status after removal.

    :param sample_batch_ids: List of sample batch IDs to process
    :param full_remove: If True, removes all matches; if False, removes only orphaned matches
    :param set_rematch_status: If True, sets batches to 'rematch' status after removal
    :return: Operation results with counts and affected batch IDs
    """
    if not sample_batch_ids:
        return {
            "status": "success",
            "message": "No batches to process",
            "data": {
                "total_batches": 0,
                "processed_batches": 0,
            },
        }

    runtime.logger.info(
        f"Starting match removal for {len(sample_batch_ids)} batches "
        f"(full_remove={full_remove})"
    )

    processed_count = 0
    errors: list[dict] = []

    for batch_id in sample_batch_ids:
        try:
            result = await match_remove_batch(
                sample_batch_id=batch_id,
                full_remove=full_remove,
                independent_transaction=True,
            )

            if result.get("status") == "success":
                processed_count += 1
            else:
                errors.append(
                    {
                        "sample_batch_id": batch_id,
                        "error": "Match removal returned non-success status",
                    }
                )

        except Exception as e:
            runtime.logger.error(f"Error removing matches for batch {batch_id}: {e}")
            errors.append({"sample_batch_id": batch_id, "error": str(e)})

    if set_rematch_status and processed_count > 0:
        runtime.logger.info(f"Setting {processed_count} batches to 'rematch' status")
        try:
            await update_sample_batch_status(
                sample_batch_ids=sample_batch_ids,
                status="rematch",
                independent_transaction=True,
            )
        except Exception as e:
            runtime.logger.error(f"Error setting rematch status: {e}")
            errors.append({"operation": "set_rematch_status", "error": str(e)})

    message = f"Processed {processed_count}/{len(sample_batch_ids)} batches, "
    if errors:
        message += f" ({len(errors)} errors)"

    runtime.logger.info(message)

    return {
        "status": "success" if processed_count > 0 else "error",
        "message": message,
        "data": {
            "total_batches": len(sample_batch_ids),
            "processed_batches": processed_count,
            "errors": errors if errors else None,
        },
    }


def run_remove_batch_matches(
    sample_batch_ids: list[str],
    full_remove: bool = True,
    set_rematch_status: bool = True,
) -> dict:
    """
    Synchronous entry point for removing batch matches.

    Wrapper around async `remove_batch_matches()` for use in synchronous contexts
    such as CLI commands or standalone scripts.

    :param sample_batch_ids: List of sample batch IDs to process
    :param full_remove: If True, removes all matches; if False, removes only orphaned matches
    :param set_rematch_status: If True, sets batches to 'rematch' status after removal
    :return: Operation results
    """
    return asyncio.run(
        remove_batch_matches(
            sample_batch_ids=sample_batch_ids,
            full_remove=full_remove,
            set_rematch_status=set_rematch_status,
        )
    )
