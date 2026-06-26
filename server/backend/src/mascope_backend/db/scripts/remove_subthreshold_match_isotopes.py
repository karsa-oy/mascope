"""
Maintenance script to remove negligible (sub-threshold) match isotopes.

Deletes match_isotope rows whose target isotope relative abundance is below the
effective per-instrument abundance threshold (honoring per-ion filter_params
overrides). Lossless by default: aborts if any matched (score > 0) row would be
deleted, so higher-level aggregates stay valid and need no recomputation.

Usage:
    mascope dev db script run remove_subthreshold_match_isotopes
    mascope prod db script run remove_subthreshold_match_isotopes --yes

To preview without deleting, run the dry-run variant from a shell, or set
DRY_RUN=1 in the environment before invoking.

Date: 2026-06-25
"""

import asyncio
import os

from mascope_backend.db import configure_database_engine
from mascope_backend.db.admin.match.remove_subthreshold_match_isotopes import (
    remove_subthreshold_match_isotopes,
)
from mascope_backend.runtime import runtime


async def run_remove() -> None:
    """
    Initialize the database and remove sub-threshold match isotopes, logging a summary.

    Honors environment toggles:
    - DRY_RUN=1            : report only, make no changes
    - ALLOW_MATCHED_LOSS=1 : permit deletion of matched rows (aggregates then stale)
    """
    await configure_database_engine()

    dry_run = os.environ.get("DRY_RUN") == "1"
    allow_matched_loss = os.environ.get("ALLOW_MATCHED_LOSS") == "1"

    result = await remove_subthreshold_match_isotopes(
        allow_matched_loss=allow_matched_loss,
        dry_run=dry_run,
    )

    runtime.logger.info("=" * 80)
    runtime.logger.info("REMOVE SUB-THRESHOLD MATCH ISOTOPES COMPLETE")
    runtime.logger.info(f"Status: {result['status']}")
    runtime.logger.info(result["message"])
    runtime.logger.info(
        f"Deleted={result['deleted']}, "
        f"total_subthreshold={result['total_subthreshold']}, "
        f"total_matched={result['total_matched']}"
    )
    for entry in result["per_instrument"]:
        runtime.logger.info(
            f"  {entry['instrument']}: threshold={entry['threshold']}, "
            f"subthreshold_rows={entry['subthreshold_rows']}, "
            f"matched_rows={entry['matched_rows']}"
        )
    if result["skipped_instruments"]:
        runtime.logger.info(
            f"Skipped unknown instruments: {result['skipped_instruments']}"
        )
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the removal script."""
    try:
        asyncio.run(run_remove())
    except KeyboardInterrupt:
        runtime.logger.info("Removal cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Removal script failed")
        raise


if __name__ == "__main__":
    main()
