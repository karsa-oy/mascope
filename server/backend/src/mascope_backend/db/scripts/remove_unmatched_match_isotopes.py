"""
Maintenance script to remove unmatched (placeholder) match isotopes.

Deletes match_isotope rows with an empty sample_peak_id - isotopes that had no
matched peak. These are no longer stored by the backend and are reconstructed on
read from their target_isotope, so removing the historical ones is lossless and
reclaims the bulk of the table. Run in bounded batches; follow with
``VACUUM FULL match_isotope`` (or pg_repack) to return the freed space to the OS.

Usage:
    mascope dev db script run remove_unmatched_match_isotopes
    mascope prod db script run remove_unmatched_match_isotopes --yes

Environment toggles:
- DRY_RUN=1        : report the count only, delete nothing
- BATCH_SIZE=<n>   : rows deleted per committed batch (default 100000)

Date: 2026-07-08
"""

import asyncio
import os

from mascope_backend.db import configure_database_engine
from mascope_backend.db.admin.match.remove_unmatched_match_isotopes import (
    DEFAULT_BATCH_SIZE,
    remove_unmatched_match_isotopes,
)
from mascope_backend.runtime import runtime


async def run_remove() -> None:
    """
    Initialize the database and remove unmatched match isotopes, logging a summary.

    Honors environment toggles:
    - DRY_RUN=1      : report only, make no changes
    - BATCH_SIZE=<n> : rows per committed batch
    """
    await configure_database_engine()

    dry_run = os.environ.get("DRY_RUN") == "1"
    try:
        batch_size = int(os.environ.get("BATCH_SIZE", DEFAULT_BATCH_SIZE))
    except ValueError:
        runtime.logger.error("BATCH_SIZE must be a positive integer.")
        raise

    result = await remove_unmatched_match_isotopes(
        dry_run=dry_run,
        batch_size=batch_size,
    )

    runtime.logger.info("=" * 80)
    runtime.logger.info("REMOVE UNMATCHED MATCH ISOTOPES COMPLETE")
    runtime.logger.info(f"Status: {result['status']}")
    runtime.logger.info(result["message"])
    runtime.logger.info(
        f"Deleted={result['deleted']}, total_unmatched={result['total_unmatched']}"
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
