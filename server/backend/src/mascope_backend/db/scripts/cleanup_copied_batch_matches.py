"""
Maintenance script to clean up corrupted matches in copied batches.

Bug #1170 - Sample item ordering was not preserved during batch copy operations,
causing match data to be assigned to incorrect samples.

This script finds batches with 'copy' in their name, displays them for review,
requests confirmation, then removes all match data and sets them to 'rematch' status.

Usage:
    mascope dev db script run cleanup_copied_batch_matches

    # To limit to a specific workspace (optional):
    mascope prod db script run cleanup_copied_batch_matches --workspace <workspace_id>


Date: 2025-10-21
Issue: #1170
"""

import argparse
import asyncio

from sqlalchemy import select

from mascope_backend.api.controllers.match.targets.batch.match_targets_batch_controller import (
    get_batch_data,
)
from mascope_backend.db import SampleBatch, async_session, configure_database_engine
from mascope_backend.db.admin.match.remove_batch_matches import remove_batch_matches
from mascope_backend.runtime import runtime


async def find_copied_batches(workspace_id: str | None = None) -> list[dict]:
    """
    Find all sample batches with 'copy' in their name and fetch their detailed data.

    :param workspace_id: Optional workspace ID to filter results
    :return: List of batch data dictionaries with match counts
    """
    async with async_session() as session:
        query = select(SampleBatch).where(SampleBatch.sample_batch_name.ilike("%copy%"))

        if workspace_id:
            query = query.where(SampleBatch.workspace_id == workspace_id)

        result = await session.execute(query)
        batches = result.scalars().all()

        if not batches:
            return []

    batch_data_list = []
    for batch in batches:
        try:
            batch_data_result = await get_batch_data(
                sample_batch_id=batch.sample_batch_id
            )

            batch_data_list.append(
                {
                    "sample_batch": batch_data_result["data"]["sample_batch"],
                    "counts": batch_data_result["result"],
                }
            )
        except Exception as e:
            runtime.logger.error(
                f"Error fetching data for batch {batch.sample_batch_id}: {e}"
            )
            batch_data_list.append(
                {
                    "sample_batch": {
                        "sample_batch_id": batch.sample_batch_id,
                        "sample_batch_name": batch.sample_batch_name,
                        "workspace_id": batch.workspace_id,
                        "status": batch.status,
                    },
                    "counts": {
                        "samples": 0,
                        "compounds": 0,
                        "ions": 0,
                        "isotopes": 0,
                    },
                }
            )

    return batch_data_list


def display_batch_summary(batches: list[dict]) -> None:
    """
    Display a formatted summary of affected batches.

    :param batches: List of batch data dictionaries from get_batch_data
    """
    total_samples = 0
    total_matches = 0

    print(f"Found {len(batches)} batches with 'copy' in name:")
    print("=" * 80)
    for i, batch_data in enumerate(batches, 1):
        batch = batch_data["sample_batch"]
        counts = batch_data["counts"]

        print(f"\n{i}. {batch['sample_batch_name']}")
        print(f"   ID: {batch['sample_batch_id']}")
        print(f"   Workspace: {batch['workspace_id']}")
        print(f"   Status: {batch['status']}")
        print(f"   Samples: {counts['samples']}")
        print(
            f"   Matches: {counts['compounds']} compounds, "
            f"{counts['ions']} ions, {counts['isotopes']} isotopes"
        )

        total_samples += counts["samples"]
        total_matches += counts["compounds"] + counts["ions"] + counts["isotopes"]
    print("=" * 80)
    print(
        f"Total: {len(batches)} batches, {total_samples} samples, {total_matches} matches"
    )


async def run_cleanup(workspace_id: str | None = None) -> None:
    """
    Main cleanup logic: find batches, confirm, and remove matches.

    :param workspace_id: Optional workspace ID to limit scope
    """
    await configure_database_engine()

    batches = await find_copied_batches(workspace_id=workspace_id)

    if not batches:
        runtime.logger.info(
            "No batches with 'copy' in name found. Nothing to clean up."
        )
        return

    display_batch_summary(batches)

    runtime.logger.info("Executing cleanup...")
    batch_ids = [b["sample_batch"]["sample_batch_id"] for b in batches]

    result = await remove_batch_matches(
        sample_batch_ids=batch_ids,
        full_remove=True,
        set_rematch_status=True,
    )

    runtime.logger.info("=" * 80)
    runtime.logger.info("CLEANUP COMPLETE")
    runtime.logger.info(
        f"Batches processed: {result['data']['processed_batches']}/{result['data']['total_batches']}"
    )
    runtime.logger.info("=" * 80)

    if result["data"].get("errors"):
        runtime.logger.warning(f"Errors encountered: {len(result['data']['errors'])}")
        for error in result["data"]["errors"]:
            runtime.logger.error(f"  - {error}")


def main() -> None:
    """Entry point for the cleanup script."""
    parser = argparse.ArgumentParser(
        description="Clean up corrupted matches in copied batches",
    )
    parser.add_argument(
        "--workspace",
        help="Limit cleanup to specific workspace",
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_cleanup(workspace_id=args.workspace))
    except KeyboardInterrupt:
        runtime.logger.info("\nCleanup cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Cleanup script failed")
        raise


if __name__ == "__main__":
    main()
